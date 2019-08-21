# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 28, 2019
# Last Update: Time-stamp: <2019-08-19 19:25:26 liux>
###############################################################

from collections import defaultdict
import multiprocessing as mp
#from concurrent import futures
import time, atexit

from .simulus import *
from .simulator import *

__all__ = ["sync"]

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class sync(object):
    """A synchronized group of simulators whose simulation clocks will
    advance synchronously."""

    _simulus = None
    
    def __init__(self, sims, enable_smp=False, enable_spmd=False, lookahead=infinite_time, smp_ways=None):
        """Create a synchronized group of multiple simulators. 

        Bring all simulators in the group to synchrony; that is, the
        simulation clocks of all the simulators in the group, from now
        on, will be advanced synchronously in a coordinated fashion.

        Args:
            sims (list or tuple): a list of local simulators; the
                simulators are identified either by their names or as
                direct references to instances

            enable_smp (bool): enable SMP (Symmetric Multi-Processing)
                mode, in which case each local simulator will run as a
                separate process, and communication between the
                simulators will be facilitated through inter-process
                communication (IPC) mechanisms; the default is False,
                in which case all local simulators will run
                sequentially within the same process

            enable_spmd (bool): enable SPMD (Single Program Multiple
                Data) mode, in which case multiple simulus instances,
                potentially on distributed memory machines, will run
                in parallel, where communication between the simulus
                instances will be facilitated through the Message
                Passing Interface (MPI); the default is False, in
                which case the local simulus instance will run
                standalone with all simulators running either
                sequentially as one process (when enable_smp is
                False), or in parallel as separate processes (when
                enable_smp is True)

            lookahead (float): the maximum difference in simulation
                time between the simulators in the group; the default
                is infinity; the final lookahead for parallel
                simulation will be determined by the min delays of the
                named mailboxes of the simulators

            smp_ways (int): the maximum number of processes to be
                created for shared-memory multiprocessing. This
                parameter is only used when SMP is enabled.

        Returns: 
            This function creates, initializes, and returns a
            synchronized group. The simulators will first advance
            their simulation clock (asynchronously) to the maximum
            simulation time among all simulators (including both local
            simulators and remote ones, if enable_spmd is True). When
            the function returns, the listed simulators are bound to
            the synchronized group.  That is, the simulation clocks of
            the simulators will be advanced synchronously from now on:
            all simulators will process events (including all messages
            sent between the simulators) in the proper timestamp
            order. (This is also known as the local causality
            constraint in the parallel discrete-event simulation
            literature.)

        """

        # the simulus instance is a class variable
        if not sync._simulus:
            sync._simulus = _Simulus()

        if lookahead <= 0:
            errmsg = "sync(looahead=%r) expects a positive lookahead" % lookahead
            log.error(errmsg)
            raise ValueError(errmsg)
            
        if smp_ways is not None and \
           (not isinstance(smp_ways, int) or smp_ways <= 0):
            errmsg = "sync(smp_ways=%r) expects a positive integer" % smp_ways
            log.error(errmsg)
            raise ValueError(errmsg)
        
        self._activated = False  # keep it false until we are done with creating the sync group
        self._smp = enable_smp
        self._smp_ways = smp_ways
        self._spmd = enable_spmd
        if self._spmd and not sync._simulus.args.mpi:
            errmsg = "sync(enable_spmd=True) requires MPI support (use --mpi or -x command-line option)"
            log.error(errmsg)
            raise ValueError(errmsg)

        # the local simulators are provided either by names or as
        # direct references
        self._local_sims = {} # a map from names to simulator instances
        self._all_sims = {} # a map from names to mpi ranks (identifying simulator's location)
        now_max = minus_infinite_time # to find out the max simulation time of all simulators
        if not isinstance(sims, (list, tuple)):
            errmsg = "sync(sims=%r) expects a list of simulators" % sims
            log.error(errmsg)
            raise TypeError(errmsg)
        for s in sims:
            if isinstance(s, str):
                # if simulator name is provided, turn it into instance
                ss = sync._simulus.get_simulator(s)
                if ss is None:
                    errmsg = "sync() expects a list of simulators, but '%s' is not" % s
                    log.error(errmsg)
                    raise ValueError(errmsg)
                else: s = ss

            # the item must be a simulator instance
            if isinstance(s, simulator):
                if s._insync:
                    # the simulator's already in a sync group
                    if s._insync != self:
                        errmsg = "sync() simulator '%s' belongs to another group" % s.name
                    else:
                        errmsg = "sync() duplicate simulator '%s' listed" % s.name
                    log.error(errmsg)
                    raise ValueError(errmsg)
                else:
                    s._insync = self
                    self._local_sims[s.name] = s
                    self._all_sims[s.name] = sync._simulus.comm_rank
                    if s.now > now_max: now_max = s.now
            else:
                errmsg = "sync() expects a list of simulators, but %r is not" % s
                log.error(errmsg)
                raise ValueError(errmsg)

        # a synchronized group cannot be empty
        if len(self._local_sims) < 1:
            errmsg = "sync() sims should not be empty"
            log.error(errmsg)
            raise ValueError(errmsg)

        # if this is a global synchronization group (i.e., when
        # enable_spmd is true), we need to learn about the remote
        # simulators (e.g., the ranks at which they reside), and get
        # the maximum simulation time of all simulators in the group
        if self._spmd:
            self._all_sims = sync._simulus.allgather(self._all_sims)
            now_max = sync._simulus.allreduce(now_max, max)

        # find all mailboxes attached to local simulators
        self._lookahead = lookahead
        self._local_mboxes = {} # a map from mailbox names to mailbox instances
        self._all_mboxes = {} # a map from mail name to corresponding simulator name, min_delay and num of partitions
        for sname, sim in self._local_sims.items():
            for mbname, mb in sim._mailboxes.items():
                if mbname in self._local_mboxes:
                    if sim == mb._sim:
                        errmsg = "sync() duplicate mailbox named '%s' in simulator '%s'" % \
                                 (mbname, sname)
                    else:
                        errmsg = "sync() duplicate mailbox name '%s' in simulators '%s' and '%s'" % \
                                 (mbname, sname, mb._sim.name)
                    log.error(errmsg)
                    raise ValueError(errmsg)
                else:
                    self._local_mboxes[mbname] = mb
                    self._all_mboxes[mbname] = (sname, mb.min_delay, mb.nparts)
                    if mb.min_delay < self._lookahead:
                        self._lookahead = mb.min_delay
                        
        # if this is a global synchronization group (i.e., when
        # enable_spmd is true) , we need to learn about the remote
        # mailboxes and the min delays of all mailboxes
        if self._spmd:
            self._all_mboxes = sync._simulus.allgather(self._all_mboxes)
            self._lookahead = sync._simulus.allreduce(self._lookahead, min)

        # lookahead must be strictly positive
        if self._lookahead <= 0:
            errmsg = "sync() expects positive lookahead; " + \
                   "check min_delay of mailboxes in simulators"
            log.error(errmsg)
            raise ValueError(errmsg)

        # bring all local simulators' time to the max now
        for sname, sim in self._local_sims.items():
            if sim.now < now_max:
                sim._run(now_max, True)
        self.now = now_max

        log.info("[r%d] creating sync (enable_smp=%r, enable_spmd=%r): now=%g, lookahead=%g" %
                 (sync._simulus.comm_rank, self._smp, self._spmd, self.now, self._lookahead))
        for sname, simrank in self._all_sims.items():
            log.info("[r%d] >> simulator '%s' => r%d" %
                     (sync._simulus.comm_rank, sname, simrank))
        for mbname, (sname, mbdly, mbparts) in self._all_mboxes.items():
            log.info("[r%d] >> mailbox '%s' => sim='%s', min_delay=%g, nparts=%d" %
                     (sync._simulus.comm_rank, mbname, sname, mbdly, mbparts))

        # ready for next window
        self._remote_msgbuf = defaultdict(list) # a map from rank to list of remote messages
        self._remote_future = infinite_time
        self._local_partitions = None
        self._activated = True

    def run(self, offset=None, until=None, show_runtime_report=False):
        """Process events of all simulators in the synchronized group each in
        timestamp order and advances the simulation time of all simulators 
        synchronously.

        Args:
            offset (float): relative time from now until which each of
                the simulators should advance its simulation time; if
                provided, it must be a non-negative value

            until (float): the absolute time until which each of the
                simulators should advance its simulation time; if
                provided, it must not be earlier than the current time

        The user can specify either 'offset' or 'until', but not both;
        if both 'offset' and 'until' are ignored, the simulator will
        run as long as there are events on the event lists of the
        simulators. Be careful, in this case, the simulation may run
        forever as for some models there may always be future events.

        Each simulator will process their events in timestamp order.
        Synchronization is provided so that messages sent between the
        simulators may not produce causality errors. When this method
        returns, the simulation time of the simulators will advance to
        the designated time, if either 'offset' or 'until' has been
        specified.  All events with timestamps smaller than the
        designated time will be processed. If neither 'offset' nor
        'until' is provided, the simulators will advance to the time
        of the last processed event among all simulators.

        If SPMD is enabled, at most one simulus instance (at rank 0)
        is allowed to specify the time (using 'offset' or 'until').
        All the other simulators must not specify the time.

        """

        # figure out the time, up to which all events will be processed
        upper_specified = 1
        if until == None and offset == None:
            upper = infinite_time
            upper_specified = 0
        elif until != None and offset != None:
            errmsg = "sync.run(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "sync.run(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            upper = self.now + offset
        elif until < self.now:
            errmsg = "sync.run(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: upper = until

        if self._spmd:
            # only rank 0 can specify the upper for global synchronization
            if upper_specified > 0 and sync._simulus.comm_rank > 0:
                errmsg = "sync.run() 'offset' or 'until' allowed only on rank 0"
                log.error(errmsg)
                raise ValueError(errmsg)

            # we conduct a global synchronization to get the upper
            # time for all
            sync._simulus.bcast(0) # run command
            upper = sync._simulus.allreduce(upper, min)
            upper_specified = sync._simulus.allreduce(upper_specified, max)

        if self._local_partitions is None:
            if self._smp:
                # divide the local simulators among the CPU/cores
                sims = list(self._local_sims.keys())
                if self._smp_ways is None:
                    self._smp_ways = mp.cpu_count()
                k, m = divmod(len(sims), self._smp_ways)
                self._local_partitions = list(filter(lambda x: len(x)>0, \
                        (sims[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(self._smp_ways))))
                
                self._local_queues = {} # a map from pid to queue
                self._local_pids = {} # a map from simulator name to pid
                for pid, snames in enumerate(self._local_partitions):
                    self._local_queues[pid] = mp.Queue()
                    for s in snames: self._local_pids[s] = pid

                # start the child processes
                self._child_procs = [mp.Process(target=sync._child_run, args=(self, i)) \
                                     for i in range(1, len(self._local_partitions))]
                for p in self._child_procs: p.start()
            else:
                self._local_partitions = [self._local_sims.keys()]
                self._local_pids = {} # a map from simulator name to pid
                for s in self._local_sims.keys():
                    self._local_pids[s] = 0

        atexit.register(self._run_finish)
        self._smp_run(0, upper, upper_specified)

        if self._simulus.comm_rank > 0:
            while True:
                cmd = self._simulus.bcast(None)
                if cmd == 0: # run command
                    upper = sync._simulus.allreduce(infinite_time, min)
                    upper_specified = sync._simulus.allreduce(0, max)
                    self._smp_run(0, upper, upper_specified)
                elif cmd == 1: # report command
                    self._smp_report(0)
                else: # stop command
                    assert cmd == 2
                    break
        else:
            if show_runtime_report:
                self.show_runtime_report()
                
    def _child_run(self, pid):
        """The child processes running in SMP mode."""
 
        log.info("[r%d] sync._child_run(pid=%d): partitions=%r" %
                 (sync._simulus.comm_rank, pid, self._local_partitions))
        assert self._smp and pid>0

        # if smp is enabled and for all child processes, we need
        # to clear up remote message buffer so that events don't
        # get duplicated on different processes
        self._remote_msgbuf.clear()
        self._remote_future = infinite_time

        while True:
            try:
                cmd = self._local_queues[pid].get()
            except KeyboardInterrupt:
                # we handle the keyboard interrupt here, since Jupyter
                # notebook seems to raise this exception when the
                # kernel is interrupted
                continue
            log.info("[r%d] sync._child_run(pid=%d): recv command %d" %
                     (sync._simulus.comm_rank, pid, cmd))
            if cmd == 0: # run command
                upper, upper_specified = self._local_queues[pid].get()
                self._smp_run(pid, upper, upper_specified)
            elif cmd == 1: # report command
                self._smp_report(pid)
            else: # stop command
                assert cmd == 2
                break

    def _smp_run(self, pid, upper, upper_specified):
        """Run simulators in separate processes."""
        
        log.info("[r%d] sync._smp_run(pid=%d): begins with upper=%g, upper_specified=%r" %
                 (sync._simulus.comm_rank, pid, upper, upper_specified))
        run_sims = self._local_partitions[pid]
                
        if pid == 0:
            for s in range(1, len(self._local_partitions)):
                self._local_queues[s].put(0) # run command
                self._local_queues[s].put((upper, upper_specified))
        
        while True:
            # figure out the start time of the next window (a.k.a.,
            # lower bound on timestamp): it's the minimum of three
            # values: (1) the timestamp of the first event plus the
            # lookahead, (2) the smallest timestamp of messages to be
            # sent to a remote simulator, and (3) the upper time
            horizon = infinite_time
            for s in run_sims:
                t = self._local_sims[s].peek()
                if horizon > t: horizon = t
            if horizon < infinite_time:
                horizon += self._lookahead
            if horizon > self._remote_future:
                horizon = self._remote_future
            if horizon > upper:
                horizon = upper

            # find the next window for all processes on all ranks
            if len(self._local_partitions) > 1:
                if pid > 0:
                    self._local_queues[0].put(horizon)
                else:
                    for s in range(1, len(self._local_partitions)):
                        x = self._local_queues[0].get()
                        if x < horizon: horizon = x
            if self._spmd and pid == 0:
                horizon = sync._simulus.allreduce(horizon, min)
            if len(self._local_partitions) > 1:
                if pid > 0:
                    horizon = self._local_queues[pid].get()
                else:
                    for s in range(1, len(self._local_partitions)):
                        self._local_queues[s].put(horizon)
            #log.debug("[r%d] sync._run(pid='%d'): sync window [%g:%g]" %
            #          (sync._simulus.comm_rank, pid, self.now, horizon))

            # if there's no more event anywhere, and the upper was not
            # specified, it means we can simply stop by now, the
            # previous iteration should have updated the current time
            # to the horizon for the last event
            if horizon == infinite_time and upper_specified == 0:
                break

            # bring all local simulators' time to horizon
            for s in run_sims:
                #log.debug("[r%d] sync._run(): simulator '%s' execute [%g:%g]" %
                #          (sync._simulus.comm_rank, s[-4:], self._local_sims[s].now, horizon))
                self._local_sims[s]._run(horizon, True)
            self.now = horizon

            # distribute remote messages:
            
            # first, gather remote messages from processes
            if len(self._local_partitions) > 1:
                if pid > 0:
                    #log.debug("[r%d] sync._run(pid=%d): put %r to pid 0" %
                    #          (sync._simulus.comm_rank, pid, self._remote_msgbuf))
                    self._local_queues[0].put(self._remote_msgbuf)
                else:
                    for s in range(1, len(self._local_partitions)):
                        x = self._local_queues[0].get()
                        #log.debug("[r%d] sync._run(pid=0): get %r" %
                        #          (sync._simulus.comm_rank, x))
                        for r in x.keys():
                            self._remote_msgbuf[r].extend(x[r])
                        
            # second, distribute via all to all
            if pid == 0:
                if self._spmd:
                    incoming = sync._simulus.alltoall(self._remote_msgbuf)
                else:
                    incoming = self._remote_msgbuf[0]
                #log.debug("[r%d] sync._run(pid=0): all-to-all incoming=%r" %
                #          (sync._simulus.comm_rank, incoming))
            
            # third, scatter messages to target processes
            if len(self._local_partitions) > 1:
                if pid > 0:
                    incoming = self._local_queues[pid].get()
                    #log.debug("[r%d] sync._run(pid=%d): get %r" %
                    #              (sync._simulus.comm_rank, pid, incoming))
                else:
                    pmsgs = defaultdict(list)
                    if incoming is not None:
                        for m in incoming:
                            _, mbname, *_ = m # find destination mailbox name
                            s, *_ = self._all_mboxes[mbname] # find destination simulator name
                            # find destination pid
                            pmsgs[self._local_pids[s]].append(m)
                    for s in range(1, len(self._local_partitions)):
                        self._local_queues[s].put(pmsgs[s])
                        #log.debug("[r%d] sync._run(pid=%d): put %r to pid %d" %
                        #          (sync._simulus.comm_rank, pid, pmsgs[s], s))
                    incoming = pmsgs[0]
                    #log.debug("[r%d] sync._run(pid=%d): keep %r" %
                    #          (sync._simulus.comm_rank, pid, incoming))
            
            if incoming is not None:
                for until, mbname, part, msg in incoming:
                    mbox = self._local_mboxes[mbname]
                    mbox._sim.sched(mbox._mailbox_event, msg, part, until=until)

            # now we can remove the old messages and get ready for next window
            self._remote_msgbuf.clear()
            self._remote_future = infinite_time

            if horizon >= upper: break

        log.info("[r%d] sync._smp_run(pid=%d): finishes with upper=%g, upper_specified=%r" %
                 (sync._simulus.comm_rank, pid, upper, upper_specified))

    def _run_finish(self):
        log.info("[r%d] sync._run_finish() at exit" % sync._simulus.comm_rank)

        if self._simulus.comm_rank ==0:
            self._simulus.bcast(2) # stop command

        if len(self._local_partitions) > 1:
            for s in range(1, len(self._local_partitions)):
                self._local_queues[s].put(2) # stop command
            for p in self._child_procs: p.join()

    def send(self, sim, mbox_name, msg, delay=None, part=0):
        """Send a messsage from a simulator to a named mailbox.

        Args:
            sim (simulator): the simulator from which the message will
                be sent

            name (str): the name of the mailbox to which the message
                is expected to be delivered

            msg (object): a message can be any Python object; however,
                a message needs to be pickle-able as it may be
                transferred between different simulators located on
                separate processes (with different Python interpreter)
                or even on different machines; a message also cannot
                be None
        
            delay (float): the delay with which the message is
                expected to be delivered to the mailbox; if it is
                ignored, the delay will be set to be the min_delay of
                the mailbox; if it is set, the delay value must not be
                smaller than the min_delay of the mailbox
        
            part (int): the partition number of the mailbox to which
                the message will be delivered; the default is zero

        Returns:
            This method returns nothing (as opposed to the mailbox
            send() method); once sent, it's sent, as it cannot be
            cancelled or rescheduled.

        """

        if not self._activated:
            errmsg = "sync.send() called before the synchronized is created"
            log.error(errmsg)
            raise RuntimeError(errmsg)
        if sim is None or not isinstance(sim, simulator):
            errmsg = "sync.send(sim=%r) requires a simulator" % sim
            log.error(errmsg)
            raise ValueError(errmsg)
        if sim.name not in self._local_sims:
            errmsg = "sync.send(sim='%s') simulator not in synchronized group" % sim.name
            log.error(errmsg)
            raise ValueError(errmsg)
        if msg is None:
            errmsg = "sync.send() message cannot be None"
            log.error(errmsg)
            raise ValueError(errmsg)

        if mbox_name in self._all_mboxes:
            sname, min_delay, nparts = self._all_mboxes[mbox_name]
            if delay is None:
                delay = min_delay
            elif delay < min_delay:
                errmsg = "sync.send() delay (%g) less than min_delay (%r)" % \
                         (delay, min_delay)
                log.error(errmsg)
                raise ValueError(errmsg)
            if part < 0 or part >= nparts:
                errmsg = "sync.send(part=%r) out of range (target mailbox '%s' has %d partitions)" % \
                         (part, mbox_name, nparts)
                log.error(errmsg)
                raise IndexError(errmsg)

            # if it's local delivery, send to the target mailbox
            # directly; a local delivery can be one of the two cases:
            # 1) if SMP is disabled (that is, all local simulators are
            # executed on the same process), the target mailbox
            # belongs to one of the local simulators; or 2) if SMP is
            # enabled (that is, all local simulators are executed on
            # separate processes), the target mailbox belongs to the
            # same sender simulator
            if not self._smp and mbox_name in self._local_mboxes or \
               mbox_name in sim._mailboxes:
                mbox = self._local_mboxes[mbox_name]
                until = sim.now+delay
                mbox._sim.sched(mbox._mailbox_event, msg, part, until=until)
                #log.debug("[r%d] sync.send(sim='%s') to local mailbox '%s': msg=%r, delay=%g (until=%g), part=%d" %
                #          (sync._simulus.comm_rank, sim.name[-4:], mbox_name, msg, delay, until, part))
            else:
                until = sim.now+delay
                self._remote_msgbuf[self._all_sims[sname]].append((until, mbox_name, part, msg))
                if self._remote_future > until:
                    self._remote_future = until
                #log.debug("[r%d] sync.send(sim='%s') to remote mailbox '%s' on simulator '%s': msg=%r, delay=%g, part=%d" %
                #          (sync._simulus.comm_rank, sim.name[-4:], mbox_name, sname[-4:], msg, delay, part))
        else:
            errmsg = "sync.send() to mailbox named '%s' not found" % mbox_name
            log.error(errmsg)
            raise ValueError(errmsg)

    @classmethod
    def comm_rank(cls):
        """Return the process rank of this simulus instance."""
        
        # the simulus instance is a class variable
        if not sync._simulus:
            sync._simulus = _Simulus()
        return sync._simulus.comm_rank

    @classmethod
    def comm_size(cls):
        """Return the total number processes."""
        
        # the simulus instance is a class variable
        if not sync._simulus:
            sync._simulus = _Simulus()
        return sync._simulus.comm_size

    def show_runtime_report(self, show_partition=True, prefix=''):
        """Print a report on the runtime performance of running the
        synchronized group. 

        Args:
            show_partition (bool): if it's True (the default), the
                print-out report also contains the processor
                assignment of the simulators

            prefix (str): all print-out lines will be prefixed by this
                string (the default is empty); this would help if one
                wants to find the report in a large amount of output

        """

        if self._spmd and sync._simulus.comm_rank > 0:
            errmsg = "sync.show_runtime_report() allowed only on rank 0"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        if self._local_partitions is None:
            errmsg = "sync.show_runtime_report() called before sync.run()"
            log.error(errmsg)
            raise ValueError(errmsg)

        if self._spmd:
            cmd = sync._simulus.bcast(1) # report command
        self._smp_report(0, show_partition, prefix)

    def _smp_report(self, pid, show_partition=None, prefix=None):
        """Collect statistics and report them."""

        if pid == 0:
            for s in range(1, len(self._local_partitions)):
                self._local_queues[s].put(1) # report command
        
        t1 = time.time()
        run_sims = self._local_partitions[pid]
        sync_rt = {
            "start_clock": time.time(),
            "sims": self._local_pids.copy(),
            "scheduled_events": 0,
            "cancelled_events": 0,
            "executed_events": 0,
            "initiated_processes": 0,
            "cancelled_processes": 0,
            "process_contexts": 0,
            "terminated_processes": 0,
        }
        for s in run_sims:
            rt = self._local_sims[s]._runtime
            if rt["start_clock"] < sync_rt["start_clock"]:
                sync_rt["start_clock"] = rt["start_clock"]
            sync_rt["scheduled_events"] += rt["scheduled_events"]
            sync_rt["cancelled_events"] += rt["cancelled_events"]
            sync_rt["executed_events"] += rt["executed_events"]
            sync_rt["initiated_processes"] += rt["initiated_processes"]
            sync_rt["cancelled_processes"] += rt["cancelled_processes"]
            sync_rt["process_contexts"] += rt["process_contexts"]
            sync_rt["terminated_processes"] += rt["terminated_processes"]
            
        if len(self._local_partitions) > 1:
            if pid > 0:
                self._local_queues[0].put(sync_rt)
            else:
                for s in range(1, len(self._local_partitions)):
                    rt = self._local_queues[0].get()
                    if rt["start_clock"] < sync_rt["start_clock"]:
                        sync_rt["start_clock"] = rt["start_clock"]
                    sync_rt["scheduled_events"] += rt["scheduled_events"]
                    sync_rt["cancelled_events"] += rt["cancelled_events"]
                    sync_rt["executed_events"] += rt["executed_events"]
                    sync_rt["initiated_processes"] += rt["initiated_processes"]
                    sync_rt["cancelled_processes"] += rt["cancelled_processes"]
                    sync_rt["process_contexts"] += rt["process_contexts"]
                    sync_rt["terminated_processes"] += rt["terminated_processes"]

        if pid == 0 and self._spmd:
            all_rts = sync._simulus.gather(sync_rt)
            if self._simulus.comm_rank == 0:
                sync_rt = all_rts[0]
                for rt in all_rts[1:]:
                    if rt["start_clock"] < sync_rt["start_clock"]:
                        sync_rt["start_clock"] = rt["start_clock"]
                    sync_rt["sims"].update(rt["sims"])
                    sync_rt["scheduled_events"] += rt["scheduled_events"]
                    sync_rt["cancelled_events"] += rt["cancelled_events"]
                    sync_rt["executed_events"] += rt["executed_events"]
                    sync_rt["initiated_processes"] += rt["initiated_processes"]
                    sync_rt["cancelled_processes"] += rt["cancelled_processes"]
                    sync_rt["process_contexts"] += rt["process_contexts"]
                    sync_rt["terminated_processes"] += rt["terminated_processes"]

        if pid == 0 and self._simulus.comm_rank == 0:
            print('%s*********** sync group performance metrics ***********' % prefix)
            if show_partition:
                print('%spartitioning information (simulator assignment):' % prefix)
                for sname, simrank in self._all_sims.items():
                    print("%s  '%s' on rank %d proc %d" % (prefix, sname, simrank, sync_rt["sims"][sname]))
            t = t1-sync_rt["start_clock"]
            print('%sexecution time: %g' % (prefix,t))
            print('%sscheduled events: %d (rate=%g)' %
                  (prefix, sync_rt["scheduled_events"], sync_rt["scheduled_events"]/t))
            print('%sexecuted events: %d (rate=%g)' %
                  (prefix, sync_rt["executed_events"], sync_rt["executed_events"]/t))
            print('%scancelled events: %d' % (prefix, sync_rt["cancelled_events"]))
            print('%screated processes: %d' % (prefix, sync_rt["initiated_processes"]))
            print('%sfinished processes: %d' % (prefix, sync_rt["terminated_processes"]))
            print('%scancelled processes: %d' % (prefix, sync_rt["cancelled_processes"]))
            print('%sprocess context switches: %d' % (prefix, sync_rt["process_contexts"]))
