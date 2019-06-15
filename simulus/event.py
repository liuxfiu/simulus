# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-06-15 04:48:27 liux>
###############################################################

"""Simulation event and event list."""

import heapq

__all__ = ["_EventList", "_DirectEvent", "_ProcessEvent", \
           "infinite_time", "minus_infinite_time"]


# two extremes of simulation time
infinite_time = float('inf')
minus_infinite_time = float('-inf')


class _Event(object):
    """The base class for all simulation events."""

    def __init__(self, time):
        self.time = time

    def __str__(self):
        return "event(%g)" % self.time

    
class _DirectEvent(_Event):
    """The event type for direct event scheduling."""

    def __init__(self, time, func, params=None):
        super(_DirectEvent, self).__init__(time)
        self.func = func
        self.params = params

    def __str__(self):
        return "direct_event(%g,%s,%r)" % \
            (self.time, self.func.__name__, self.params)


class _ProcessEvent(_Event):
    """The event type for processes."""

    def __init__(self, time, proc):
        super(_ProcessEvent, self).__init__(time)
        self.proc = proc

    def __str__(self):
        return "proc_event(%g)" % self.time


class _EventList(object):
    """An event list sorts events in timestamp order.

    An event list is a priority queue that stores and sorts simulation
    events based on the time of the events. It supports three basic
    operations: to insert a (future) event, to peek and to retrieve
    the event with the minimal timestamp.

    """

    def __init__(self):
        self.pqueue = []
        self.last = minus_infinite_time

    def __len__(self):
        return len(self.pqueue)
        
    def insert(self, evt):
        if self.last <= evt.time:
            heapq.heappush(self.pqueue, (evt.time, id(evt), evt))
        else:
            raise Exception("eventlist.insert(%s): event in the past (last=%g)" %
                            (evt, self.last))

    def get_min(self):
        if len(self.pqueue) > 0:
            return self.pqueue[0][0] # just return the time
        else:
            raise Exception("eventlist.get_min() from empty list")

    def delete_min(self):
        if len(self.pqueue) > 0:
            assert self.last <= self.pqueue[0][0]
            self.last = self.pqueue[0][0]
            return heapq.heappop(self.pqueue)[-1]
        else:
            raise Exception("eventlist.delete_min() from empty list")


## ------------------------------------------------------------

def _test():
    el = _EventList()

    el.insert(_Event(10))
    el.insert(_Event(100))
    el.insert(_Event(1))
    el.insert(_Event(1000))
    el.insert(_Event(50))

    while len(el)>0:
        t = el.get_min()
        print("get_min(): %g" % t)
        e = el.delete_min()
        print("delete_min(): %s" % e)

    try:
        el.insert(_Event(100))
    except Exception as ex:
        print(ex)

    el.insert(_Event(5000))
    el.delete_min()
        
    try:
        el.get_min()
    except Exception as ex:
        print(ex)
    try:
        el.delete_min()
    except Exception as ex:
        print(ex)
    
if __name__ == '__main__':
    _test()

