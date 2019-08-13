# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-08-12 04:52:42 liux>
###############################################################

import random, uuid, time
from collections import deque

from .utils import *
from .trappable import *
from .trap import *
from .semaphore import *
from .resource import *
from .event import *
from .process import *
from .simulus import *
from .resource import *
from .store import *
from .mailbox import *

__all__ = ["simulator", "infinite_time", "minus_infinite_time"]

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class simulator:
    """A simulator instance.

    Each simulator instance has an independent timeline (i.e., event
    list) on which events are scheduled and executed in timestamp
    order. In parallel simulation, each simulator instance is also
    known as a logical process (LP).

    Simulus supports multiple simulators to run simultaneously. Each
    simulator can run separately, or can be synchronized and run
    collectively as part of a parallel discrete-event simulation.

    Each simulator can have an optional name, which however must be
    globally unique. Or, it can remain anonymous. Each simulator
    maintains an event list and a simulation clock.

    """

    def __init__(self, name=None, init_time=0):
        """Create a simulator.

        One can repeatedly create as many simulators as needed. A
        simulator maintains its own event list (along with all
        scheduled functions and processes) and keeps track of the
        simulation time.

        Args:
            name (string): a name of the simulator; if ignored, the
                system will generate a unique name for the simulator;
                if specified, the name needs to be unique so that the
                name can be used to retrieve the corresponding
                simulator instance; the name is also used to determine
                the seed of the pseudo-random generator attached to
                the simulator

            init_time (float): the optional start time of the
                simulator; if unspecified, the default is zero

        Returns:
            This function returns the newly created simulator.

        """

        # note simulus is implemented as a singleton
        self._simulus = _Simulus()

        self._insync = None
        self._mailboxes = {}
        
        if name is None:
            self.name = self._simulus.unique_name()
        else:
            self.name = name
        self._simulus.register_simulator(name, self)
        log.info("[r%d] creating simulator '%s'" % (self._simulus.comm_rank, self.name))

        self.init_time = self.now = init_time
        self._eventlist = _EventList_()
        self._theproc = None
        self._readyq = deque()
        self._rng = None
        #self._fast_rng = None

        # performance statistics
        self._runtime = {
            "start_clock": time.time(),
            "scheduled_events": 0,
            "cancelled_events": 0,
            "executed_events": 0,
            "initiated_processes": 0,
            "cancelled_processes": 0,
            "process_contexts": 0,
            "terminated_processes": 0,
        }

    ###################################
    # direct event scheduling methods #
    ###################################
        
    def sched(self, func, *args, offset=None, until=None, name=None, repeat_intv=None, **kwargs):
        """Schedule an event.

        An event in simulus is represented as a function invoked in
        the simulated future. 
        
        Args: 
            func (function): the event handler, which is a
                user-defined function

            args (list): the positional arguments as a list to be
                passed to the scheduled function (the event handler)
                once the function is invoked at the scheduled time

            offset (float): relative time from now at which the event
                is scheduled to happen; if provided, must be a
                non-negative value

            until (float): the absolute time at which the event is
                scheduled to happen; if provided, it must not be
                earlier than the current time; note that either
                'offset' or 'until' can be used, but not both; if both
                are ignored, it's assumed to be the current time

            name (string): an optional name for the event

            repeat_intv (float): if provided, the event will be
                repeated with the given time interval; the interval
                must be a strictly postive value

            kwargs (dict): the keyworded arguments as a dictionary to
                be passed to the scheduled function (the event
                handler), once the function is invoked at the
                scheduled time

        Returns: 
            This method returns a direct scheduling event (which is an
            opaque object to the user), with which the user can cancel
            the event, or reschedule the event, or apply conditional
            wait on the event if needed

        """

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            errmsg = "simulator.sched(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.sched(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "simulator.sched(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        if repeat_intv is not None and repeat_intv <= 0:
            errmsg = "simulator.sched(repeat_intv=%r) non-positive repeat interval" % repeat_intv
            log.error(errmsg)
            raise ValueError(errmsg)
            
        #log.debug("[r%d] simulator '%s' schedule event at time=%g from now=%g" %
        #          (self._simulus.comm_rank, self.name[-4:], time, self.now))
        self._runtime["scheduled_events"] += 1
        e = _DirectEvent(self, time, func, name, repeat_intv, args, kwargs)
        self._eventlist.insert(e)
        return e

    def cancel(self, o):
        """Cancel a scheduled event or kill a process.

        This method takes one argument, which is the return value from
        sched() or process(). In either case, it's an opaque object to
        the user, which can be either an event or process. If it's an
        event, when cancelled, the previously scheduled function will
        no longer be invoked at the expected time. Note that the
        method has no effect if the event that has already happened.
        If the argument is a process, it's the same as to kill the
        process using the kill() method.

        """
        
        if o is None:
            errmsg = "simulator.cancel(o=None) requires event or process."
            log.error(errmsg)
            raise ValueError(errmsg)
        elif isinstance(o, _Event):
            try:
                self._eventlist.cancel(o)
            except Exception:
                # the event is not in the event list; that's OK
                #log.debug("[r%d] simulator '%s' cancel non-active event from now=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], self.now, self.now))
                pass
            else:
                #log.debug("[r%d] simulator '%s' cancel event at time=%g from now=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], o.time, self.now))
                self._runtime["cancelled_events"] += 1
        elif isinstance(o, _Process):
            self.kill(o)
        else:
            errmsg = "simulator.cancel(o=%r) not an event or process" % o
            log.error(errmsg)
            raise TypeError(errmsg)

    def resched(self, e, offset=None, until=None):
        """Reschedule an event.

        One can change the time of a scheduled event using this
        method. When rescheduled, the previously scheduled function
        will be invoked at the new designated time. If the event
        already happens, this method would have no effect.

        This method takes at least one argument, which is the return
        value from sched(). Additionally, one can either provide an
        'offset' time from now or an absolute time 'until', but not
        both. If both 'offset' and 'until' are ignored, the
        rescheduled event is for the current time. The time should
        never be earlier than the current time.

        This method returns the same event upon having successfully
        rescheduled the event. Otherwise, it returns None.

        """

        if not isinstance(e, _Event):
            errmsg = "simulator.resched(e=%r) not an event" % e
            log.error(errmsg)
            raise TypeError(errmsg)

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            e.time = self.now
        elif until != None and offset != None:
            errmsg = "simulator.resched(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.resched(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            e.time = self.now + offset
        elif until < self.now:
            errmsg = "simulator.resched(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: e.time = until

        try:
            self._eventlist.update(e)
            #log.debug("[r%d] simulator '%s' reschedule event to time=%g from now=%g" %
            #          (self._simulus.comm_rank, self.name[-4:], e.time, self.now))
            return e
        except Exception:
            # the event already happened as it's not in the event list
            #log.debug("[r%d] simulator '%s' reschedule non-active event from now=%g" %
            #          (self._simulus.comm_rank, self.name[-4:], self.now))
            return None


    ##############################
    # process scheduling methods #
    ##############################
    
    def process(self, proc, *args, offset=None, until=None, name=None,
                prio=0, prio_args=None, **kwargs):
        """Create a process and schedule its execution.

        A process is a separate thread of control. During its
        execution, a process can sleep for some time, or wait for
        certain conditions to become true (on a trap or semaphore or
        others). In any case, the process can be suspended and the
        simulation time may advance until it resumes execution.

        This method creates a process and schedule for the process to
        run (from a starting function) in the simulated future
        (including now).
        
        Args:
            proc (function): the starting function of the process,
                which can be an arbitrary user-defined function.

            args (list): the positional arguments as a list to be
                passed to the starting function when the process
                begins at the scheduled time

            offset (float): relative time from now at which the
                process is expected to start running; if provided, it
                must be a non-negative value (zero is OK)

            until (float): the absolute time at which the process is
                expected to start running; if provided, it must not be
                earlier than the current time; note that either
                'offset' or 'until' can be used, but not both; if both
                are ignored, it is assumed to be the current time

            name (string): an optional name for the process

            prio: the priority of the process (which is default to be
                zero). A priority can be any numerical value: a lower
                value means higher priority. The argument here can
                also be a function, which will be invoked when needed
                by the system to prioritize waiting processes (e.g.,
                when qdis is set to be QDIS.PRIORITY for a resource or
                facility). If it is indeed a fucntion, the function
                may take a list of arguments (provided by prio_args)
                and should return a numerical value

            prio_args: the user-defined arguments to the function
                specifed by prio; if provided, the arguments must be
                placed inside a list

            kwargs (dict): the keyworded arguments as a dictionary to
                be passed to the starting function when the process
                begins at the scheduled time

        Returns:
            This method returns the process being created (it's an
            opaque object to the user); the user can use it to check
            whether the process is terminated, to join the process
            (i.e., to wait for its termination), or even to explicitly
            kill the process.

        """
        
        # figure out the time to start running the process
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            errmsg = "simulator.process(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.process(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "simulator.process(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        #log.debug("[r%d] simulator '%s' schedule process event at time=%g from now=%g" %
        #          (self._simulus.comm_rank, self.name[-4:], time, self.now))
        self._runtime["scheduled_events"] += 1
        self._runtime["initiated_processes"] += 1
        p = _Process(self, name, proc, args, kwargs, prio, prio_args)
        e = _ProcessEvent(self, time, p, name)
        self._eventlist.insert(e)
        return p

    def cur_process(self):
        """Return the current running process, or None if we are not in a
        process context."""
        
        assert self._theproc is None or \
            self._theproc.state == _Process.STATE_RUNNING
        return self._theproc
    
    def terminated(self, p):
        """Check whether the given process has terminated.""" 

        if not isinstance(p, _Process):
            errmsg = "simulator.terminated(p=%r) not a process" % p
            log.error(errmsg)
            raise TypeError(errmsg)
        return p.state == _Process.STATE_TERMINATED

    def kill(self, p=None):
        """Kill a process.

        The process to be killed should be provided as the only
        argument. If it's ignored, it's assumed to be the current
        process, which means the process is trying to kill itself. In
        this case, this method must be called within a process context
        (not in an event handler or in the main function).

        """

        if p is not None:
            # kill another process
            if not isinstance(p, _Process):
                errmsg = "simulator.kill(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)

            if p.state != _Process.STATE_TERMINATED:
                # if the process has not been terminated already
                #log.debug("[r%d] simulator '%s' kill process at time=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], self.now))
                self._runtime["cancelled_processes"] += 1
                p.deactivate(_Process.STATE_TERMINATED)
                p.trap.trigger()
            else:
                # otherwise, it's already killed; we do nothing
                #log.debug("[r%d] simulator '%s' kill non-active process at time=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], self.now))
                pass
        else:
            # kill oneself
            p = self.cur_process()
            if p is None:
                errmsg = "simulator.kill() outside process context"
                log.error(errmsg)
                raise RuntimeError(errmsg)
            #log.debug("[r%d] simulator '%s' self-kill process at time=%g" %
            #          (self._simulus.comm_rank, self.name[-4:], self.now))
            self._runtime["cancelled_processes"] += 1
            p.terminate()

    def get_priority(self, p=None):
        """Get the priority of a process.

        A process should be provided as the only argument. If it's
        ignored, it's assumed to be the current process.

        """

        if p is not None:
            # get priority of another process
            if not isinstance(p, _Process):
                errmsg = "simulator.get_priority(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)
        else:
            # get the priority of the current process
            p = self.cur_process()
            if p is None:
                errmsg = "simulator.get_priority() outside process context"
                log.error(errmsg)
                raise RuntimeError(errmsg)
        return p.get_priority()

    def set_priority(self, prio, prio_args=None, p=None):
        """Set the priority of a process.

        Args:
            prio: the new priority of the process. A priority can be
                any numerical value: a lower value means higher
                priority. The argument here can be a function, which
                is invoked when needed by the system to prioritize
                waiting processes (e.g., when qdis is set to be
                QDIS.PRIORITY for a resource or facility). If it is
                indeed a fucntion, the function may take a list of
                arguments (provided by prio_args) and should return a
                numerical value

            prio_args: the user-defined arguments to the function
                specifed by prio; if provided, the arguments must be
                placed inside a list

            p: the process to change priority; if ignored, it's
                assumed to be the current process

        """

        if p is not None:
            # set priority of another process
            if not isinstance(p, _Process):
                errmsg = "simulator.set_priority(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)
        else:
            # set the priority of the current process
            p = self.cur_process()
            if p is None:
                errmsg = "simulator.set_priority() outside process context"
                log.error(errmsg)
                raise RuntimeError(errmsg)
        p.set_priority(prio, prio_args)

    def sleep(self, offset=None, until=None):
        """A process blocks for a certain time duration.

        This method must be called within a process context (not in an
        event handler or in the main function). The process will be
        put on hold for the given period of time. It will resume
        execution after the time period has passed.

        Note that sleep cannot be interrupted, although the process
        can be killed by another process when it's asleep. For
        interruptable sleep, use the wait() method.

        Args:
            offset (float): relative time from now until which the
                process will be put on hold; if provided, it must be a
                non-negative value

            until (float): the absolute time at which the process is
                expected to resume execution; if provided, it must not
                be earlier than the current time; either 'offset' or
                'until' must be provided, but not both

        This method does not return a value. When it returns, the
        process has already resumed execution.

        """
        
        # must be called within process context
        p = self.cur_process()
        if p is None:
            errmsg = "simulator.sleep() outside process context"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        # figure out the expected wakeup time
        if until == None and offset == None:
            errmsg = "simulator.sleep() missing time specification"
            log.error(errmsg)
            raise ValueError(errmsg)
        elif until != None and offset != None:
            errmsg = "simulator.sleep(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.sleep(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "simulator.sleep(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        # the control will be switched back to the simulator's main
        # event loop (i.e., the process will be putting on hold)...
        p.sleep(time)
        # the control comes back now; the process resumes execution...


    #########################################
    # trappables, resources, and facilities #
    #########################################
    
    def trap(self):
       """Create and return a trap for inter-process communication."""
       return Trap(self)

    def semaphore(self, initval=0, qdis=QDIS.FIFO):
        """Create a semaphore for inter-process communication.

        Args:
            initval (int): the initial value of the semaphore; the
                value must be non-negative; the default is zero

            qdis (int): the queuing discipline for the waiting
                processes, which can be selected from QDIS.FIFO (first
                in first out), QDIS.LIFO (last in first out),
                QDIS.SIRO (service in random order), or QDIS.PRIORITY
                (based on process priority); if ignored, the default
                is QDIS.FIFO

        Returns:
            This method returns a newly created semaphore.

        """

        if initval < 0:
            errmsg = "simulator.semaphore(initval=%r) negative init value" % initval
            log.error(errmsg)
            raise ValueError(errmsg)
        if qdis < QDIS.FIFO or qdis > QDIS.PRIORITY:
            errmsg = "simulator.semaphore(qdis=%r) unknown queuing discipline" % qdis
            log.error(errmsg)
            raise ValueError(errmsg)
        return Semaphore(self, initval, qdis)

    def resource(self, capacity=1, qdis=QDIS.FIFO, name=None, collect=None):
        """Create and return a resource.

        Args:
            capacity (int): the capacity of the resource; the value
                must be a positive integer; the default is one

            qdis (int) : the queuing discipline for the waiting
                processes, which can be selected from QDIS.FIFO (first
                in first out), QDIS.LIFO (last in first out),
                QDIS.SIRO (service in random order), or QDIS.PRIORITY
                (based on process priority); if ignored, the default
                is QDIS.FIFO

            name (string): the optional name of the resource

            collect (DataCollector): the optional collector for statistics

        Returns:
            This method returns the newly created resource.

        The DataCollector, if provided, accepts the following values:
            * **arrivals**: timemarks (time of job arrivals)
            * **services**: timemarks (time of jobs entering services)
            * **reneges**: timemarks (time of jobs reneging from queue)
            * **departs**: timemarks (time of jobs departing from system)
            * **inter_arrivals**: dataseries (job inter-arrival time)
            * **queue_times**: dataseries (time of jobs in queue before servicing)
            * **renege_times**: dataseries (time of jobs in queue before reneging)
            * **service_times**: dataseries (time of jobs in service)
            * **system_times**: dataseries (time of jobs in system)
            * **in_systems**: timeseries (number of jobs in system)
            * **in_services**: timeseries (number of jobs in service)
            * **in_queues**: timeseries (number of jobs in queue)

        """

        if not isinstance(capacity, int):
            errmsg = "simulator.resource(capacity=%r) non-integer capacity" % capacity
            log.error(errmsg)
            raise TypeError(errmsg)
        if capacity <= 0:
            errmsg = "simulator.resource(capacity=%r) non-positive capacity" % capacity
            log.error(errmsg)
            raise ValueError(errmsg)
        if qdis < QDIS.FIFO or qdis > QDIS.PRIORITY:
            errmsg = "simulator.resource(qdis=%r) unknown queuing discipline" % qdis
            log.error(errmsg)
            raise ValueError(errmsg)
        return Resource(self, name, capacity, qdis, collect)

    def store(self, capacity=1, initlevel=0, initobj=None,
              p_qdis=QDIS.FIFO, c_qdis=QDIS.FIFO, name=None, collect=None):
        """Create and return a store.

        Args:
            capacity (int, float): the capacity of the store; the
                value must be positive; the default is one

            initlevel (int, float): the initial storage level; the
                value must be non-negative and it cannot be larger
                than the capacity; the default is zero

            initobj (object or list/tuple): initial objects to be
                deposited in the store (if real objects are going to
                be used for the store operation), in which case the
                number of objects must match with the initlevel

            p_qdis (int): the queuing discipline for the waiting
                producer processes (putters), which can be selected
                from QDIS.FIFO (first in first out), QDIS.LIFO (last
                in first out), QDIS.SIRO (service in random order), or
                QDIS.PRIORITY (based on process priority); if ignored,
                the default is QDIS.FIFO

            c_qdis (int): the queuing discipline for the waiting
                consumer processes (getter); if ignored, the default
                is QDIS.FIFO

            name (string): the optional name of the store

            collect (DataCollector): the optional data collector for
                statistics

        Returns:
            This method returns the newly created store.

        The DataCollector, if provided, accepts the following values:
            * **puts**: timeseries (time and amount of put requests)
            * **put_times**: dataseries (waiting time to put items)
            * **put_queues**: timeseries (number of processes waiting to put items)
            * **gets**: timeseries (time and amount of get requests)
            * **get_times**: dataseries (waiting time to get items)
            * **get_queues**: timeseries (number of processes waiting to get items)
            * **levels**: timeseries (storage levels)

        """

        if capacity <= 0:
            errmsg = "simulator.store(capacity=%r) non-positive capacity" % capacity
            log.error(errmsg)
            raise ValueError(errmsg)
        if initlevel < 0 or initlevel > capacity:
            errmsg = "simulator.store(capacity=%r, initlevel=%r) out of bound" % (capacity, initlevel)
            log.error(errmsg)
            raise ValueError(errmsg)
        if p_qdis < QDIS.FIFO or p_qdis > QDIS.PRIORITY:
            errmsg = "simulator.store(p_qdis=%r) unknown queuing discipline" % p_qdis
            log.error(errmsg)
            raise ValueError(errmsg)
        if c_qdis < QDIS.FIFO or c_qdis > QDIS.PRIORITY:
            errmsg = "simulator.store(c_qdis=%r) unknown queuing discipline" % c_qdis
            log.error(errmsg)
            raise ValueError(errmsg)

        return Store(self, capacity, initlevel, initobj, name, p_qdis, c_qdis, collect)

    def mailbox(self, name=None, min_delay=0, nparts=1, collect=None):
        """Create and return a mailbox.

        Args:
            name (string): an optional name of the mailbox

            min_delay (float): the minimum delay for messages to be
                transported through the mailbox

            nparts (int): the number of compartments/partitions; the
                value must be a positive integer; the default is one

            collect (DataCollector): the optional collector for
                statistics; when provided, if the number of partitions
                is greater than one, it should be a list or tuple of
                DataCollectors, one for each partition; if there's
                only one partition, it should be the DataCollector
                itself (as opposed to be wrapped in a list)

        Returns:
            This method returns the newly created mailbox.

        The DataCollector, if provided, accepts the following values:
            * **arrivals**: timemarks (time of message arrivals)
            * **retrievals**: timemarks (time of message retrieval requests)
            * **messages**: timeseries (number of messages in mailbox)

        """

        if self._insync:
            errmsg = "simulator.mailbox() disabled for synchronized group"
            log.error(errmsg)
            raise RuntimeError(errmsg)
        
        if not isinstance(nparts, int) or nparts <= 0:
            errmsg = "simulator.mailbox(nparts=%r) non-positive integer" % nparts
            log.error(errmsg)
            raise TypeError(errmsg)
        if min_delay < 0:
            errmsg = "simulator.mailbox(min_delay=%r) negative min_delay" % min_delay
            log.error(errmsg)
            raise ValueError(errmsg)

        #if name is None:
        #    name = self._simulus.unique_name()
        if name is not None and name in self._mailboxes:
            errmsg = "simulator.mailbox(name=%s) duplicate name" % name
            log.error(errmsg)
            raise ValueError(errmsg)
        mb = Mailbox(self, nparts, min_delay, name, collect)
        if name is None:
            log.info("[r%d] simulator '%s' creating anonymous mailbox" %
                     (self._simulus.comm_rank, self.name))
        else:
            self._mailboxes[name] = mb
            log.info("[r%d] simulator '%s' creating mailbox '%s'" %
                     (self._simulus.comm_rank, self.name, name))
        return mb


    ####################
    # conditional wait #
    ####################

    def wait(self, traps, offset=None, until=None, method=all):
        """Conditional wait on one or more trappables for some time.

        This method must be called within a process context (not in an
        event handler or in the main function). The process will be
        put on hold waiting for one or a list of trappables and for a
        given amount of time if specified. The process will resume
        execution after the given condition is met.

        Args:
            traps (trappable, list, tuple): either a trappable (an
                event, a process, a trap, a semaphore, or one of the
                resources and facilities), or a list/tuple of
                trappables

            offset (float): relative time from now until which the
                process will wait at the latest; if provided, it must
                be a non-negative value

            until (float): the absolute time at which the process is
                expected to resume execution at the latest; if
                provided, it must not be earlier than the current
                time; either 'offset' or 'until' can be provided, but
                not both; if both 'offset' and 'until' are ignored,
                there will be no time limit on the wait

            method (function): can be either 'all' (the default) or
                'any'; if 'all', all trappables must be triggered
                before this process can resume execution (or timed
                out); if 'any', one of the trappables must be
                triggered before this process can resume execution (or
                timed out); this parameter would have no effect if
                only one trappable (whether it's standalone or as part
                of the list) is provided as the first argument

        Returns:
            The return value of this method is a tuple that consists
            of two elements: the first element is to indicate which of
            the trappables have been triggered or not; the second
            element of tuple is to indicate whether timeout happens.

            If the first argument when calling this method is only one
            trappable (not in a list or tuple), the first element of
            the returned tuple will be simply a scalar value, True or
            False, depending on whether the trappable has been
            triggered or not.

            If the first argument when calling this method is a list
            or a tuple of trappables (even if the list or the tuple
            has only one element), the first element of the returned
            tuple will be a list of booleans, each of which indicates
            whether the corresponding trappable has been triggered or
            not.

        """

        # must be called within process context
        p = self.cur_process()
        if p is None:
            errmsg = "simulator.wait() outside process context"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        # sanity check of the first argument: one trappable or a
        # list/tuple of trappables
        if isinstance(traps, Trappable):
            single_trappable = True
            traps = [traps]
        elif isinstance(traps, (list, tuple)):
            single_trappable = False
            if len(traps) == 0:
                errmsg = "simulator.wait() empty list of trappables"
                log.error(errmsg)
                raise ValueError(errmsg)
            for t in traps:
                if not isinstance(t, Trappable):
                    errmsg = "simulator.wait() not a trappable in list"
                    log.error(errmsg)
                    raise TypeError(errmsg)
        else:
            errmsg = "simulator.wait() one trappable or a list of trappables expected"
            log.error(errmsg)
            raise TypeError(errmsg)
        
        # figure out the expected wakeup time
        if until == None and offset == None:
            time = infinite_time
        elif until != None and offset != None:
            errmsg = "simulator.wait(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.wait(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "simulator.wait(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        # only two methods are allowed
        if method != all and method != any:
            errmsg = "simulator.wait() with unknown method"
            log.error(errmsg)
            raise ValueError(errmsg)

        # a mask indicating whether the corresponding trap has been
        # triggered or not; if it is, there's no need to wait
        trigged = [not t._try_wait() for t in traps]
        for i, t in enumerate(traps):
            if trigged[i]: 
                t._commit_wait()
        
        # true_traps are the list of trappables that will be really
        # triggered (processes and events don't get triggered, but
        # their attached traps are); note this has to be called after
        # _try_wait() has been called on events
        true_traps = [t._true_trappable() for t in traps]

        timedout = False
        e = None # this will be the timeout event

        p.acting_trappables.clear()
        while not method(trigged):
            # the wait condition hasn't been satisfied; the process
            # will be suspended
            
            # make sure we schedule the timeout event, only once
            if e is None and time < infinite_time:
                #log.debug("[r%d] simulator '%s' schedule timeout event at time=%g from now=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], time, self.now))
                self._runtime["scheduled_events"] += 1
                e = _ProcessEvent(self, time, p, p.name)
                self._eventlist.insert(e)
            
            p.suspend()

            # update the mask (this is a circuitous way to find out
            # which trap in the list of traps is responsible for
            # unblocking the process at this time)
            for t in p.acting_trappables:
                # if the acting trappables are not in expected list of
                # traps, something is wrong (in which case an
                # exception will be raised)
                i = true_traps.index(t)
                traps[i]._commit_wait()
                trigged[i] = True
            p.acting_trappables.clear()

            # check if we are timed out
            if e is not None and not self._eventlist.current_event(e):
                timedout = True
                break
            
        # cancel the future timeout event
        if e is not None and not timedout:
            #log.debug("[r%d] simulator '%s' cancel timeout event at time=%g from now=%g" %
            #          (self._simulus.comm_rank, self.name[-4:], e.time, self.now))
            self._runtime["cancelled_events"] += 1
            self._eventlist.cancel(e)

        # cancel the try-wait for those untriggered trappables
        [t._cancel_wait() for i, t in enumerate(traps) if not trigged[i]]
         
        # the wait condition has been satisfied, return accordingly
        if single_trappable:
            return trigged[0], timedout
        else:
            return trigged, timedout
        # note this is how to find the remaining untriggered traps
        # r = [t for i, t in enumerate(traps) if not trigged[i]]
        

    ######################
    # running simulation #
    ######################
    
    def run(self, offset=None, until=None):
        """Run simulation and process events.

        This method processes the events in timestamp order and
        advances the simulation time accordingly.

        Args:
            offset (float): relative time from now until which the
                simulator should advance its simulation time; if
                provided, it must be a non-negative value

            until (float): the absolute time until which the simulator
                should advance its simulation time; if provided, it
                must not be earlier than the current time

        The user can specify either 'offset' or 'until', but not both;
        if both 'offset' and 'until' are ignored, the simulator will
        run as long as there are events on the event list. Be careful,
        in this case, the simulator may run forever for some models as
        there could always be events scheduled in the future.

        The simulator will process all events in timestamp order. When
        the method returns, the simulation time will advance to the
        designated time, if either 'offset' or 'until' is specified.
        All events with timestamps smaller than the designated time
        will be processed. If neither 'offset' nor 'until' is
        provided, the simulator will advance to the time of the last
        processed event.

        """

        if self._insync:
            self._insync.run(offset, until)
            return
        
        # figure out the horizon, up to which all events will be processed
        upper_specified = True
        if until == None and offset == None:
            upper = infinite_time
            upper_specified = False
        elif until != None and offset != None:
            errmsg = "simulator.run(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "simulator.run(offset=%r) negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            upper = self.now + offset
        elif until < self.now:
            errmsg = "simulator.run(until=%r) earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: upper = until

        self._run(upper, upper_specified)

    def _run(self, upper, updating_until):
        """Run simulation up to the given time 'until' (by processing all
        events with timestamps less than 'until'), and if
        'updating_until' is true, update the simulation clock to
        'until' after processing all the events."""
        
        # this is the main event loop of the simulator!
        while len(self._eventlist) > 0:
            t = self._eventlist.get_min()
            if t >= upper: break
            self._process_one_event()

        # after all the events, make sure we don't wind back the clock
        # if upper (set by either 'until' or 'offset') has been
        # explicitly specified by the user
        if updating_until:
            self._eventlist.last = upper
            self.now = upper

    def step(self):
        """Process only one event.

        This method processes the next event and advances the
        simulation time to the time of the next event. If no event is
        available on the event list, this method does nothing.

        """

        if self._insync:
            errmsg = "simulator.step() disabled for synchronized group"
            log.error(errmsg)
            raise RuntimeError(errmsg)
        
        # this is the main event loop
        if len(self._eventlist) > 0:
            self._process_one_event();
            
    def peek(self):
        """Return the time of the next scheduled event, or infinity if no
        future events are available."""
        
        if len(self._eventlist) > 0:
            return self._eventlist.get_min()
        else:
            return infinite_time

    def _process_one_event(self):
        """Process one event on the event list, assuming there is a least one
        event on the event list."""
        
        e = self._eventlist.delete_min()
        self.now = e.time
        #log.debug("[r%d] simulator '%s' execute event at time %g" %
        #          (self._simulus.comm_rank, self.name[-4:], self.now))
        self._runtime["executed_events"] += 1

        # trigger the trap if the event already has a trap; this is a
        # memory-saving mechanism: only those events that the user is
        # explicitly interested in (used in the simulator's wait()
        # method) are attached with a trap
        if e.trap is not None:
            e.trap.trigger()
            
        if isinstance(e, _DirectEvent):
            if e.repeat_intv is not None:
                # note that a renewed event is not trappable
                e = e.renew(e.time+e.repeat_intv)
                #log.debug("[r%d] simulator '%s' schedule repeated event at time=%g from now=%g" %
                #          (self._simulus.comm_rank, self.name[-4:], e.time, self.now))
                self._runtime["scheduled_events"] += 1
                self._eventlist.insert(e)
            e.func(*e.args, **e.kwargs)
        elif isinstance(e, _ProcessEvent):
            e.proc.activate()
        else:
            errmsg = "unknown event type: " + str(e)
            log.error(errmsg)
            raise RuntimeError(errmsg)

        # processes are run only from the main loop!!
        while len(self._readyq) > 0:
            p = self._readyq.popleft()
            if p.state == _Process.STATE_RUNNING:
                self._theproc = p
                #log.debug("[r%d] simulator '%s' context switch at time %g" %
                #          (self._simulus.comm_rank, self.name[-4:], self.now))
                self._runtime["process_contexts"] += 1
                p.run()
            else:
                # process is killed while in the ready queue
                assert p.state == _Process.STATE_TERMINATED
        self._theproc = None

    def rng(self):
        """Return the pseudo-random number generator attached to this
        simulator. It's a random.Random instance (Mersenne twister)."""

        if self._rng is None:
            u = uuid.uuid3(self._simulus.namespace, self.name)
            self._rng = random.Random(int(u.int/2**32))
        return self._rng

    def sync(self):
        """Return the synchronized group to which this simulator belongs to,
        or None if the simulator does not belong to any group."""
        return self._insync
    
    # def fast_rng(self):
    #     """Return a fast pseudo-random number generator attached to this
    #     simulator. It's a Lehmer random number generator, which has a
    #     very short period. Use with caution!"""
    #     class _FastRNG(random.Random):
    #         M = 2147483647
    #         A = 48271
    #         A256 = 22925
    #         Q = int(M/A)
    #         R = M%A
    #         def __init__(self, initial_seed):
    #             self._seed = initial_seed
    #         def random(self):
    #             t = _FastRNG.A*(self._seed%_FastRNG.Q)-_FastRNG.R*int(self._seed/_FastRNG.Q)
    #             if t > 0: self._seed = t
    #             else: self._seed = t+_FastRNG.M
    #             return float(self._seed)/_FastRNG.M
    #         def seed(self, a):
    #             t = a%_FastRNG.M
    #             if t > 0: self._seed = t
    #             else: self._seed = t+_FastRNG.M
    #         def getstate(self):
    #             return self._seed
    #         def setstate(self, state):
    #             self._seed(state)
    #         #def getrandbits(self, k): pass
    #     if self._fast_rng is None:
    #         u = uuid.uuid3(self._simulus.namespace, self.name)
    #         self._fast_rng = _FastRNG(int(u.int/2**32))
    #     return self._fast_rng

    def show_calendar(self):
        """Print the list of all future events currently on the event
        list. This is an expensive operation and should be used
        responsively, possibly just for debugging purposes."""

        print("list of all future events (num=%d) at time %g on simulator '%s':" %
              (len(self._eventlist), self.now, self.name if self.name else ''))
        for e in sorted(self._eventlist.pqueue.values()):
            print("  %s" % e)

    def show_runtime_report(self, prefix=''):
        """Print a report on the simulator's runtime performance.

        Args:
            prefix (str): all print-out lines will be prefixed by this
                string (the default is empty); this would help if one
                wants to find the report in a large amount of output

        """

        t = time.time()-self._runtime["start_clock"]
        print('%s*********** simulator performance metrics ***********' % prefix)
        print('%ssimulator name: %s' % (prefix, self.name))
        print('%ssimulation time: %g' % (prefix, self.now-self.init_time))
        print('%sexecution time: %g' % (prefix, t))
        print('%ssimulation to real time ratio: %g' % (prefix, (self.now-self.init_time)/t))
        print('%sscheduled events: %d (rate=%g)' %
              (prefix, self._runtime["scheduled_events"], self._runtime["scheduled_events"]/t))
        print('%sexecuted events: %d (rate=%g)' %
              (prefix, self._runtime["executed_events"], self._runtime["executed_events"]/t))
        print('%scancelled events: %d' % (prefix, self._runtime["cancelled_events"]))
        print('%screated processes: %d' % (prefix, self._runtime["initiated_processes"]))
        print('%sfinished processes: %d' % (prefix, self._runtime["terminated_processes"]))
        print('%scancelled processes: %d' % (prefix, self._runtime["cancelled_processes"]))
        print('%sprocess context switches: %d' % (prefix, self._runtime["process_contexts"]))
