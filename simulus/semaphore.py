# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 15, 2019
# Last Update: Time-stamp: <2019-06-30 12:18:48 liux>
###############################################################

from collections import deque
import heapq, random

# ... requires the following:
#   _Trappable
#   Simulator.cur_process()
#   _Process.acting_trappables
#   _Process.get_actcnt()
#   _Process.inc_actcnt()
#   _Process.get_priority()
#   _Process.suspend()
#   _Process.activate()

from .trap import _Trappable

__all__ = ["Semaphore"]


class Semaphore(_Trappable):
    """A semaphore a multi-use signaling mechanism for inter-process
    communication. It is one of the two primitive methods in simulus
    designed for simulation processes to synchronize and communicate
    with one another. (The other primitive method is using traps.)

    A semaphore here implements what is commonly called a "counting
    semaphore." Initially, a semaphore can have a nonnegative integer
    count, which indicates the number of available resources. The
    processes atomically increment the semaphore count when resources
    are added or returned to the pool (using the signal() method) and
    atomically decrement the semaphore count when resources are
    removed (using the wait() method). When the semaphore count is
    zero, it means that there are no available resources. In that
    case, a process trying to decrement the semaphore (to remove a
    resource) will be blocked until more resources are added back to
    the pool. Since semaphores need not be incremented and decremented
    by the same process, they can be used as a signaling mechanism for
    inter-process communication.

    A semaphore is different from a trap. A trap is a one-time
    signaling mechanism. Multiple processes can wait on a trap. Once a
    process triggers the trap, *all* waiting processes will be
    unblocked. A trap cannot be reused: once a trap is sprung,
    subsequent waits will not block the processes and it cannot be
    triggered again. In comparison, a semaphore is a multi-use
    signaling mechanism. Each time a process waits on a semaphore, the
    semaphore value will be decremented. If the value becomes
    negative, the process will be blocked. Each time one signals a
    semaphore, the semaphore value will be incremented. If there are
    blocked processes, *one* of these processes will be unblocked.
    Processes can use the same semaphore repeatedly.

    By default, we use FIFO order (that is, first in first out) to
    unblock processes if multiple processes are waiting on a
    semaphore. Other possible queuing disciplines include LIFO (last
    in first out), RANDOM, and PRIORITY (depending on the 'priority'
    of the processes; a lower value means higher priority). One can
    choose a queuing discipline when the semaphore is created.

    """
    
    # semaphores can apply different queuing disciplines to waiting
    # processes
    QDIS_FIFO     = 0
    QDIS_LIFO     = 1
    QDIS_RANDOM   = 2
    QDIS_PRIORITY = 3

    
    def __init__(self, sim, initval, qdis):
        """A semaphore can only be created using simulator's semaphore()
        function; one can set the initial value (must be nonnegative),
        as well as one of the four queuing disciplines of the
        semaphore.

        """

        self.sim = sim
        assert initval >= 0
        self.val = initval
        self.qdis = qdis
        if self.qdis == Semaphore.QDIS_FIFO or \
           self.qdis == Semaphore.QDIS_LIFO:
            # both FIFO and LIFO use a double ended queue for the
            # blocked processes
            self.blocked = deque()
        else:
            # RANDOM and PRIORITY use a list for the blocked processes
            self.blocked = []


    def wait(self):
        """Waiting on a semphore will decrement its value; and if it becomes
        negative, the process needs to be blocked."""
        
        # we must be in the process context
        p = self.sim.cur_process()
        if p is None:
            raise Exception("Semaphore.wait() outside process context")

        self.val -= 1
        if self.val < 0:
            # enqueue the process and suspend it
            if self.qdis == Semaphore.QDIS_FIFO or \
               self.qdis == Semaphore.QDIS_LIFO:
                self.blocked.append((p, p.get_actcnt()))
            elif self.qdis == Semaphore.QDIS_RANDOM:
                self.blocked.append((p, p.get_actcnt()))
                # when we add a new process, we shuffle it with an
                # existing one in the blocked list
                l = len(self.blocked)
                if l > 1:
                     # get random index (from 0 to l-1) 
                    i = random.randrange(l)
                    if i != l-1:
                        # swap with the last element
                        self.blocked[i], self.blocked[-1] = \
                            self.blocked[-1], self.blocked[i] 
            else:
                # Semaphore.QDIS_PRIORITY
                heapq.heappush(self.blocked, (p.get_priority(), id(p), p, p.get_actcnt()))
            assert len(self.blocked) == -self.val
            p.suspend()
            # so that no other waits can activate the process
            p.inc_actcnt()
        else:
            # nothing to be done; there are no waiting processes
            assert len(self.blocked) == 0

            
    def _try_wait(self):
        """A process tries to wait on the semaphore.
        
        This function is supposed to be called by the simulator's
        wait() function, and should not be called by users
        directly. The function behaves the same as the wait()
        function, except that it's a non-block call: It returns True,
        if the process needs to be suspended; or False if the process
        should not be suspended.  This function is useful if a process
        wants to wait on multiple semaphores or traps.

        """
        
        # we must be in the process context
        p = self.sim.cur_process()
        if p is None:
            raise Exception("Semaphore._try_wait() outside process context")

        self.val -= 1
        if self.val < 0:
            # enqueue the process and suspend it
            if self.qdis == Semaphore.QDIS_FIFO or \
               self.qdis == Semaphore.QDIS_LIFO:
                self.blocked.append((p, p.get_actcnt()))
            elif self.qdis == Semaphore.QDIS_RANDOM:
                self.blocked.append((p, p.get_actcnt()))
                # when we add a new process, we shuffle it with an
                # existing one in the blocked list
                l = len(self.blocked)
                if l > 1:
                     # get random index (from 0 to l-1) 
                    i = random.randrange(l)
                    if i != l-1:
                        # swap with the last element
                        self.blocked[i], self.blocked[-1] = \
                            self.blocked[-1], self.blocked[i] 
            else:
                # Semaphore.QDIS_PRIORITY
                heapq.heappush(self.blocked, (p.get_priority(), id(p), p, p.get_actcnt()))
            assert len(self.blocked) == -self.val
            return True
        else:
            # nothing to be done; there are no waiting processes
            assert len(self.blocked) == 0
            return False
        

    def signal(self):
        """Signaling a semphore increments its value; and if there are waiting
        processes, one of them will be unblocked."""

        self.val += 1
        if len(self.blocked) > 0:
            # there're waiting processes, we unblock one
            if self.qdis == Semaphore.QDIS_FIFO:
                p, cnt = self.blocked.popleft()
            elif self.qdis == Semaphore.QDIS_LIFO:
                p, cnt = self.blocked.pop()
            elif self.qdis == Semaphore.QDIS_RANDOM:
                p, cnt = self.blocked.pop()
            else:
                # Semaphore.QDIS_PRIORITY
                p, cnt = heapq.heappop(self.blocked)[-2:]
                
            # we resume the process only when it has not been
            # activated previously (since a process may simultaneously
            # wait on multiple traps and semaphores)
            if p.get_actcnt() == cnt:
                p.acting_trappables.append(self)
                p.activate()


    # create an alias method
    trigger = signal


