# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-06-15 17:32:18 liux>
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
    def __init__(self, name):
        self.name = name
        self.now = 0
        self.event_list = _EventList()
        self.cur_proc = None
        self.running_procs = deque()


    def process(self, proc, offset=None, until=None, params=None, **kargs):
        if until == None and offset == None:
            time = self.now
        elif until != None and offset != None:
            raise Exception("simulator.process(proc=%s, until=%r, offset=%r) duplicate time specification" %
                            (proc.__name__, until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.process(proc=%s, until=%r, offset=%r) negative offset" %
                                (proc.__name__, until, offset))
            time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.process(proc=%s, until=%r, offset=%r) earlier than current time (%g)" %
                            (proc.__name__, until, offset, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("simulator.process(): params must be a dictionary");

        p = _Process(self, proc, params)
        self.event_list.insert(_ProcessEvent(time, p))


    def sleep(self, offset):
        if offset <= 0:
            raise Exception("simulator.sleep(offset=%r) negative offset" % offset)
        if self.cur_proc != None:
            self.cur_proc.sleep(self.now+offset)
        else:
            raise Exception("simulator.sleep(offset=%r) invoked outside process" % offset)


    def semaphore(self, initval=0):
        return _Semaphore(self, initval)


    def sched(self, func, offset=None, until=None, params=None, **kargs):
        if until == None and offset == None:
            raise Exception("simulator.sched(func=%s, until=%r, offset=%r) missing time specification" %
                            (func.__name__, until, offset))
        elif until != None and offset != None:
            raise Exception("simulator.sched(func=%s, until=%r, offset=%r) duplicate time specification" %
                            (func.__name__, until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.sched(func=%s, until=%r, offset=%r) negative offset" %
                                (func.__name__, until, offset))
            time = self.now + offset
        elif until < self.now:
            raise Exception("simulator.sched(func=%s, until=%r, offset=%r) earlier than current time (%g)" %
                            (func.__name__, until, offset, self.now))
        else: time = until

        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise Exception("simulator.sched(): params must be a dictionary");

        self.event_list.insert(_DirectEvent(time, func, params))
            

    def run(self, until = None, offset = None):
        if until == None and offset == None:
            raise Exception("simulator.run(until=%r, offset=%r) missing time specification" %
                            (until, offset))
        elif until != None and offset != None:
            raise Exception("simulator.run(until=%r, offset=%r) duplicate time specification" %
                            (until, offset))
        elif offset != None:
            if offset < 0:
                raise Exception("simulator.run(until=%r, offset=%r) negative offset" %
                                (until, offset))
            upper = self.now + offset
        elif until < self.now:
            raise Exception("simulator.run(until=%r, offset=%r) earlier than current time (%g)" %
                            (until, offset, self.now))
        else: upper = until

        # this is the main event loop
        #print("simulator.run(until=%r, offset=%r) until time %g" % (until, offset, upper))
        while len(self.event_list) > 0:
            t = self.event_list.get_min()
            if t > upper:
                break

            e = self.event_list.delete_min()
            self.now = e.time
            #print("%g: process event %s" % (self.now, e))
            
            if isinstance(e, _DirectEvent):
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

        # after all events, make sure we don't wind back
        self.event_list.last = upper
        self.now = upper

        
def simulator(name = None):
    """Create a simulator."""
    
    if (name != None) and (name in _named_simulators):
            raise Exception("simulator(name=%s) duplicate name" % name)
    sim = _Simulator(name)
    if name != None:
        _named_simulators[name] = sim
    return sim


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

