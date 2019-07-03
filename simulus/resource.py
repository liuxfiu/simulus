# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-02 22:40:41 liux>
###############################################################

from .utils import QDIS, QStats
from .trap import _Trappable
from .semaphore import Semaphore

__all__ = ["Resource"]


class Resource(_Trappable):
    """A resource provides services to processes.

    A resource basically models a single-server queue or a
    multi-server queue. A resource can allow only a limited number of
    processes to be serviced at any given time. A process arrives and
    reserves service at the resource. If there is an available server,
    the process will gain access to the resource for as long as the
    service is required. If there isn't an available server, the
    process will be put on hold. All waiting processes are placed in a
    queue. When a process releases the server, one of the waiting
    processes will be unblocked and gain access to the resource.

    A process is expected to following the following sequence of
    actions to use the resource. The process first calls the reserve()
    method to gain access to a server; this is potentially a blocking
    call: the process could be blocked and wait for a server to become
    available to it. Once the call returns, the process is supposed to
    have obtained a server. The process can use the server for as long
    as it needs to; this is usually modeled by a call to the sleep()
    method. Afterwards, the same process is expected to call the
    release() method to free the resource, so that another waiting
    process may have a chance to gain access to the server.

    """

    
    def __init__(self, sim, name, capacity, qdis, qstats):
        """A resource should be created using simulator's resource() function;
        one can give it an optional name, set the capacity (must be
        positive), fix the queuing discipline, and provide the
        statistics collector."""

        self.sim = sim
        self.name = name
        self.capacity = capacity # check int >= 1, #servers!!
        self.qdis = qdis
        self.qstats = qstats

        # internally we use a semaphore to implement the resource
        self.sem = Semaphore(sim, capacity, qdis)

        # for statistics and bookkeeping
        self.last_arrival_time = sim.now
        self.proc_arrivals = {} # map from process to its arrival time
        self.proc_services = {} # map from process to its entering service time


    def reserve(self):
        """Trying to acquire a server by atomically decrementing a semaphore
        value. The calling process may need to be blocked."""

        self._sample_arrival()
        self.sem.wait()
        self._sample_service()


    def release(self):
        """The process relinquishes the use of the server acquired previously.
        Note that reserve() and release() are expected in pairs, and
        they should be called by the same process."""

        self._sample_departure()
        self.sem.signal()




    def num_in_system(self):
        return len(self.proc_arrivals)

    def num_in_service(self):
        return len(self.proc_services)

    def num_in_queue(self):
        return self.num_in_system()-self.num_in_service()

    def _try_wait(self):
        self._sample_arrival()
        self.sem._try_wait()

    def _cancel_wait(self):
        self._sample_renege()
        self.sem._cancel_wait()

    def _commit_wait(self):
        self._sample_service()


    ##################
    ##  STATISTICS  ##
    ##################

    @staticmethod
    def default_qstats(report='sum'):
        if 'all' == report:
            return QStats(arrivals='all',
                          inter_arrival_time='all',
                          entering_service_time='all',
                          queuing_time='all',
                          reneges='all',
                          renege_queuing_time='all',
                          departures='all',
                          service_time='all',
                          system_time='all',
                          num_in_system='all',
                          num_in_service='all')
        elif 'sum' == report:
            return QStats(#arrivals='cnt',
                          inter_arrival_time='sum',
                          #entering_service_time='cnt',
                          queuing_time='sum',
                          reneges='cnt',
                          #renege_queuing_time='sum',
                          #departures='cnt',
                          service_time='sum',
                          #system_time='sum',
                          num_in_system='acc',
                          num_in_service='acc')
        else:
            return None

    def _sample_arrival(self):
        if self.qstats is not None:
            self.qstats.sample("arrivals", self.sim.now);
            self.qstats.sample("inter_arrival_time", self.sim.now-self.last_arrival_time)
            self.qstats.sample("num_in_system", (self.sim.now, len(self.proc_arrivals)+1))
        self.last_arrival_time = self.sim.now
        self.proc_arrivals[self.sim.cur_process()] = self.sim.now

    def _sample_service(self):
        if self.qstats is not None:
            self.qstats.sample("entering_service_time", self.sim.now);
            self.qstats.sample("queuing_time", self.sim.now-self.proc_arrivals[self.sim.cur_process()])
            self.qstats.sample("num_in_service", (self.sim.now, len(self.proc_services)+1))
        self.proc_services[self.sim.cur_process()] = self.sim.now

    def _sample_renege(self):
        if self.qstats is not None:
            self.qstats.sample("reneges", self.sim.now);
            self.qstats.sample("renege_queuing_time", self.sim.now-self.proc_arrivals[self.sim.cur_process()])
            self.qstats.sample("num_in_system", (self.sim.now, len(self.proc_arrivals)-1))
        del self.proc_arrivals[self.sim.cur_process()]

    def _sample_departure(self):
        if self.qstats is not None:
            self.qstats.sample("departures", self.sim.now);
            self.qstats.sample("service_time", self.sim.now-self.proc_services[self.sim.cur_process()])
            self.qstats.sample("system_time", self.sim.now-self.proc_arrivals[self.sim.cur_process()])
            self.qstats.sample("num_in_system", (self.sim.now, len(self.proc_arrivals)-1))
            self.qstats.sample("num_in_service", (self.sim.now, len(self.proc_services)-1))
        del self.proc_arrivals[self.sim.cur_process()]
        del self.proc_services[self.sim.cur_process()]
