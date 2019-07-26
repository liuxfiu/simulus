# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-07-25 17:07:51 liux>
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
from .sync import *
from .resource import *
from .store import *
from .mailbox import *

__all__ = ["simulator", "sync", "infinite_time", "minus_infinite_time"]

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class Simulator:
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

    def __init__(self, name, init_time):
        """A simulator can only be created using the simulator() function."""

        self.name = name
        self.init_time = init_time
        self.now = init_time
        self._eventlist = _EventList_()
        self._theproc = None
        self._readyq = deque()
        self._rng = None
        #self._fast_rng = None

        # performance statistics
        self._runtime_start_clock = time.time()
        self._runtime_scheduled_events = 0
        self._runtime_cancelled_events = 0 
        self._runtime_executed_events = 0
        self._runtime_initiated_processes = 0
        self._runtime_cancelled_processes = 0
        self._runtime_process_contexts = 0
        self._runtime_terminated_processes = 0


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
            errmsg = "sched(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "sched(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "sched(until=%r) must not be earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        if repeat_intv is not None and repeat_intv <= 0:
            errmsg = "sched(repeat_intv=%r) requires positive repeat interval" % repeat_intv
            log.error(errmsg)
            raise ValueError(errmsg)
            
        log.debug('schedule event at time=%g from now=%g' % (time, self.now))
        self._runtime_scheduled_events += 1
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
            errmsg = "cancel(o=None) requires event or process."
            log.error(errmsg)
            raise ValueError(errmsg)
        elif isinstance(o, _Event):
            try:
                self._eventlist.cancel(o)
            except Exception:
                # the event is not in the event list; that's OK
                log.debug('cancel non-active event from now=%g' % self.now)
            else:
                log.debug('cancel event at time=%g from now=%g' % (o.time, self.now))
                self._runtime_cancelled_events += 1
        elif isinstance(o, _Process):
            self.kill(o)
        else:
            errmsg = "cancel(o=%r) not an event or process" % o
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
            errmsg = "resched(e=%r) not an event" % e
            log.error(errmsg)
            raise TypeError(errmsg)

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            e.time = self.now
        elif until != None and offset != None:
            errmsg = "resched(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "resched(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            e.time = self.now + offset
        elif until < self.now:
            errmsg = "resched(until=%r) must not be earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: e.time = until

        try:
            self._eventlist.update(e)
            log.debug('reschedule event to time=%g from now=%g' % (e.time, self.now))
            return e
        except Exception:
            # the event already happened as it's not in the event list
            log.debug('reschedule non-active event from now=%g' % self.now)
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
            errmsg = "process(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "process(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "process(until=%r) must not be earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        log.debug('schedule process event at time=%g from now=%g' % (time, self.now))
        self._runtime_scheduled_events += 1
        self._runtime_initiated_processes += 1
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
            errmsg = "terminated(p=%r) not a process" % p
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
                errmsg = "kill(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)

            if p.state != _Process.STATE_TERMINATED:
                # if the process has not been terminated already
                log.debug('kill process at time=%g' % self.now)
                self._runtime_cancelled_processes += 1
                p.deactivate(_Process.STATE_TERMINATED)
                p.trap.trigger()
            else:
                # otherwise, it's already killed; we do nothing
                log.debug('kill non-active process at time=%g' % self.now)
        else:
            # kill oneself
            p = self.cur_process()
            if p is None:
                errmsg = "kill() outside process context"
                log.error(errmsg)
                raise RuntimeError(errmsg)
            log.debug('self-kill process at time=%g' % self.now)
            self._runtime_cancelled_processes += 1
            p.terminate()

    def get_priority(self, p=None):
        """Get the priority of a process.

        A process should be provided as the only argument. If it's
        ignored, it's assumed to be the current process.

        """

        if p is not None:
            # get priority of another process
            if not isinstance(p, _Process):
                errmsg = "get_priority(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)
        else:
            # get the priority of the current process
            p = self.cur_process()
            if p is None:
                errmsg = "get_priority() outside process context"
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
                errmsg = "set_priority(p=%r) not a process" % p
                log.error(errmsg)
                raise TypeError(errmsg)
        else:
            # set the priority of the current process
            p = self.cur_process()
            if p is None:
                errmsg = "set_priority() outside process context"
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
            errmsg = "sleep() outside process context"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        # figure out the expected wakeup time
        if until == None and offset == None:
            errmsg = "sleep() missing time specification"
            log.error(errmsg)
            raise ValueError(errmsg)
        elif until != None and offset != None:
            errmsg = "sleep(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "sleep(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "sleep(until=%r) must not be earlier than now (%r)" % (until, self.now)
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
            errmsg = "semaphore(initval=%r) requires non-negative init value" % initval
            log.error(errmsg)
            raise ValueError(errmsg)
        if qdis < QDIS.FIFO or qdis > QDIS.PRIORITY:
            errmsg = "semaphore(qdis=%r) unknown queuing discipline" % qdis
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
            errmsg = "resource(capacity=%r) requires integer capacity" % capacity
            log.error(errmsg)
            raise TypeError(errmsg)
        if capacity <= 0:
            errmsg = "resource(capacity=%r) requires positive capacity" % capacity
            log.error(errmsg)
            raise ValueError(errmsg)
        if qdis < QDIS.FIFO or qdis > QDIS.PRIORITY:
            errmsg = "resource(qdis=%r) unknown queuing discipline" % qdis
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
            errmsg = "store(capacity=%r) requires positive capacity" % capacity
            log.error(errmsg)
            raise ValueError(errmsg)
        if initlevel < 0 or initlevel > capacity:
            errmsg = "store(capacity=%r, initlevel=%r) out of bound" % (capacity, initlevel)
            log.error(errmsg)
            raise ValueError(errmsg)
        if p_qdis < QDIS.FIFO or p_qdis > QDIS.PRIORITY:
            errmsg = "store(p_qdis=%r) unknown queuing discipline" % p_qdis
            log.error(errmsg)
            raise ValueError(errmsg)
        if c_qdis < QDIS.FIFO or c_qdis > QDIS.PRIORITY:
            errmsg = "store(c_qdis=%r) unknown queuing discipline" % c_qdis
            log.error(errmsg)
            raise ValueError(errmsg)

        return Store(self, capacity, initlevel, initobj, name, p_qdis, c_qdis, collect)

    def mailbox(self, nparts=1, min_delay=0, name=None, collect=None):
        """Create and return a mailbox.

        Args:
            nparts (int): the number of compartments/partitions; the
                value must be a positive integer; the default is one

            min_delay (float): the minimum delay for messages to be
                transported through the mailbox

            name (string): an optional name of the mailbox

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

        if not isinstance(nparts, int) or nparts <= 0:
            errmsg = "mailbox(nparts=%r) requires a positive integer" % nparts
            log.error(errmsg)
            raise TypeError(errmsg)
        if min_delay < 0:
            errmsg = "mailbox(min_delay=%r) requires non-negative min_delay" % min_delay
            log.error(errmsg)
            raise ValueError(errmsg)

        mb = Mailbox(self, nparts, min_delay, name, collect)
        if name is not None:
            _Sync_.register_mailbox(name, mb)
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
            errmsg = "wait() outside process context"
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
                errmsg = "wait() empty list of trappables"
                log.error(errmsg)
                raise ValueError(errmsg)
            for t in traps:
                if not isinstance(t, Trappable):
                    errmsg = "wait() not a trappable in list"
                    log.error(errmsg)
                    raise TypeError(errmsg)
        else:
            errmsg = "wait() one trappable or a list of trappables expected"
            log.error(errmsg)
            raise TypeError(errmsg)
        
        # figure out the expected wakeup time
        if until == None and offset == None:
            time = infinite_time
        elif until != None and offset != None:
            errmsg = "wait(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "wait(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            time = self.now + offset
        elif until < self.now:
            errmsg = "wait(until=%r) must not be earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: time = until

        # only two methods are allowed
        if method != all and method != any:
            errmsg = "wait() with unknown method"
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
                log.debug('schedule timeout event at time=%g from now=%g' % (time, self.now))
                self._runtime_scheduled_events += 1
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
            log.debug('cancel timeout event at time=%g from now=%g' % (e.time, self.now))
            self._runtime_cancelled_events += 1
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
    
    def run(self, offset = None, until = None):
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
        designated time, if either 'offset' or 'until' is
        specified. All events with timestamps smaller than and equal
        to the designated time will be processed. If neither 'offset'
        nor 'until' is provided, the simulator will advance to the
        time of the last processed event.

        """

        # figure out the horizon, up to which all events will be processed
        upper_specified = True
        if until == None and offset == None:
            upper = infinite_time
            upper_specified = False
        elif until != None and offset != None:
            errmsg = "run(until=%r, offset=%r) duplicate specification" % (until, offset)
            log.error(errmsg)
            raise ValueError(errmsg)
        elif offset != None:
            if offset < 0:
                errmsg = "run(offset=%r) requires non-negative offset" % offset
                log.error(errmsg)
                raise ValueError(errmsg)
            upper = self.now + offset
        elif until < self.now:
            errmsg = "run(until=%r) must not be earlier than now (%r)" % (until, self.now)
            log.error(errmsg)
            raise ValueError(errmsg)
        else: upper = until

        # this is the main event loop of the simulator!
        while len(self._eventlist) > 0:
            t = self._eventlist.get_min()
            if t > upper: break
            self._process_one_event()

        # after all the events, make sure we don't wind back the clock
        # if upper (set by either 'until' or 'offset') has been
        # explicitly specified by the user
        if upper_specified:
            self._eventlist.last = upper
            self.now = upper

    def step(self):
        """Process only one event.

        This method processes the next event and advances the
        simulation time to the time of the next event. If no event is
        available on the event list, this method does nothing.

        """

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

    def rng(self):
        """Return the pseudo-random number generator attached to this
        simulator. It's a random.Random instance (Mersenne twister)."""

        if self._rng is None:
            u = uuid.uuid3(_Sync_.namespace, self.name)
            self._rng = random.Random(int(u.int/2**32))
        return self._rng

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
    #         u = uuid.uuid3(_Sync_.namespace, self.name)
    #         self._fast_rng = _FastRNG(int(u.int/2**32))
    #     return self._fast_rng

    def _process_one_event(self):
        """Process one event on the event list, assuming there is a least one
        event on the event list."""
        
        e = self._eventlist.delete_min()
        self.now = e.time
        log.debug("execute event at time %g" % self.now)
        self._runtime_executed_events += 1

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
                log.debug('schedule repeated event at time=%g from now=%g' % (e.time, self.now))
                self._runtime_scheduled_events += 1
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
                log.debug('context switch at time %g' % self.now)
                self._runtime_process_contexts += 1
                p.run()
            else:
                # process is killed while in the ready queue
                assert p.state == _Process.STATE_TERMINATED
        self._theproc = None

    def show_calendar(self):
        """Print the list of all future events currently on the event
        list. This is an expensive operation and should be used
        responsively, possibly just for debugging purposes."""

        print("list of all future events (num=%d) at time %g on simulator %s:" %
              (len(self._eventlist), self.now, self.name if self.name else ''))
        for e in sorted(self._eventlist.pqueue.values()):
            print("  %s" % e)

    def show_runtime_report(self):
        """Print a report on the simulator's runtime performance."""
        t = time.time()-self._runtime_start_clock
        print('*********** simulator performance metrics ***********')
        print('simulator name:', self.name)
        print('simulation time:', self.now-self.init_time)
        print('execution time:', t)
        print('simulation to real time ratio:', (self.now-self.init_time)/t)
        print('scheduled events: %d (rate=%g)' %
              (self._runtime_scheduled_events, self._runtime_scheduled_events/t))
        print('executed events: %d (rate=%g)' %
              (self._runtime_executed_events, self._runtime_executed_events/t))
        print('cancelled events:', self._runtime_cancelled_events)
        print('created processes:', self._runtime_initiated_processes)
        print('finished processes:', self._runtime_terminated_processes)
        print('cancelled processes:', self._runtime_cancelled_processes)
        print('process context switches:', self._runtime_process_contexts)
       
            
def simulator(name = None, init_time = 0):
    """Create a simulator.

    One can use this method repeatedly to create as many simulators as
    needed. A simulator maintains its own event list (along with all
    scheduled functions and processes) and keeps track of the
    simulation time.

    Args:
        name (string): a name of the simulator; if ignored, the system
                will generate a unique name for the simulator; if
                specified, the name needs to be unique so that the
                name can be used to retrieve the corresponding
                simulator instance; the name is also used to determine
                the seed of the pseudo-random generator attached to
                the simulator

        init_time (float): the optional start time of the simulator;
                if unspecified, the default is zero

    Returns:
        This function returns the newly created simulator.

    """

    _Sync_.init() # make sure we have it

    if name is None:
        name = _Sync_.unique_name()
        sim = Simulator(name, init_time)
    else:
        sim = Simulator(name, init_time)
        _Sync_.register_simulator(name, sim)
    return sim
