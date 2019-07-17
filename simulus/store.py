# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-17 05:31:29 liux>
###############################################################

from collections import deque

from .utils import QDIS, DataCollector, TimeSeries, DataSeries, TimeMarks
from .trappable import Trappable
from .semaphore import Semaphore

__all__ = ["Store"]

class Store(object):
    """A store for synchronizing producer and consumer processes.

    A store is a facility either for storing countable objects (such
    as jobs in a queue, packets in a network router, and io requests
    at a storage device), or for storing uncountable quantities or
    volumes (such as gas in a tank, water in a reservoir, and battery
    power in a mobile computer). The user can determine which kind of
    store (for countable objects or for uncountable quantities) should
    apply upon use.

    A store has a maximum capacity, which is a positive quantity
    specified either as an integer or as a float-point number. A store
    can also tell its current storage level, which goes between zero
    and the maximum capacity.

    One or several processes can put objects or quantities into the
    store. They are called producer processes. One or several
    processes can get objects or quantities from the store. They are
    called consumer processes. The producer process and the consumer
    process is determined by its performed action on the store. They
    can be the same process.

    A producer process calls the put() method to deposit one or more
    objects, or some quantities into the store. The put amount shall
    be specified as an argument (default is one). The current storage
    level will increase accordingly as a result. However, if a
    producer process tries to put more objects or quantities than the
    store's capacity, the producer process will be blocked. The
    process will remain blocked until the current storage level
    decreases (by some other processes getting objects or quantities
    from the store) so that there is room for putting all the objects
    or quantities.

    Similarly, a consumer process calls the get() method to retrieve
    one or more objects, or some quantities from the store. The get
    amount shall be specified as an argument (default is one).  The
    current storage level will decrease accordingly as a result. If a
    consumer process tries to get more objects or quantities than what
    is avaialble at the store, the consumer process will be blocked.
    The process will remain blocked until the current storage level
    goes above the requested amount (by some other processes putting
    objects or quantities into the store).

    The store facility can actually be used for storing real
    (countable) Python objects, if the user calls the put() method and
    passes in a Python object or a list/tuple of Python objects using
    the keyworded 'obj' argument. In this case, the put amount must
    match with the number of objects. These Python objects can be
    retrieved in a first-in-first-out fashion by consumer processes
    calling the get() method, which specifies the get amount. The same
    number of Python objects will be returned, either as a list if the
    get amount is greater than one, or as the object itself if the get
    amount is one.

    """
    
    def __init__(self, sim, capacity, initlevel, initobj, name, p_qdis, c_qdis, dc):
        """A store should be created using simulator's store() function. A
        store has a capacity (must be positive), an initial level,
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

        # one can choose to use the store either with or without
        # storing real objects; whatever the case, the user has to be
        # consistent
        self._obj_store = None
        if initlevel==0:
            self._obj_decided = False
            if initobj != None:
                raise ValueError("Store(initlevel=0) initobj not None")
        else:
            self._obj_decided = True
            if initobj != None:
                if initlevel == 1:
                    # if it's expected to be a single object (although
                    # the object itself could be a list or tuple)
                    self._obj_store = deque()
                    self._obj_store.append(initobj)
                else:
                    # otherwise, the object has to be a list or tuple
                    # and the number must match with the amount
                    if not isinstance(initobj, (list, tuple)) or \
                       len(initobj) != initlevel:
                        raise ValueError("Store(initlevel=%r, initobj=%r) unmatched "
                                         "number of objects" % (initlevel, initobj))
                    self._obj_store = deque(initobj) # shallow copy from the list or tuple

        if self.stats is not None:
            for k, v in dc._attrs.items():
                if k in ('puts', 'put_queues', 'gets', 'get_queues', 'levels'):
                    if not isinstance(v, TimeSeries):
                        raise TypeError("Store DataCollector: '%s' not timeseries" % k)
                elif k in ('put_times', 'get_times'):
                    if not isinstance(v, DataSeries):
                        raise TypeError("Store DataCollector: '%s' not dataseries" % k)
                else:
                    raise ValueError("Store DataCollector: '%s' unrecognized" % k)
            self.stats._sample("levels", (sim.init_time, initlevel))

    def get(self, amt=1):
        """Retrieve objects or quantities from the store.

        Args:
            amt (int, float): the number of countable objects or the
                amount of uncountable quantities to be retrieved all
                at once (default is one)

        Returns:
            This method returns none if no Python objects are
            stored. Otherwise, if 'amt' is one, this method returns
            the object that was first put into the store; if the 'amt'
            is more than one, this method returns the 'amt' number of
            objects in a list. The objects are stored first in and
            first out.

        """
        
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Store.get() outside process context")

        if self.capacity < amt:
            raise ValueError("Store.get(amt=%r) more than capacity (%r)" %
                             (amt, self.capacity))
        if amt <= 0:
            raise ValueError("Store.get(amt=%r) non-positive amount" % amt)

        self._make_c_arrival(p, amt)

        # the consumer must be blocked if there isn't enough quantity
        # in the store
        if amt > self.level:
            self._c_sem.wait()

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
                lvl += self._p_arrivals[np][1]
                self._p_sem.signal()
                np = self._p_sem._next_unblock()
            else: break

        return self._make_c_departure(p, amt)

    def put(self, amt=1, *, obj=None):
        """Deposit objects or quantities to the store.

        Args:
            amt (int, float): the number of countable objects or the
                amount of uncountable quantities to be deposited all
                at once (default is one)

            obj (object): the python object or a list/tuple of python
                objects to be deposited to the store; this is
                optional; however, if provided, this is a mandatory
                keyworded argument, i.e., user must use the 'obj'
                keyword if providing the object(s) after all

        This method does not return a value.

        """
        
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Store.put() outside process context")

        if self.capacity < amt:
            raise ValueError("Store.put(amt=%r) more than capacity (%r)" %
                             (amt, self.capacity))
        if amt <= 0:
            raise ValueError("Store.put(amt=%r) non-positive amount" % amt)

        # if object is provided, it must match with the amount
        if obj is not None:
            if amt == 1:
                # if it's expected to be a single object (the object
                # itself could be a list or tuple), we put it inside a
                # list so it'll be easier for later processing
                obj = [obj]
            else:
                # otherwise, the object has to be a list or tuple and
                # the number must match with the amount
                if not isinstance(obj, (list, tuple)) or \
                   len(obj) != amt:
                    raise ValueError("Store.put(amt=%r, obj=%r) unmatched "
                                     "number of objects" % (amt, obj))
            
        self._make_p_arrival(p, amt, obj)

        # the producer will be blocked if the put amount would
        # overflow the store
        if amt + self.level > self.capacity:
            self._p_sem.wait()

        # the put amount can be satisfied now if the producer process
        # reaches here; we increase the level and unblock as many
        # consumer processes as we can
        self.level += amt
        lvl = self.level
        nc = self._c_sem._next_unblock()
        while nc is not None:
            # if the consumer process to be unblocked next has enough
            # quantity in store now for the get amount, we unblock it
            if self._c_arrivals[nc][1] <= lvl:
                lvl -= self._c_arrivals[nc][1]
                self._c_sem.signal()
                nc = self._c_sem._next_unblock()
            else: break

        self._make_p_departure(p, amt)

    def getter(self, amt=1):
        """Return a trappable for getting objects or quantities from the
        store. This function is similar to the get() method, except
        that it returns a trappable (like traps, semaphores, and
        resources) on which one can apply conditional wait using the
        simulator's wait() function."""

        class _GetTrappable(Trappable):
            """The store's trappable for conditional wait on get."""
            
            def __init__(self, store, amt):
                super().__init__(store._sim)
                self._store = store
                self._amt = amt

                if store.capacity < amt:
                    raise ValueError("Store.getter(amt=%r) more than capacity (%r)" %
                                     (amt, store.capacity))
                if amt <= 0:
                    raise ValueError("Store.getter(amt=%r) non-positive amount" % amt)

            def _try_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None
                
                self._store._make_c_arrival(p, self._amt)

                # the consumer will be blocked if there isn't enough
                # quantity in the store
                if self._amt > self._store.level:
                    return self._store._c_sem._try_wait() # must be True
                else:
                    return False

            def _cancel_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None
                self._store._make_c_renege(p)
                self._store._c_sem._cancel_wait()

            def _commit_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None

                # the get amount can be satisfied if the consumer
                # process reaches here; we lower the level and unblock
                # as many producer processes as we can
                self._store.level -= self._amt
                lvl = self._store.level
                np = self._store._p_sem._next_unblock()
                while np is not None:
                    # if the producer process to be unblocked next has
                    # room now for the put amount, we unblock it
                    if self._store._p_arrivals[np][1] + lvl <= self._store.capacity:
                        lvl += self._store._p_arrivals[np][1]
                        self._store._p_sem.signal()
                        np = self._store._p_sem._next_unblock()
                    else: break
                    
                self.retval = self._store._make_c_departure(p, self._amt)

            def _true_trappable(self):
                return self._store._c_sem

        return _GetTrappable(self, amt)
    
    def putter(self, amt=1, *, obj=None):
        """Return a trappable for putting objects or quantities to the
        store. This function is similar to the put() method, except
        that it returns a trappable (like traps, semaphores, and
        resources) on which one can apply conditional wait using the
        simulator's wait() function."""

        class _PutTrappable(Trappable):
            """The store's trappable for conditional wait on put."""
            
            def __init__(self, store, amt, obj):
                super().__init__(store._sim)
                self._store = store
                self._amt = amt
                self._obj = obj

                if store.capacity < amt:
                    raise ValueError("Store.putter(amt=%r) more than capacity (%r)" %
                                     (amt, store.capacity))
                if amt <= 0:
                    raise ValueError("Store.putter(amt=%r) non-positive amount" % amt)

                # if object is provided, it must match with the amount
                if obj is not None:
                    if amt == 1:
                        # if it's expected to be a single object (the
                        # object itself could be a list or tuple), we
                        # put it inside a list so it'll be easier for
                        # later processing
                        self._obj = [obj]
                    else:
                        # otherwise, the object has to be a list or
                        # tuple and the number must match with the
                        # amount
                        if not isinstance(obj, (list, tuple)) or \
                           len(obj) != amt:
                            raise ValueError("Store.putter(amt=%r, obj=%r) unmatched "
                                             "number of objects" % (amt, obj))

            def _try_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None

                self._store._make_p_arrival(p, self._amt, self._obj)

                # the producer must be blocked if the put amount would
                # overflow the store
                if self._amt + self._store.level > self._store.capacity:
                    return self._store._p_sem._try_wait() # must be True
                else:
                    return False

            def _cancel_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None
                self._store._make_p_renege(p)
                self._store._p_sem._cancel_wait()

            def _commit_wait(self):
                p = self._store._sim.cur_process()
                assert p is not None

                # the put amount can be satisfied now if the producer
                # process reaches here; we increase the level and
                # unblock as many consumer processes as we can
                self._store.level += self._amt
                lvl = self._store.level
                nc = self._store._c_sem._next_unblock()
                while nc is not None:
                    # if the consumer process to be unblocked next has
                    # enough quantity in store now for the get amount,
                    # we unblock it
                    if self._store._c_arrivals[nc][1] <= lvl:
                        lvl -= self._store._c_arrivals[nc][1]
                        self._store._c_sem.signal()
                        nc = self._store._c_sem._next_unblock()
                    else: break

                self._store._make_p_departure(p, self._amt)

            def _true_trappable(self):
                return self._store._p_sem

        return _PutTrappable(self, amt, obj)
    
    def getters_in_queue(self):
        return len(self._c_arrivals)

    def putters_in_queue(self):
        return len(self._p_arrivals)

    def _make_p_arrival(self, p, amt, obj):
        self._p_arrivals[p] = (self._sim.now, amt)
        if obj is not None:
            if self._obj_decided and self._obj_store is None:
                raise RuntimeError("Store() inconsistent use of objects")
            elif not self._obj_decided:
                assert self._obj_store is None
                self._obj_decided = True
                self._obj_store = deque(obj) # shallow copy from the list
            else:
                self._obj_store.extend(obj)
        else:
            if self._obj_decided and self._obj_store is not None:
                raise RuntimeError("Store() inconsistent use of objects")
            elif not self._obj_decided:
                assert self._obj_store is None
                self._obj_decided = True
            
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
        if self._obj_store is not None:
            if amt == 1: 
                return self._obj_store.popleft()
            else:
                ret = []
                for _ in range(amt):
                    ret.append(self._obj_store.popleft())
                return ret
