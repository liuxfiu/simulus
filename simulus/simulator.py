# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-06-17 15:07:20 liux>
###############################################################

"""A simulator instance.

A simulator has an independent timeline on which events are scheduled
and executed in timestamp order. In parallel simulation, it is also
called a logical process (LP).

Simulus supports multiple simulators to run simultaneously. Each
simulator can run separately, or can be synchronized and run
collectively as in a parallel discrete-event simulation.

Each simulator can have a name, which must be globally unique. Or it
can remain anonymous. Each simulator maintains an event list and a
simulation clock.

"""

from collections import deque

from .event import *
from .process import *
from .semaphore import *

__all__ = ["simulator", "sync", "infinite_time", "minus_infinite_time"]


# a map from names to simulator instances
_named_simulators = {}


class _Simulator:
    #
    # direct event scheduling methods
    #
        
    def sched(self, func, offset=None, name=None, until=None, params=None, repeat_intv=None, **kargs):
        """Schedule an event.

        An event in simulus is represented as a function invoked in
        the simulated future.
        
        Pamameters 
        ----------
        func: the event handler, which is a function that takes two
                arguments, the simulator and the user parameters
                passed in as a dictionary

        offset (float): relative time from now; if provided, must be a
                non-negative value

        name (string): an optional name for the event

        until (float): the absolute time of the event; if provided,
                must not be earlier than the current time; note that
                either offset or until can be used, but not both; if
                both are ignored, it's current time by default

        params (dict): an optional dictionary containing the user
                parameters to be passed to the event handler when it's
                invoked

        repeat_intv (float): if provided, the event will be repeated
                with the given interval; the interval must be a
                postive value

        kargs: optional keyword arguments, which will be folded into
                params and passed to the event handler

        Returns
        -------
        The method returns the direct scheduling event (it's an opaque
        object to the user); the user can print the event, cancel the
        event, or even reschedule the event if necessary

        """

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            raise Exception("simulator.sched(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.sched(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.sched(until=%r) earlier than current time (%r)" %
                            (until, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("simulator.sched(): params must be a dictionary");

        if repeat_intv is not None and repeat_intv <= 0:
            raise Exception("simulator.sched(repeat_intv=%r) non-postive repeat interval" % repeat_intv)
            
        e = _DirectEvent(time, func, params, name, repeat_intv)
        self.event_list.insert(e)
        return e


    def cancel(self, e):
        """Cancel a scheduled event.

        The method takes one argument, which is the return value from
        sched(). When cancelled, the previously scheduled function
        will no longer be invoked.

        """
        
        try:
            self.event_list.cancel(e)
        except Exception:
            raise Exception("simulator.cancel() schedule not found")


    def resched(self, e, offset=None, until=None):
        """Reschedule a scheduled event.

        One can change the time of a scheduled event using this
        method. When rescheduled, the previously scheduled function
        will be invoked at the new designated time.

        """

        # figure out the event time
        if until == None and offset == None:
            # if both are missing, it's now!
            e.time = self.now
        elif until != None and offset != None:
            raise Exception("simulator.resched(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.resched(offset=%r) negative offset" % offset)
            e.time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.resched(until=%r) earlier than current time (%r)" %
                            (until, self.now))
        else: e.time = until     

        try:
            self.event_list.update(e)
        except Exception:
            raise Exception("simulator.resched() schedule not found")


    def peek(self):
        """Return the time of the next scheduled event or infinity if no
                future events are available."""
        
        if len(self.event_list) > 0:
            return self.event_list.get_min()
        else:
            return infinite_time

        
    def show_calendar(self):
        """Print the list of all future events on the event list. This is an
                expensive operation and should be used rarely and
                possibly just for debugging purposes."""

        print("list of future events (n=%d) at time %g on simulator %s:" %
              (len(self.event_list), self.now, self.name if self.name else ''))
        for e in sorted(self.event_list.pqueue.values()):
            print("  %s" % e)


    #
    # process scheduling methods
    #
    
    def process(self, proc, offset=None, name=None, until=None, params=None, **kargs):
        """Create and schedule a process.

        A process in simulus is represented as a function invoked in
        the simulated future.
        
        Pamameters 
        ----------
        proc: the starting function of the process; the function that
                takes two arguments, the simulator and the user
                parameters passed in as a dictionary

        offset (float): relative time from now the process will start
                running; if provided, must be a non-negative value

        name (string): an optional name for the process

        until (float): the absolute time of the process to start
                running; if provided, must not be earlier than the
                current time; note that either offset or until can be
                used, but not both; if both are ignored, it's current
                time by default

        params (dict): an optional dictionary containing the user
                parameters to be passed to the process when it's
                started

        kargs: optional keyword arguments, which will be folded into
                params and passed to the process' starting function

        Returns
        -------
        The method returns the process creation event (it's an opaque
        object to the user); the user can print the event, cancel the
        event, or even reschedule the event if necessary

        """
        
        # figure out the time to start running the process
        if until == None and offset == None:
            # if both are missing, it's now!
            time = self.now
        elif until != None and offset != None:
            raise Exception("simulator.process(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.process(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.process(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("simulator.process(): params must be a dictionary");

        p = _Process(self, name, proc, params)
        e = _ProcessEvent(time, p, name)
        self.event_list.insert(e)
        return e


    def sleep(self, offset=None, until=None):
        """A process sleeps for a certain duration.

        """
        
        # must be called within process context
        if self.cur_proc is None:
            raise Exception("simulator.sleep(offset=%r) outside process context" % offset)

        # figure out the expected wakeup time
        if until == None and offset == None:
            raise Exception("simulator.sleep() missing time specification")
        elif until != None and offset != None:
            raise Exception("simulator.sleep(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.sleep(offset=%r) negative offset" % offset)
            time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.sleep(until=%r) earlier current time (%g)" %
                            (until, self.now))
        else: time = until

        self.cur_proc.sleep(time)


    def semaphore(self, initval=0):
        return _Semaphore(self, initval)


    #
    # run simulation
    #
    
    def run(self, offset = None, until = None):
        """Process the scheduled events.

        The method processes the events in timestamp order and
        advances the simulation clock accordingly. 

        Pamameters 
        ----------
        offset (float): relative time from now; if provided, must be a
                non-negative value

        until (float): the absolute time of the event; if provided,
                must not be earlier than the current time

        The user can specify either offset or until (but not both),
        the simulator will process all events with timestamps no
        larger than the designated time. When the method returns, the
        simulation time will be advanced to the designated time.

        if both offset and until are ignored, the simulator will run
        as long as there are events on the event list. Be careful in
        this case, the simulator may run forever for some models.

        """

        # figure out the horizon, up to which all events will be processed
        upper_specified = True
        if until == None and offset == None:
            upper = infinite_time
            upper_specified = False
        elif until != None and offset != None:
            raise Exception("simulator.run(until=%r, offset=%r) duplicate specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.run(offset=%r) negative offset" % offset)
            upper = self.now + offset
        elif until < self.now:
            raise Exception("simulator.run(until=%r) earlier than current time (%g)" %
                            (until, self.now))
        else: upper = until

        # this is the main event loop
        while len(self.event_list) > 0:
            t = self.event_list.get_min()
            if t > upper: break

            e = self.event_list.delete_min()
            self.now = e.time
            #print("%g: process event %s" % (self.now, e))
            
            if isinstance(e, _DirectEvent):
                if e.repeat_intv is not None:
                    e.time += e.repeat_intv
                    self.event_list.insert(e)
                e.func(self, e.params)
            elif isinstance(e, _ProcessEvent):
                e.proc.activate()
            else:
                raise Exception("unknown event type: " + str(e))

            # processes are run only from the main loop!!
            while len(self.running_procs) > 0:
                self.cur_proc = self.running_procs.popleft()
                self.cur_proc.run()
            self.cur_proc = None

        # after all the events, make sure we don't wind back the clock
        # if upper (either until or offset) has been explicitly
        # specified by user
        if upper_specified:
            self.event_list.last = upper
            self.now = upper


    def step(self):
        """Process the next scheduled event.

        The method processes the next event and advances the
        simulation clock to the time of the next event. If no event is
        available on the event list, the method is a no-op.

        """

        # this is the main event loop
        if len(self.event_list) > 0:
            e = self.event_list.delete_min()
            self.now = e.time
            
            if isinstance(e, _DirectEvent):
                if e.repeat_intv is not None:
                    e.time += e.repeat_intv
                    self.event_list.insert(e)
                e.func(self, e.params)
            elif isinstance(e, _ProcessEvent):
                e.proc.activate()
            else:
                raise Exception("unknown event type: " + str(e))

            while len(self.running_procs) > 0:
                self.cur_proc = self.running_procs.popleft()
                self.cur_proc.run()
            self.cur_proc = None
    

    def __init__(self, name, init_time):
        self.name = name
        self.now = init_time
        self.event_list = _EventList()
        self.cur_proc = None
        self.running_procs = deque()

        
def simulator(name = None, init_time=0):
    """Create a simulator.

    One can use this method repeatedly to create as many simulators as
    needed. A simulator maintains its own event list (along with all
    scheduled functions and processes) and keeps track of the
    simulation time.

    Parameters
    ----------
    name (string): an optional name of the simulator; if specified,
        the name should be unique among all simulators created; the
        name can be used to retrieve the corresponding simulator; if
        there's a duplicate name, the name will represent the
        simulator that gets created later

    init_time (float): the optional start time of the simulator; if
        unspecified, the default is 0

    """
    
    sim = _Simulator(name, init_time)
    if name != None:
        # may possibly replace an earlier simulator
        _named_simulators[name] = sim
    return sim


def get_named_simulator(name):
    """Return the previously created simulator with the given name."""
    return _named_simulators[name]


def sync(sims, lookahead):
    raise Exception("simulus.sync() not implemented")


## ------------------------------------------------------------

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

