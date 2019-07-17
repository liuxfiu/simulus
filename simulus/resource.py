# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-17 05:30:34 liux>
###############################################################

from .utils import QDIS, DataCollector, TimeSeries, DataSeries, TimeMarks
from .trappable import Trappable
from .semaphore import Semaphore

__all__ = ["Resource"]

class Resource(Trappable):
    """A resource provides services to processes.

    A resource basically models a single-server or multi-server queue.
    A resource can allow only a limited number of processes to be
    serviced at any given time. A process arrives and acquires a
    server at the resource. If there is an available server, the
    process will gain access to the resource for as long as the
    service is required. If there isn't an available server, the
    process will be put on hold waiting placed in a queue. When
    another process has finished and released the server, one of the
    waiting processes will be unblocked and gain access to the
    resource.

    A process is expected to following the expected sequence of
    actions to use the resource. The process first calls the acquire()
    method to gain access to a server; this is potentially a blocking
    call: the process may be blocked until a server can be assigned to
    it. Once the call returns, the process has acquired the resource.
    The process can use the resource for as long as it needs to; this
    is usually modeled using the sleep() method. Afterwards, the same
    process is expected to call the release() method to free the
    resource, so that another waiting process may have a chance to
    gain access to the resource.

    """

    def __init__(self, sim, name, capacity, qdis, dc):
        """A resource is created using simulator's resource() function; a
        resource can have an optional name, a capacity (which must be
        a postive integer indicating the number of servers at the
        resource), a queuing discipline, and also an optional data
        collector for statistics."""

        super().__init__(sim)
        self.name = name
        self.capacity = capacity
        self.qdis = qdis
        self.stats = dc

        # internally we use a semaphore to implement the resource
        self._sem = Semaphore(sim, capacity, qdis)

        # for bookkeeping and statistics
        self._arrivals = {} # map from process to its arrival time
        self._services = {} # map from process to its entering service time
        if self.stats is not None:
            for k, v in dc._attrs.items():
                if k in ('in_systems', 'in_services', 'in_queues'):
                    if not isinstance(v, TimeSeries):
                        raise TypeError("Resource DataCollector: '%s' not timeseries" % k)
                elif k in ('arrivals', 'services', 'reneges', 'departs'):
                    if not isinstance(v, TimeMarks):
                        raise TypeError("Resource DataCollector: '%s' not timemarks" % k)
                elif k in ('inter_arrivals', 'queue_times', 'renege_times',
                           'service_times', 'system_times'):
                    if not isinstance(v, DataSeries):
                        raise TypeError("Resource DataCollector: '%s' not dataseries" % k)
                else:
                    raise ValueError("Reource DataCollector: '%s' unrecognized" % k)
            self._last_arrival = sim.init_time
        
    def acquire(self):
        """Acquire a server from the resource.

        This method will atomically decrementing a semaphore value
        (indicating the number of servers). The calling process may be
        blocked if no more servers are available.

        """

        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Resource.acquire() outside process context")

        self._make_arrival(p)
        self._sem.wait()
        self._make_service(p)

    def release(self):
        """Relinquish the resource acquired previously.

        Note that acquire() and release() are expected in pairs, and
        they should be called by the same process.

        """

        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Resource.acquire() outside process context")

        self._make_departure(p)
        self._sem.signal()

    def num_in_system(self):
        """Return the number of processes currently using or waiting to use
        the resource."""
        return len(self._arrivals)

    def num_in_service(self):
        """Return the number of processes currently using the resource. It's a
        number between zero and the number of servers (the capacity)."""
        return len(self._services)

    def num_in_queue(self):
        """Return the number of processes wating to use the resource."""
        return self.num_in_system()-self.num_in_service()

    def _try_wait(self):
        p = self._sim.cur_process()
        assert p is not None
        self._make_arrival(p)
        return self._sem._try_wait()

    def _cancel_wait(self):
        p = self._sim.cur_process()
        assert p is not None
        self._make_renege(p)
        self._sem._cancel_wait()

    def _commit_wait(self):
        p = self._sim.cur_process()
        assert p is not None
        self._make_service(p)

    def _true_trappable(self):
        return self._sem

    def _make_arrival(self, p):
        self._arrivals[p] = self._sim.now
        if self.stats is not None:
            self.stats._sample("arrivals", self._sim.now)
            self.stats._sample("inter_arrivals", self._sim.now-self._last_arrival)
            self.stats._sample("in_systems", (self._sim.now, len(self._arrivals)))
            self.stats._sample("in_queues", (self._sim.now, len(self._arrivals)-len(self._services)))
            self._last_arrival = self._sim.now

    def _make_service(self, p):
        self._services[p] = self._sim.now
        if self.stats is not None:
            self.stats._sample("services", self._sim.now)
            self.stats._sample("queue_times", self._sim.now-self._arrivals[p])
            self.stats._sample("in_queues", (self._sim.now, len(self._arrivals)-len(self._services)))
            self.stats._sample("in_services", (self._sim.now, len(self._services)))

    def _make_renege(self, p):
        t = self._arrivals.pop(p) # throw a KeyError if not in dictionary
        if self.stats is not None:
            self.stats._sample("reneges", self._sim.now)
            self.stats._sample("renege_times", self._sim.now-t)
            self.stats._sample("in_queues", (self._sim.now, len(self._arrivals)-len(self._services)))
            self.stats._sample("in_systems", (self._sim.now, len(self._arrivals)))

    def _make_departure(self, p):
        ta = self._arrivals.pop(p) # throw a KeyError if not in dictionary
        ts = self._services.pop(p) # ... this also
        if self.stats is not None:
            self.stats._sample("departs", self._sim.now)
            self.stats._sample("service_times", self._sim.now-ts)
            self.stats._sample("system_times", self._sim.now-ta)
            self.stats._sample("in_systems", (self._sim.now, len(self._arrivals)))
            self.stats._sample("in_services", (self._sim.now, len(self._services)))
