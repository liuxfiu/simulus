# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on August 7, 2019
# Last Update: Time-stamp: <2019-09-09 05:03:24 liux>
###############################################################

from collections import deque

from .utils import QDIS, DataCollector, TimeSeries, DataSeries, TimeMarks
from .trappable import Trappable
from .semaphore import Semaphore

__all__ = ["Bucket"]

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class Bucket(object):
    """A bucket for synchronizing producer and consumer processes.

    A bucket is a facility for storing uncountable quantities or
    volumes (such as gas in a tank, water in a reservoir, and battery
    power in a mobile computer). It's similar to a store, except that
    it's for uncountable quantities.

    A bucket has a maximum capacity, which is a positive quantity
    specified as a float-point number. A bucket can also tell its
    current storage level, which goes between zero and the maximum
    capacity.

    One or several processes can put some quantities into the bucket.
    They are called producer processes. One or several processes can
    get quantities from the bucket. They are called consumer
    processes.  The producer process and the consumer process is
    determined by its performed action on the bucket. They can be the
    same process.

    A producer process calls the put() method to deposit some
    quantities into the bucket. The put amount shall be specified as
    an argument. The current storage level will increase accordingly
    as a result. However, if a producer process tries to put more
    quantities than the bucket's capacity, the producer process will
    be blocked. The process will remain blocked until the current
    storage level decreases (by some other processes getting
    quantities from the bucket) so that there is room for putting the
    specified quantities.

    Similarly, a consumer process calls the get() method to retrieve
    quantities from the bucket. The get amount shall be specified as
    an argument.  The current storage level will decrease accordingly
    as a result. If a consumer process tries to get more quantities
    than what is avaialble at the bucket, the consumer process will be
    blocked.  The process will remain blocked until the current
    storage level goes above the requested amount (by some other
    processes putting quantities into the bucket).

    """
    
    def __init__(self, sim, capacity, initlevel, name, p_qdis, c_qdis, dc):
        """A bucket should be created using simulator's bucket() function. A
        bucket has a capacity (must be positive), an initial level,
        optional initial jobs, an optional name, a queuing discipline,
        and a DataCollector instance for statistics collection."""

        self._sim = sim
        self.capacity = capacity # postive
        self.level = initlevel # nonnegative, no more than capacity
        self.name = name
        self.stats = dc

        # internally, we use two semaphores; one for producer and one
        # for consumer
        self._p_sem = Semaphore(sim, 0, p_qdis)
        self._c_sem = Semaphore(sim, 0, c_qdis)

        # for statistics and bookkeeping
        self._p_arrivals = {} # map from producer process to its arrival time and put amount
        self._c_arrivals = {} # map from consumer process to its arrival time and get amount

        if self.stats is not None:
            for k, v in dc._attrs.items():
                if k in ('puts', 'put_queues', 'gets', 'get_queues', 'levels'):
                    if not isinstance(v, TimeSeries):
                        errmsg = "'%s' not timeseries in bucket datacollector" % k
                        log.error(errmsg)
                        raise TypeError(errmsg)
                elif k in ('put_times', 'get_times'):
                    if not isinstance(v, DataSeries):
                        errmsg = "'%s' not dataseries in bucket datacollector" % k
                        log.error(errmsg)
                        raise TypeError(errmsg)
                else:
                    errmsg = "unrecognized attribute '%s' in bucket datacollector" % k
                    log.error(errmsg)
                    raise TypeError(errmsg)
            self.stats._sample("levels", (sim.init_time, initlevel))

    def get(self, amt):
        """Retrieve quantities from the bucket.

        Args:
            amt (float): the amount of quantities to be retrieved all
                at once (must be positive)

        This method does not return a value.

        """
        
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            errmsg = "bucket.get() outside process context"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        if self.capacity < amt:
            errmsg = "bucket.get(amt=%r) more than capacity (%r)" % (amt, self.capacity)
            log.error(errmsg)
            raise ValueError(errmsg)
        if amt <= 0:
            errmsg = "bucket.get(amt=%r) requires positive amount" % amt
            log.error(errmsg)
            raise ValueError(errmsg)

        self._make_c_arrival(p, amt)

        # the consumer must be blocked if there isn't enough quantity
        # in the bucket
        if amt > self.level:
            #log.debug('consumer get(amt=%r) blocked from bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
            self._c_sem.wait()
            #log.debug('consumer get(amt=%r) unblocked from bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
        else:
            #log.debug('no consumer blocked to get(amt=%r) from bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
            pass

        # the get amount can be satisfied now if the consumer process
        # reaches here; we lower the level and unblock as many
        # producer processes as we can
        self.level -= amt
        lvl = self.level
        np = self._p_sem._next_unblock()
        while np is not None:
            # if the producer process to be unblocked next has room
            # now for the put amount, we unblock it
            if self._p_arrivals[np][1] + lvl <= self.capacity:
                #log.debug('consumer get(amt=%r) unblocks producer put(amt=%r) in bucket (level=%r)' %
                #          (amt, self._p_arrivals[np][1], self.level))
                lvl += self._p_arrivals[np][1]
                self._p_sem.signal()
                np = self._p_sem._next_unblock()
            else: break

        return self._make_c_departure(p, amt)

    def put(self, amt):
        """Deposit quantities to the bucket.

        Args:
            amt (float): the amount of quantities to be deposited all
                at once (must be positive)

        This method does not return a value.

        """
        
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            errmsg = "bucket.put() outside process context"
            log.error(errmsg)
            raise RuntimeError(errmsg)

        if self.capacity < amt:
            errmsg = "bucket.put(amt=%r) more than capacity (%r)" % (amt, self.capacity)
            log.error(errmsg)
            raise ValueError(errmsg)
        if amt <= 0:
            errmsg = "bucket.put(amt=%r) requires positive amount" % amt
            log.error(errmsg)
            raise ValueError(errmsg)
           
        self._make_p_arrival(p, amt)

        # the producer will be blocked if the put amount would
        # overflow the bucket
        if amt + self.level > self.capacity:
            #log.debug('producer put(amt=%r) blocked from bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
            self._p_sem.wait()
            #log.debug('producer put(amt=%r) unblocked from bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
        else:
            #log.debug('no producer blocked to put(amt=%r) to bucket (level=%r) at %g' %
            #          (amt, self.level, self._sim.now))
            pass
            
        # the put amount can be satisfied now if the producer process
        # reaches here; we increase the level and unblock as many
        # consumer processes as we can
        self.level += amt
        lvl = self.level
        nc = self._c_sem._next_unblock()
        while nc is not None:
            # if the consumer process to be unblocked next has enough
            # quantity in bucket now for the get amount, we unblock it
            if self._c_arrivals[nc][1] <= lvl:
                #log.debug('producer put(amt=%r) unblocks consumer get(amt=%r) in bucket (level=%r)' %
                #          (amt, self._c_arrivals[nc][1], self.level))
                lvl -= self._c_arrivals[nc][1]
                self._c_sem.signal()
                nc = self._c_sem._next_unblock()
            else: break

        self._make_p_departure(p, amt)

    def getter(self, amt):
        """Return a trappable for getting quantities from the bucket.  This
        function is similar to the get() method, except that it
        returns a trappable (like traps, semaphores, and resources) on
        which one can apply conditional wait using the simulator's
        wait() function."""

        class _GetTrappable(Trappable):
            """The bucket's trappable for conditional wait on get."""
            
            def __init__(self, bucket, amt):
                super().__init__(bucket._sim)
                self._bucket = bucket
                self._amt = amt

                if bucket.capacity < amt:
                    errmsg = "bucket.getter(amt=%r) more than capacity (%r)" % (amt, bucket.capacity)
                    log.error(errmsg)
                    raise ValueError(errmsg)
                if amt <= 0:
                    errmsg = "bucket.getter(amt=%r) requires positive amount" % amt
                    log.error(errmsg)
                    raise ValueError(errmsg)

            def _try_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None
                
                self._bucket._make_c_arrival(p, self._amt)

                # the consumer will be blocked if there isn't enough
                # quantity in the bucket
                if self._amt > self._bucket.level:
                    #log.debug('consumer try-get(amt=%r) blocked from bucket (level=%r) at %g' %
                    #          (self._amt, self._bucket.level, self._bucket._sim.now))
                    return self._bucket._c_sem._try_wait() # must be True
                else:
                    #log.debug('no consumer blocked to try-get(amt=%r) from bucket (level=%r) at %g' %
                    #          (self._amt, self._bucket.level, self._bucket._sim.now))
                    return False

            def _cancel_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None
                self._bucket._make_c_renege(p)
                #log.debug('consumer cancels try-get(amt=%r) from bucket (level=%r) at %g' %
                #          (self._amt, self._bucket.level, self._bucket._sim.now))
                self._bucket._c_sem._cancel_wait()

            def _commit_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None
                #log.debug('consumer try-get(amt=%r) unblocked from bucket (level=%r) at %g' %
                #          (self._amt, self._bucket.level, self._bucket._sim.now))

                # the get amount can be satisfied if the consumer
                # process reaches here; we lower the level and unblock
                # as many producer processes as we can
                self._bucket.level -= self._amt
                lvl = self._bucket.level
                np = self._bucket._p_sem._next_unblock()
                while np is not None:
                    # if the producer process to be unblocked next has
                    # room now for the put amount, we unblock it
                    if self._bucket._p_arrivals[np][1] + lvl <= self._bucket.capacity:
                        #log.debug('consumer try-get(amt=%r) unblocks producer put(amt=%r) in bucket (level=%r)' %
                        #          (self._amt, self._bucket._p_arrivals[np][1], self._bucket.level))
                        lvl += self._bucket._p_arrivals[np][1]
                        self._bucket._p_sem.signal()
                        np = self._bucket._p_sem._next_unblock()
                    else: break
                    
                self._bucket._make_c_departure(p, self._amt)

            def _true_trappable(self):
                return self._bucket._c_sem

        return _GetTrappable(self, amt)
    
    def putter(self, amt):
        """Return a trappable for putting quantities to the bucket. This
        function is similar to the put() method, except that it
        returns a trappable (like traps, semaphores, and resources) on
        which one can apply conditional wait using the simulator's
        wait() function."""

        class _PutTrappable(Trappable):
            """The bucket's trappable for conditional wait on put."""
            
            def __init__(self, bucket, amt):
                super().__init__(bucket._sim)
                self._bucket = bucket
                self._amt = amt

                if bucket.capacity < amt:
                    errmsg = "bucket.putter(amt=%r) more than capacity (%r)" % (amt, bucket.capacity)
                    log.error(errmsg)
                    raise ValueError(errmsg)
                if amt <= 0:
                    errmsg = "bucket.putter(amt=%r) requires positive amount" % amt
                    log.error(errmsg)
                    raise ValueError(errmsg)

            def _try_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None

                self._bucket._make_p_arrival(p, self._amt)

                # the producer must be blocked if the put amount would
                # overflow the bucket
                if self._amt + self._bucket.level > self._bucket.capacity:
                    #log.debug('producer try-put(amt=%r) blocked from bucket (level=%r) at %g' %
                    #          (self._amt, self._bucket.level, self._bucket._sim.now))
                    return self._bucket._p_sem._try_wait() # must be True
                else:
                    #log.debug('no producer blocked to try-put(amt=%r) to bucket (level=%r) at %g' %
                    #          (self._amt, self._bucket.level, self._bucket._sim.now))
                    return False

            def _cancel_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None
                self._bucket._make_p_renege(p)
                #log.debug('producer cancels try-put(amt=%r) to bucket (level=%r) at %g' %
                #          (self._amt, self._bucket.level, self._bucket._sim.now))
                self._bucket._p_sem._cancel_wait()

            def _commit_wait(self):
                p = self._bucket._sim.cur_process()
                assert p is not None
                #log.debug('producer try-put(amt=%r) unblocked from bucket (level=%r) at %g' %
                #          (self._amt, self._bucket.level, self._bucket._sim.now))

                # the put amount can be satisfied now if the producer
                # process reaches here; we increase the level and
                # unblock as many consumer processes as we can
                self._bucket.level += self._amt
                lvl = self._bucket.level
                nc = self._bucket._c_sem._next_unblock()
                while nc is not None:
                    # if the consumer process to be unblocked next has
                    # enough quantity in bucket now for the get amount,
                    # we unblock it
                    if self._bucket._c_arrivals[nc][1] <= lvl:
                        #log.debug('producer try-put(amt=%r) unblocks consumer get(amt=%r) in bucket (level=%r)' %
                        #          (self._amt, self._bucket._c_arrivals[nc][1], self._bucket.level))
                        lvl -= self._bucket._c_arrivals[nc][1]
                        self._bucket._c_sem.signal()
                        nc = self._bucket._c_sem._next_unblock()
                    else: break

                self._bucket._make_p_departure(p, self._amt)

            def _true_trappable(self):
                return self._bucket._p_sem

        return _PutTrappable(self, amt)
    
    def getters_in_queue(self):
        return len(self._c_arrivals)

    def putters_in_queue(self):
        return len(self._p_arrivals)

    def _make_p_arrival(self, p, amt):
        self._p_arrivals[p] = (self._sim.now, amt)
        if self.stats is not None:
            self.stats._sample("puts", (self._sim.now, amt))
            self.stats._sample("put_queues", (self._sim.now, len(self._p_arrivals)))

    def _make_c_arrival(self, p, amt):
        self._c_arrivals[p] = (self._sim.now, amt)
        if self.stats is not None:
            self.stats._sample("gets", (self._sim.now, amt))
            self.stats._sample("get_queues", (self._sim.now, len(self._c_arrivals)))

    def _make_p_renege(self, p):
        t,a = self._p_arrivals.pop(p) # throw a KeyError if not in dictionary
        if self.stats is not None:
            self.stats._sample("put_times", self._sim.now-t)
            self.stats._sample("put_queues", (self._sim.now, len(self._p_arrivals)))

    def _make_c_renege(self, p):
        t,a = self._c_arrivals.pop(p) # throw a KeyError if not in dictionary
        if self.stats is not None:
            self.stats._sample("get_times", self._sim.now-t)
            self.stats._sample("get_queues", (self._sim.now, len(self._c_arrivals)))

    def _make_p_departure(self, p, amt):
        t,a = self._p_arrivals.pop(p) # throw a KeyError if not in dictionary
        assert a == amt
        if self.stats is not None:
            self.stats._sample("put_times", self._sim.now-t)
            self.stats._sample("put_queues", (self._sim.now, len(self._p_arrivals)))
            self.stats._sample("levels", (self._sim.now, self.level))
            
    def _make_c_departure(self, p, amt):
        t,a = self._c_arrivals.pop(p) # throw a KeyError if not in dictionary
        assert a == amt
        if self.stats is not None:
            self.stats._sample("get_times", self._sim.now-t)
            self.stats._sample("get_queues", (self._sim.now, len(self._c_arrivals)))
            self.stats._sample("levels", (self._sim.now, self.level))
