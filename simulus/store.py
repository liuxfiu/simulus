# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-02 22:01:11 liux>
###############################################################

from .utils import QDIS, QStats
from .trap import _Trappable
from .semaphore import Semaphore

__all__ = ["Store"]



class Store(_Trappable):
    def __init__(self, sim, name=None, capacity=1, qdis, qstats):
        """A store should be created using simulator's store() function.  A
        store has an optional name, a capacity (must be positive), a
        queuing discipline, and a QStats instance for statistics
        collection."""

        self.sim = sim
        self.name = name
        self.capacity = capacity # postive
        self.level = initlevel # nonnegative, no more than capacity
        self.qdis = qdis
        self.qstats = qstats
        self.sem = Semaphore(sim, 0, qdis)

        # for statistics and bookkeeping
        #self.last_arrival_time = sim.now
        #self.proc_arrivals = {}
        #self.proc_services = {}

    def get(self, amount=1):
        # amount must be positive
        if amount <= self.level:
            self.level -= amount
        else:
            self.sem.wait()

    def put(self, amount=1):
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
