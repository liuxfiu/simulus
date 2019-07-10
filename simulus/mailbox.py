# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 9, 2019
# Last Update: Time-stamp: <2019-07-09 21:55:51 liux>
###############################################################

from .utils import QDIS, DataCollector
from .trappable import Trappable
from .trap import Trap

__all__ = ["Mailbox"]

class _Compartment(Trappable):
    """One compartment of the mailbox; it's also a trappable for
    conditional wait on the compartment."""

    def __init__(self, mbox):
        super().__init__(mbox._sim)
        self._callbacks = []
        self._trap = Trap(self._sim)
        self._msgbuf = []

    def _try_wait(self):
        if len(self._msgbuf) > 0:
            return False
        return self._trap._try_wait() # must be true

    def _commit_wait(self):
        if self._trap.state == Trap.TRAP_SET:
            self._trap._commit_wait()
        self.retval = self._msgbuf
        self._msgbuf = []

    def _cancel_wait(self):
        if self._trap.state == Trap.TRAP_SET:
            self._trap._cancel_wait()

    def _true_trappable(self):
        return self._trap
            
class Mailbox(Trappable):
    """A mailbox is for deliverying messages.

    A mailbox is a facility designed specifically for message passing
    between processes or functions. A mailbox can have one or more
    compartments or partitions. A sender can send a message to one of
    the compartments of the mailbox (which, by default, is partition
    0) with a specific time delay. The message will be delievered to
    the designated partition of the mailbox at the specified
    time. Message are stored in the individual compartments of the
    mailbox until a receiver retrieves them. A message here has a
    broader meaning: it can be any Python object.

    A process can call recv() to receive the messages from a mailbox
    partition. If there are no messages currently in the designated
    mailbox partition, the process will be suspended waiting for the
    message's arrival. Once the process is unblocked, the process
    retrieves all the messages from the given mailbox partition and
    returns them.

    """

    def __init__(self, sim, nparts, min_delay, name, dc):
        """A mailbox should be created using simulator's mailbox() function. A
        mailbox has a number of compartments or partitions, a minimum
        delay, a name, and DataCollector instance for statistics
        collection."""

        super().__init__(sim)
        self.nparts = nparts
        self.min_delay = min_delay
        self.name = name
        self.stats = dc
        self._parts = [_Compartment(self) for _ in range(nparts)]

    def send(self, msg, delay=0, part=0):
        if msg is None:
            raise ValueError("Mailbox.send() empty message")
        if delay < self.min_delay:
            raise ValueError("Mailbox.send(delay=%r) less than min_delay (%r)" %
                             (delay, self.min_delay))
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.send(part=%r) out of range" % part)
        self._sim.sched(self._process_mailbox_event, msg, part, offset=delay)

    def recv(self, part=0):
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Mailbox.recv() outside process context")

        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.recv(part=%r) out of range" % part)
        if len(self._parts[part]._msgbuf) == 0:
            self._parts[part]._trap.wait()
        return self.retrieve(part)
    
    def receiver(self, part=0):
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.receiver(part=%r) out of range" % part)
        if part == 0: return self
        return self._parts[part]

    def add_callback(self, func, *args, part=0, **kwargs):
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.send(part=%r) out of range" % part)
        self._parts[part]._callbacks.append((func, args, kwargs))

    def check(self, part=0):
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.check(part=%r) out of range" % part)
        return list(self._parts[part]._msgbuf) # a shallow copy
        
    def retrieve(self, part=0):
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.retrieve(part=%r) out of range" % part)
        msgs = self._parts[part]._msgbuf
        self._parts[part]._msgbuf = []
        return msgs
    
    def _process_mailbox_event(self, msg, part):
        self._parts[part]._msgbuf.append(msg)
        if self._parts[part]._trap.state == Trap.TRAP_SET:
            self._parts[part]._trap.trigger() # release the waiting processes
            self._parts[part]._trap = Trap(self._sim) # renew the trap
        for func, args, kwargs in self._parts[part]._callbacks:
            func(*args, **kwargs)
       
    def _try_wait(self):
        return self._parts[0]._try_wait()

    def _commit_wait(self):
        self._parts[0]._commit_wait()
        self.retval = self._parts[0].retval

    def _cancel_wait(self):
        self._parts[0]._trap._cancel_wait()

    def _true_trappable(self):
        return self._parts[0]._true_trappable()

