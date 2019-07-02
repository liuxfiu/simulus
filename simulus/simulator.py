# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-07-02 05:29:47 liux>
###############################################################

from collections import deque

from .trap import *
from .semaphore import *
from .event import *
from .process import *

__all__ = ["simulator", "sync", "infinite_time", "minus_infinite_time"]


# a map from names to simulator instances
_named_simulators = {}


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

    ###################################
    # direct event scheduling methods #
    ###################################
        
    def sched(self, func, offset=None, name=None, until=None, params=None, repeat_intv=None, **kargs):
        """Schedule an event.

        An event in simulus is represented as a function invoked in
        the simulated future.
        
        Parameters 
        ----------
        func: the event handler, which is a function that takes two
                arguments: a simulator instance and the user
                parameters passed in as a dictionary

        offset (float): relative time from now at which the event is
                scheduled to happen; if provided, must be a
                non-negative value

        name (string): an optional name for the event

        until (float): the absolute time at which the event is
                scheduled to happen; if provided, it must not be
                earlier than the current time; note that either
                'offset' or 'until' can be used, but not both; if both
                are ignored, it's assumed to be the current time

        params (dict): an optional dictionary containing the user
                parameters to be passed to the event handler when the
                function is invoked

        repeat_intv (float): if provided, the event will be repeated
                with the given time interval; the interval must be a
                strictly postive value

        kargs: arbitrary keyword arguments, which will be folded into
                'params' and passed to the event handler

        Returns
        -------
        This method returns a direct scheduling event (it's an opaque
        object to the user), with which the user can cancel the event, 
        or reschedule the event, or trap the event if needed

        """

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            raise Exception("Simulator.sched(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.sched(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.sched(until=%r) earlier than current time (%r)" %
                            (until, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("Simulator.sched() params not a dictionary");

        if repeat_intv is not None and repeat_intv <= 0:
            raise Exception("Simulator.sched(repeat_intv=%r) non-postive repeat interval" % repeat_intv)
            
        e = _DirectEvent(time, func, params, name, repeat_intv)
        self.event_list.insert(e)
        return e


    def cancel(self, e):
        """Cancel a scheduled event.

        This method takes one argument, which is the return value (as
        opaque object, which is an event) from sched(). When
        cancelled, the previously scheduled function will no longer be
        invoked at the expected time. The method would have no effect
        if the event that has already happened.

        """
        
        if not isinstance(e, _Event):
            raise Exception("Simulator.cancel(e=%r) not an event" % e)
        try:
            self.event_list.cancel(e)
        except Exception:
            # the event is not in the event list
            # raise Exception("Simulator.cancel() schedule not found")
            pass


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
            raise Exception("Simulator.resched(e=%r) not an event" % e)

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            e.time = self.now
        elif until != None and offset != None:
            raise Exception("Simulator.resched(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.resched(offset=%r) negative offset" % offset)
            e.time = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.resched(until=%r) earlier than current time (%r)" %
                            (until, self.now))
        else: e.time = until     

        try:
            self.event_list.update(e)
            return e
        except Exception:
            #raise Exception("Simulator.resched() event already happened")
            return None


    ##############################
    # process scheduling methods #
    ##############################
    
    def process(self, proc, offset=None, name=None, until=None, params=None, **kargs):
        """Create a process and schedule its execution.

        A process is a separate thread of control. During its
        execution, a process can sleep for some time, or wait for
        certain conditions to become true (on a trap or semaphore), or
        both. In either case, the process can be suspended and the
        simulation time may advance until it resumes execution.

        This method creates a process and schedule for the process to
        run (from a starting function) in the simulated future
        (including now).
        
        Parameters 
        ----------
        proc: the starting function of the process; the function that
                takes two arguments: a simulator instance and the user
                parameters passed in as a dictionary

        offset (float): relative time from now at which the process is
                expected to start running; if provided, it must be a
                non-negative value (zero is OK)

        name (string): an optional name for the process

        until (float): the absolute time at which the process is
                expected to start running; if provided, it must not be
                earlier than the current time; note that either
                'offset' or 'until' can be used, but not both; if both
                are ignored, it is assumed to be the current time

        params (dict): an optional dictionary containing the user
                parameters to be passed to the process' starting
                function when it begins execution

        kargs: optional keyword arguments, which will be folded into
                'params' and passed to the process' starting function

        Returns
        -------
        This method returns the process being created (it's an opaque
        object to the user); the user can use it to check whether the
        process is terminated, to join the process (i.e., to wait for
        its termination), or to explicitly kill the process.

        """
        
        # figure out the time to start running the process
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            raise Exception("Simulator.process(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.process(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.process(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("Simulator.process() params not a dictionary");

        p = _Process(self, name, proc, params)
        e = _ProcessEvent(time, p, name)
        self.event_list.insert(e)
        return p


    def cur_process(self):
        """Return the current running process, or None if we are not in a
        process context."""
        
        assert self._theproc is None or \
            self._theproc.state == _Process.STATE_RUNNING
        return self._theproc

    
    def terminated(self, p=None):
        """Check whether a process has terminated. 

        The process to be checked for termination should be provided
        as the only argument. If it's ignored, it's assumed to be the
        current process. In the latter case, this method must be
        called within a process context (not in an event handler or in
        the main function).

        """

        if p is not None:
            if not isinstance(p, _Process):
                raise Exception("Simulator.terminated(p=%r) not a process" % p)
        else:
            p = self.cur_process()
            if p is None:
                raise Exception("Simulator.terminated() outside process context")
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
                raise Exception("Simulator.kill(p=%r) not a process" % p)

            if p.state != _Process.STATE_TERMINATED:
                # if the process has not been terminated already
                p.deactivate(_Process.STATE_TERMINATED)
                p.get_trap().trigger()
            # otherwise, it's already killed; we do nothing
        else:
            # kill oneself
            p = self.cur_process()
            if p is None:
                raise Exception("Simulator.kill() outside process context")
            p.terminate()

            
    def semaphore(self, initval=0, qdis=Semaphore.QDIS_FIFO):
        """Create a semaphore for inter-process communication.

        Parameters
        ----------
        initval (int): the initial value of the semaphore; the value must be non-negative; 
                the default is zero

        qdis : the queuing discipline for the waiting processes, which
                can be selected from Semaphore.QDIS_FIFO (first in
                first out), Semaphore.QDIS_LIFO (last in first out),
                Semaphore.QDIS_RANDOM (random ordering), or
                Semaphore.QDIS_PRIORITY (based on process priority)

        Returns
        -------
        This method returns the newly created semaphore.

        """

        if initval < 0:
            raise Exception("Simulator.semaphore(initval=%r) negative init value" % initval)
        if qdis < Semaphore.QDIS_FIFO or \
           qdis > Semaphore.QDIS_PRIORITY:
            raise Exception("Simulator.semaphore(qdis=%r) unknown queuing discipline" % qdis)
        return Semaphore(self, initval, qdis)


    def trap(self, o=None):
       """Create a trap or return the trap assocated with the given object.

       If no argument is provided, a new trap will be created and
       returned. 

       If the argument is a process (returned from the process() or
       cur_Process() method), the trap associated with the termination
       of the process will be returned.

       If the argument is an event (returned from the sched() or
       resched() method), a trap associated with the event's
       activation will be returned. The event must be a currently
       scheduled event (not one from the past), or an exception will
       be raised.

       """

       if o is None:
           return Trap(self)
       elif isinstance(o, _Process):
           return o.get_trap() # it's for process termination
       elif isinstance(o, _Event):
           if self.event_list.current_event(o):
               return o.get_trap(self)
           else:
               raise Exception("Simulator.trap(o=%r) stale event" % o)
       else:
           raise Exception("Simulator.trap(o=%r) unknown object" % o)


    def sleep(self, offset=None, until=None):
        """A process blocks for a certain time duration.

        This method must be called within a process context (not in an
        event handler or in the main function). The process will be
        put on hold for the given period of time. It will resume
        execution after the time period has passed.

        Note that sleep cannot be interrupted, although the process
        can be killed by another process when it's asleep. For
        interruptable sleep, use the wait() method.

        Parameters 
        ----------
        offset (float): relative time from now until which the process
                will be put on hold; if provided, it must be a
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
            raise Exception("Simulator.sleep() outside process context")

        # figure out the expected wakeup time
        if until == None and offset == None:
            raise Exception("Simulator.sleep() missing time specification")
        elif until != None and offset != None:
            raise Exception("Simulator.sleep(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.sleep(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.sleep(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: time = until

        # the control will be switched back to the simulator's main
        # event loop (i.e., the process will be putting on hold)...
        p.sleep(time)
        # the control comes back now; the process resumes execution...


    def wait(self, traps, offset=None, until=None, method=all):
        """A process blocks on trappables for certain time.

        This method must be called within a process context (not in an
        event handler or in the main function). The process will be
        put on hold for one or a list of trappables and for a given
        amount of time (if specified). The process will resume
        execution after conditions are met.

        Parameters
        ----------
        traps: either a trappable (a trap, semaphore, or other
                facilities) or a list/tuple of trappables

        offset (float): relative time from now until which the process
                will be put on hold at the latest; if provided, it
                must be a non-negative value

        until (float): the absolute time at which the process is
                expected to resume execution at the latest; if
                provided, it must not be earlier than the current
                time; either 'offset' or 'until' can be provided, but
                not both; if both 'offset' and 'until' are ignored,
                there will be no time limit on the wait

        method: can be either 'all' (the default) or 'any'; if 'all',
                all trappables must be triggered before this process
                can resume execution (or timed out); if 'any', one of
                the trappables must be triggered before this process
                can resume execution (or timed out); this parameter
                has no effect if only one trappable (not the list) is
                provided as the first argument

        Returns
        -------
        The return value of this method is a tuple with two elements:
        the first element of the tuple is to indicate whether the
        trappables have been triggered or not; the second element of
        tuple is to indicate whether timeout happens.

        If the first argument when calling this method is only one
        trappable (not in a list or tuple), the first element of the
        returned tuple will be simply True or False depending on the
        trappable has been triggered or not.

        If the first argument when calling this method is a list or a
        tuple of trappables, the first element of the returned tuple
        will be a list of booleans where each element of the list
        indicates whether the corresponding trappable has been
        triggered or not.

        """

        # must be called within process context
        p = self.cur_process()
        if p is None:
            raise Exception("Simulator.wait() outside process context")

        # sanity check of the first argument: a trappable or a
        # list/tuple of trappables
        if isinstance(traps, _Trappable):
            single_trappable = True
            traps = [traps]
        elif isinstance(traps, (list, tuple)):
            single_trappable = False
            if len(traps) == 0:
                raise Exception("Simulator.wait() empty trappables")
            for t in traps:
                if not isinstance(t, _Trappable):
                    raise Exception("Simulator.wait() not a trappable list") 
        else:
            raise Exception("Simulator.wait() trappable or list of trappables expected") 
        
        # figure out the expected wakeup time
        if until == None and offset == None:
            time = infinite_time
        elif until != None and offset != None:
            raise Exception("Simulator.wait(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.wait(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.wait(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: time = until

        # only two methods are allowed
        if method != all and method != any:
            raise Exception("Simulator.wait() unknown method")

        # a mask indicating whether the corresponding trap has been
        # triggered (i.e., no need to wait) or not
        trigged = [not t._try_wait() for t in traps]
        
        timedout = False
        e = None # this is the timeout event

        p.acting_trappables.clear()
        while not method(trigged):
            # the wait hasn't been satisfied; the process shall be
            # suspended
            
            # make sure we schedule the timeout event, only once
            if e is None and time < infinite_time:
                e = _ProcessEvent(time, p, p.name)
                self.event_list.insert(e)
            
            p.suspend()

            # update the mask (this is a circuitous way to find out
            # which trap in the list of traps is responsible for
            # unblocking the process this time)
            for t in p.acting_trappables:
                # if the acting trappables are not in expected list of
                # traps, something is wrong (in which case an
                # exception will be raised)
                i = traps.index(t)
                trigged[i] = True
            p.acting_trappables.clear()

            # check if we are timed out
            if e is not None and not self.event_list.current_event(e):
                timedout = True
                break
            
        # cancel the future timeout event
        if e is not None and not timedout:
            self.event_list.cancel(e)

        # cancel the try-wait for those untriggered trappables
        [t._cancel_try_wait() for i, t in enumerate(traps) if not trigged[i]]
         
        # the wait has been satisfied, return accordingly
        if single_trappable:
            return trigged[0], timedout
        else:
            return trigged, timedout
        #r = [t for i, t in enumerate(traps) if not trigged[i]]
        
        
    def join(self, procs, method=all):
        """Wait until the process(es) are finished. This 

        This method must be called within a process context (not in an
        event handler or in the main function). The process will be
        put on hold until the processes specified in the first
        argument have finished.

        Parameters 
        ----------
        procs: either a process (returned from process() or
                cur_process()) or a list/tuple of processes

        method: can be either 'all' (the default) or 'any'; if 'all',
                all processes must be finished before this process can
                resume execution; if 'any', one of the processes must
                be finished before this process can resume execution

        This method does not return a value. When it returns, the
        process has already resumed execution. That is, one process
        (in case of 'any') or all (in case of 'all') processes have
        funished execution. If using 'any', one may use the
        terminated() method to find out which process(es) are done.

        """
        
        # must be called within process context
        p = self.cur_process()
        if p is None:
            raise Exception("Simulator.join() outside process context")

        if isinstance(procs, _Process):
            traps = [procs.get_trap()]
        elif isinstance(procs, (list, tuple)):
            if len(procs) == 0:
                raise Exception("Simulator.join() empty process list")
            traps = []
            for p in procs:
                if not isinstance(p, _Process):
                    raise Exception("Simulator.join() not a process list")
                traps.append(p.get_trap())
        else:
            raise Exception("Simulator.join() a process or a list of processes expected")
        
        if method != all and method != any:
            raise Exception("Simulator.join() unknown method")

        self.wait(traps, method=method)


    ######################
    # running simulation #
    ######################
    
    def run(self, offset = None, until = None):
        """Run simulation and process events.

        This method processes the events in timestamp order and
        advances the simulation time accordingly.

        Parameters 
        ----------
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
        Otherwise, the simulator will advance to the time of the last
        event.

        """

        # figure out the horizon, up to which all events will be processed
        upper_specified = True
        if until == None and offset == None:
            upper = infinite_time
            upper_specified = False
        elif until != None and offset != None:
            raise Exception("Simulator.run(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("Simulator.run(offset=%r) negative offset" % offset)
            upper = self.now + offset
        elif until < self.now:
            raise Exception("Simulator.run(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: upper = until

        # this is the main event loop of the simulator!
        while len(self.event_list) > 0:
            t = self.event_list.get_min()
            if t > upper: break
            self._one_event()

        # after all the events, make sure we don't wind back the clock
        # if upper (set by either 'until' or 'offset') has been
        # explicitly specified by the user
        if upper_specified:
            self.event_list.last = upper
            self.now = upper


    def step(self):
        """Process only one event.

        This method processes the next event and advances the
        simulation time to the time of the next event. If no event is
        available on the event list, this method does nothing.

        """

        # this is the main event loop
        if len(self.event_list) > 0:
            self._one_event();
            

    def peek(self):
        """Return the time of the next scheduled event, or infinity if no
        future events are available."""
        
        if len(self.event_list) > 0:
            return self.event_list.get_min()
        else:
            return infinite_time

        
    def show_calendar(self):
        """Print the list of all future events currently on the event
        list. This is an expensive operation and should be used
        responsively, possibly just for debugging purposes."""

        print("list of future events (num=%d) at time %g on simulator %s:" %
              (len(self.event_list), self.now, self.name if self.name else ''))
        for e in sorted(self.event_list.pqueue.values()):
            print("  %s" % e)


    def __init__(self, name, init_time):
        """A simulator can only be created using the simulator() function."""

        self.name = name
        self.now = init_time
        self.event_list = _EventList()
        self._theproc = None
        self._ready = deque()


    def _one_event(self):
        """Process one event on the event list, assuming there is a least one
        event on the event list."""
        
        e = self.event_list.delete_min()
        self.now = e.time
        #print("%g: process %s" % (self.now, e))

        # trigger the trap if the event already has a trap; this
        # is a memory-saving mechanism: only those events that the
        # user is explicitly interested in (using the simulator's
        # trap() method) are attached with a trap
        if e.trap is not None:
            e.trap.trigger()
            
        if isinstance(e, _DirectEvent):
            if e.repeat_intv is not None:
                # note that a renewed event is not trappable
                self.event_list.insert(e.renew(e.time+e.repeat_intv))
            e.func(self, e.params)
        elif isinstance(e, _ProcessEvent):
            e.proc.activate()
        else:
            raise Exception("unknown event type: " + str(e))

        # processes are run only from the main loop!!
        while len(self._ready) > 0:
            p = self._ready.popleft()
            if p.state == _Process.STATE_RUNNING:
                self._theproc = p
                p.run()
            else:
                # processes can be killed while in the ready queue
                assert p.state == _Process.STATE_TERMINATED
        self._theproc = None

        
def simulator(name = None, init_time = 0):
    """Create a simulator.

    One can use this method repeatedly to create as many simulators as
    needed. A simulator maintains its own event list (along with all
    scheduled functions and processes) and keeps track of the
    simulation time.

    Parameters
    ----------
    name (string): an optional name of the simulator; if specified,
        the name must be unique among all simulators created; the name
        can be used to retrieve the corresponding simulator; if
        there's a duplicate name, the name will represent the
        simulator that gets created later; a simulator can also remain
        anonymous

    init_time (float): the optional start time of the simulator; if
        unspecified, the default is 0

    """
    
    sim = Simulator(name, init_time)
    if name != None:
        # may possibly replace an earlier simulator of the same name
        _named_simulators[name] = sim
    return sim


def get_simulator(name):
    """Return the simulator with the given name, or None if no such
    simulation can be found."""
    return _named_simulators[name]


## ------------------------------------------------------------

def sync(sims, lookahead):
    raise Exception("simulus.sync() not implemented")

def _test():
    sim = simulator()
    sim1 = simulator("sim1")
    sim2 = simulator("sim2")
    try:
        sim3 = simulator("sim2")
    except Exception as ex:
        print(ex)

    sim.run(offset=10)
    sim.run(until=50)
    try:
        sim.run(offset=-1)
    except Exception as ex:
        print(ex)
    try:
        sim.run(until=10)
    except Exception as ex:
        print(ex)
    try:
        sim.run()
    except Exception as ex:
        print(ex)
    try:
        sim.run(offset=10, until=100)
    except Exception as ex:
        print(ex)
    
if __name__ == '__main__':
    _test()

