# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-07-31 04:37:33 liux>
###############################################################

"""Simulation event types and event list."""

from .pqdict import _PQDict_
from .trappable import Trappable
from .trap import Trap

__all__ = ["_Event", "_DirectEvent", "_ProcessEvent", "_EventList_", \
           "infinite_time", "minus_infinite_time"]

# two extremes of simulation time
infinite_time = float('inf')
minus_infinite_time = float('-inf')

class _Event(Trappable):
    """The base class for all simulation events."""

    def __init__(self, sim, time, name=None):
        super().__init__(sim)
        self.time = time
        self.name = name
        self.trap = None

    def __str__(self):
        return "%g: evt=%s" % \
            (self.time, self.name if self.name else id(self))

    def __lt__(self, other):
        return self.time < other.time

    def _try_wait(self):
        # if the current event is on the event list, pass onto the
        # trap created for this event; otherwise, we consider the
        # trappable already triggered
        if self._sim._eventlist.current_event(self):
            if self.trap is None:
                self.trap = Trap(self._sim)
            return self.trap._try_wait()
        else:
            return False
        
    def _cancel_wait(self):
        assert self.trap is not None
        self.trap._cancel_wait()

    def _true_trappable(self):
        # it's possible the event is no longer in the event list, in
        # which case the trap is None (meaning it's sprung)
        if self.trap is not None:
            return self.trap
        else:
            return self
        
class _DirectEvent(_Event):
    """The event type for direct event scheduling."""

    #def __init__(self, sim, time, func, params, name, repeat_intv):
    def __init__(self, sim, time, func, name, repeat_intv, usr_args, usr_kwargs):
        super().__init__(sim, time, name)
        self.func = func
        #self.params = params
        self.repeat_intv = repeat_intv
        self.args = usr_args
        self.kwargs = usr_kwargs

    def __str__(self):
        return "%g: dir_evt=%s %s" % \
            (self.time, self.name if self.name else self.func.__name__+'()',
             "(repeat=%g)"%self.repeat_intv if self.repeat_intv else "")

    def renew(self, time):
        self.time = time
        self.trap = None # trap cannot be reused
        return self

class _ProcessEvent(_Event):
    """The event type for process scheduling."""

    def __init__(self, sim, time, proc, name):
        super().__init__(sim, time, name)
        self.proc = proc

    def __str__(self):
        return "%g: prc_evt=%s" % \
            (self.time, self.name if self.name else self.proc.func.__name__+'()')

class _EventList_(object):
    """An event list sorts events in timestamp order.

    An event list is a priority queue that stores and sorts simulation
    events based on the time of the events. It supports three basic
    operations: to insert a (future) event, to peek and to retrieve
    the event with the minimal timestamp.

    """

    def __init__(self):
        #self.pqueue = []
        self.pqueue = _PQDict_()
        self.last = minus_infinite_time

    def __len__(self):
        return len(self.pqueue)
        
    def insert(self, evt):
        if self.last <= evt.time:
            #heapq.heappush(self.pqueue, (evt.time, id(evt), evt))
            self.pqueue[id(evt)] = evt
        else:
            raise ValueError("EventList.insert(%s): past event (last=%g)" %
                             (evt, self.last))

    def get_min(self):
        if len(self.pqueue) > 0:
            #return self.pqueue[0][0] # just return the time
            x, e = self.pqueue.peek()
            return e.time  # just return the time
        else:
            raise IndexError("EventList.get_min() from empty list")

    def delete_min(self):
        if len(self.pqueue) > 0:
            #assert self.last <= self.pqueue[0][0]
            #self.last = self.pqueue[0][0]
            #return heapq.heappop(self.pqueue)[-1]
            x, e = self.pqueue.popitem()
            assert self.last <= e.time
            self.last = e.time
            return e
        else:
            raise IndexError("EventList.delete_min() from empty list")

    def cancel(self, evt):
        if id(evt) not in self.pqueue:
            raise ValueError("EventList.cancel(%s): event not found" % evt)
        del self.pqueue[id(evt)]

    def update(self, evt):
        if id(evt) not in self.pqueue:
            raise ValueError("EventList.update(%s): event not found" % evt)
        if self.last <= evt.time:
            self.pqueue[id(evt)] = evt
        else:
            raise ValueError("EventList.update(%s): past event (last=%g)" %
                             (evt, self.last))

    def current_event(self, evt):
        # check whether the event is current
        return id(evt) in self.pqueue
