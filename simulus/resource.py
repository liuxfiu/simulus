# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-07 08:11:10 liux>
###############################################################

from .utils import QDIS, DataCollector
from .trappable import _Trappable
from .semaphore import Semaphore

__all__ = ["Resource"]

class Resource(_Trappable):
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

        # for statistics and bookkeeping
        self._last_arrival = sim.now
        self._arrivals = {} # map from process to its arrival time
        self._services = {} # map from process to its entering service time

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

        self._sample_arrival(p)
        self._sem.wait()
        self._sample_service(p)

    def release(self):
        """Relinquish the resource acquired previously.

        Note that acquire() and release() are expected in pairs, and
        they should be called by the same process.

        """

        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Resource.acquire() outside process context")

        self._sample_departure(p)
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
        self._sample_arrival(p)
        return self._sem._try_wait()

    def _cancel_wait(self):
        p = self._sim.cur_process()
        assert p is not None
        self._sample_renege(p)
        self._sem._cancel_wait()

    def _commit_wait(self):
        p = self._sim.cur_process()
        assert p is not None
        self._sample_service(p)

    def _true_trappable(self):
        return self._sem


    ##################
    ##  STATISTICS  ##
    ##################

    def _sample_arrival(self, p):
        self._arrivals[p] = self._sim.now
        if self.stats is not None:
            self.stats.sample("arrivals", self._sim.now);
            self.stats.sample("inter_arrival_time", self._sim.now-self._last_arrival)
            self.stats.sample("num_in_system", (self._sim.now, len(self._arrivals)))
        self._last_arrival = self._sim.now

    def _sample_service(self, p):
        self._services[p] = self._sim.now
        if self.stats is not None:
            self.stats.sample("entering_service_time", self._sim.now);
            self.stats.sample("queuing_time", self._sim.now-self._arrivals[p])
            self.stats.sample("num_in_service", (self._sim.now, len(self._services)))

    def _sample_renege(self, p):
        t = self._arrivals.pop(p) # throw a KeyError if not in dictionary
        if self.stats is not None:
            self.stats.sample("reneges", self._sim.now);
            self.stats.sample("renege_queuing_time", self._sim.now-t)
            self.stats.sample("num_in_system", (self._sim.now, len(self._arrivals)))

    def _sample_departure(self, p):
        ta = self._arrivals.pop(p) # throw a KeyError if not in dictionary
        ts = self._services.pop(p) # ... this also
        if self.stats is not None:
            self.stats.sample("departures", self._sim.now);
            self.stats.sample("service_time", self._sim.now-ts)
            self.stats.sample("system_time", self._sim.now-ta)
            self.stats.sample("num_in_system", (self._sim.now, len(self._arrivals)))
            self.stats.sample("num_in_service", (self._sim.now, len(self._services)))
