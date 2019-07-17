# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 9, 2019
# Last Update: Time-stamp: <2019-07-17 06:34:16 liux>
###############################################################

from collections import deque

from .utils import QDIS, DataCollector, TimeSeries, DataSeries, TimeMarks
from .trappable import Trappable
from .trap import Trap
from .sync import *

__all__ = ["Mailbox", "send"]

class Mailbox(object):
    """A mailbox for deliverying messages.

    A mailbox is a facility designed specifically for message passing
    between processes or functions. A mailbox consists of one or more
    compartments or partitions. A sender can send a message to one of
    the partitions of the mailbox (which, by default, is partition 0)
    with a time delay. The message will be delivered to the designated
    mailbox partition at the expected time. Messages arriving at a
    mailbox will be stored in the individual partitions until a
    receiver retrieves them and removes them from the mailbox.

    In Python, the concept of messages (or mails in the sense of a
    mailbox) takes a broader meaning.  Basically, they could be any
    Python objects. And since Python is a dynamically-typed language,
    one can also use objects of different types as messages.

    A mailbox is designed to be used for both process scheduling (in
    process-oriented simulation) and direct-event scheduling (for
    event-driven simulation). In the former, a process can send as
    many messages to a mailbox as it needs to (by repeatedly calling
    the mailbox's send() method). The simulation time does not advance
    since send() does not block. As a matter of fact, one does not
    need to call send() in a process context at all. In this sense, a
    mailbox can be considered as a store with an infinite storage
    capacity.  An important difference, however, is that one can send
    messages to mailboxes and specify a different delay each time.

    One or more processes can call the mailbox's recv() method trying
    to receive the messages arrived at a mailbox partition. If there
    are one or more messages already stored at the mailbox partition,
    the process will retrieve the messages from the partition and
    return them (in a list) without delay. Here, "retrieve" means the
    messages indeed will be removed from the mailbox partition.  In
    doing so, subsequent calls to recv() will no longer find the
    retrieved messages in the mailbox partition. If there are no
    messages currently in the mailbox partition when calling recv(),
    the processes will be suspended pending on the arrival of a new
    message to the designated mailbox partition. Once a message
    arrives, *all* waiting processes at the partition will be
    unblocked and return with the retrieved message.

    There are two ways for the recv() method to retrieve the
    messages. One is to retrieve all messages from the mailbox
    partition; the other is to retrieve only the first one stored in
    the mailbox partition. The user can specify which behavior is
    desirable by setting the 'isall' parameter when calling the recv()
    method.  Regardless of the process trying to receive all messages
    or just one message, if there are multiple processes waiting to
    receive at a mailbox partition, it is possible a process wakes up
    upon a message's arrival and return empty handed (because another
    process may have taken the message from the mailbox). Simulus do
    not dictate, when multiple processes are waiting to receive a
    message, which one will wake up first to retrieve the messages.
    It'd be arbitrary since simulus handles simultaneous events
    without model specified ordering.

    A mailbox can also be used in the direct-event scheduling context
    (event-driven approach). In this case, the user can add one or
    more callback functions to a mailbox partition. A callback
    function can be any user-defined function. Whenever a message is
    delivered to a mailbox partition, *all* callback functions
    attached to the mailbox partition will be invoked.

    Within a callback function, the user has the option to either peek
    at the mailbox or retrieve (or do nothing of the kind, of course).
    One can call the peek() method to just look at the messages
    arrived at a mailbox partition. In this case, a list is returned
    containing all stored messages in the partition. The messages are
    not removed from the mailbox. One can also also call the
    retrieve() method. In this case, the user is given the option to
    retrieve just one of the messages or all messages. Again,
    "retrieve" means to remove the message or messages from the
    mailbox. Like recv(), the user passes in a boolean 'isall'
    argument to indicate which behavior is desirable.

    """

    def __init__(self, sim, nparts, min_delay, name, dc):
        """A mailbox should be created using simulator's mailbox() function. A
        mailbox has a number of compartments or partitions, a minimum
        delay, a name, and DataCollector instance for statistics
        collection."""

        class _Compartment(object):
            """One compartment or partition of the mailbox."""
            def __init__(self, mbox, dc):
                self.callbacks = []
                self.trap = Trap(mbox._sim)
                self.msgbuf = deque()
                self.stats = dc
                if self.stats is not None:
                    for k, v in dc._attrs.items():
                        if k in ('messages',):
                            if not isinstance(v, TimeSeries):
                                raise TypeError("Mailbox DataCollector: '%s' not timeseries" % k)
                        elif k in ('arrivals', 'retrievals'):
                            if not isinstance(v, TimeMarks):
                                raise TypeError("Mailbox DataCollector: '%s' not timemarks" % k)
                        else:
                            raise ValueError("Mailbox DataCollector: '%s' unrecognized" % k)

            def peek(self):
                return list(self.msgbuf) # a shallow copy
        
            def retrieve(self, isall):
                if isall:
                    ret = list(self.msgbuf)
                    self.msgbuf.clear()
                    return ret
                else:
                    try:
                        return self.msgbuf.popleft()
                    except IndexError:
                        return None

        self._sim = sim
        self.nparts = nparts
        self.min_delay = min_delay
        self.name = name

        if nparts > 1:
            if dc is None: dc = [None]*nparts
            if not isinstance(dc, (list,tuple)):
                raise TypeError("Mailbox(dc=%r): list/tuple of DataCollectors expected" % dc)
            if nparts != len(dc):
                raise TypeError("Mailbox(dc=%r): %d DataCollectors expected" % (dc, nparts))
        else:
            if dc is not None and not isinstance(dc, DataCollector):
                raise TypeError("Mailbox(dc=%r): DataCollector expected" % dc)
            dc = [dc]
        self._parts = [_Compartment(self, x) for x in dc]

    def send(self, msg, delay=None, part=0):
        """Send a message to a mailbox partition.

        Args:
            msg (object): a message can be any Python object; but it
                cannot be None
        
            delay (float): the delay after which the message is expected
                to be delivered to the mailbox; if it is ignored, the
                delay will be set to be the min_delay of the mailbox
                (which is by default zero); if it is set, the delay
                value must not be smaller than the min_delay of the
                mailbox
        
            part (int): the partition number of the mailbox to which the
                message is expected to be delivered; the default is
                zero

        Returns:
            This method returns the future event scheduled for the
            message delivery. It's an opaque object to the user, but
            the user can use it to cancel or reschedule the event.

        """
        
        if msg is None:
            raise ValueError("Mailbox.send() message is None")
        if delay is None:
            delay = self.min_delay
        else:
            if delay < self.min_delay:
                raise ValueError("Mailbox.send(delay=%r) less than min_delay (%r)" %
                                 (delay, self.min_delay))
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.send(part=%r) out of range" % part)
        return self._sim.sched(self._mailbox_event, msg, part, offset=delay)

    def recv(self, part=0, isall=True):
        """Receive messages from a mailbox partition.

        This method must be called within a process context (in a
        starting function of a process or at a function called
        directly or indirectly from the starting function). If the
        mailbox partition is empty when the call is made, the process
        will be put on hold until a message arrives.

        Args:
            part (int): the partition number of the mailbox from which
                messages are expected to be received

            isall (boolean): if True (default), this method will
                retrieve all messages from the mailbox and return
                them; if False, this method will only retrieve the
                first arrived message

        Returns:
            This method returns a list containing all the messages
            currently stored at the mailbox partition, if 'isall' is
            True (by default). If the partition is empty, however,
            this method returns an empty list. On the other hand, if
            'isall' is False, this method returns only the first
            arrived message (not wrapped in a list). If the partition
            is empty, this method would return None.

        """
        
        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise RuntimeError("Mailbox.recv() outside process context")
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.recv(part=%r) out of range" % part)
        if self._parts[part].stats is not None:
            self._parts[part].stats._sample("retrievals", self._sim.now)
        if len(self._parts[part].msgbuf) == 0:
            self._parts[part].trap.wait()
        return self.retrieve(part, isall)
    
    def receiver(self, part=0, isall=True):
        """Return a trappable for receiving messages from the mailbox.  This
        method is similar to the recv() method, except that it returns
        a trappable on which one can apply conditional wait using the
        simulator's wait() function."""
        
        class _RecvTrappable(Trappable):
            """The trappable for conditional wait to receive messages from a
            mailbox partition.""" 
            
            def __init__(self, mbox, part, isall):
                super().__init__(mbox._sim)
                self._mbox = mbox
                self._part = part
                self._isall = isall
        
            def _try_wait(self):
                if self._mbox._parts[self._part].stats is not None:
                    self._mbox._parts[self._part].stats._sample("retrievals",
                                                                self._mbox._sim.now)
                if len(self._mbox._parts[self._part].msgbuf) > 0:
                    return False
                return self._mbox._parts[self._part].trap._try_wait() # must be true

            def _commit_wait(self):
                if self._mbox._parts[self._part].trap.state == Trap.TRAP_SET:
                    self._mbox._parts[self._part].trap._commit_wait()
                self.retval = self._mbox.retrieve(self._part, self._isall)

            def _cancel_wait(self):
                if self._mbox._parts[self._part].trap.state == Trap.TRAP_SET:
                    self._mbox._parts[self._part].trap._cancel_wait()

            def _true_trappable(self):
                return self._mbox._parts[self._part].trap
            
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.receiver(part=%r) out of range" % part)
        return _RecvTrappable(self, part, isall)

    def add_callback(self, func, *args, part=0, **kwargs):
        """Add a callback function to a mailbox partition.

        Args:
            func (function): the callback function, which can be an
                arbitrary user-defined function

            args (list): the positional arguments as a list to be passed
                to the callback function when it's invoked upon the
                message arrival

            part (int): the partition number of the mailbox from which
                messages are expected to be received

            kwargs (dict): the keyworded arguments as a dictionary to be
                passed to the callback function when it's invoked upon
                the message arrival

        """
        
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.send(part=%r) out of range" % part)
        self._parts[part].callbacks.append((func, args, kwargs))

    def peek(self, part=0):
        """Return the messages currently stored in a mailbox partition; the
        messages are not removed.

        Args:
            part (int): the partition number of the mailbox

        Returns:
            This method returns a list containing all the messages
            currently stored at the designed partition of the mailbox

        """ 
        
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.peek(part=%r) out of range" % part)
        return self._parts[part].peek()
        
    def retrieve(self, part=0, isall=True):
        """Retrieve messages from a mailbox partition.

        Args:
            part (int): the partition number of the mailbox from which
                messages are retrieved; the default is zero

            isall (boolean): if True (default), this method will
                retrieve all messages from the mailbox and return
                them; if False, this method will only retrieve the
                first arrived message

        Returns:
            This method returns a list containing all the messages
            currently stored at the designated mailbox partition, if
            'isall' is True (by default). If the partition is empty,
            however, this method returns an empty list. On the other
            hand, if 'isall' is False, this method returns only the
            first arrived message (not wrapped in a list). If the
            partition is empty in this case, this method would return
            None.

        """
       
        if part < 0 or part >= self.nparts:
            raise IndexError("Mailbox.retrieve(part=%r) out of range" % part)
        msgs = self._parts[part].retrieve(isall)
        if self._parts[part].stats is not None:
            self._parts[part].stats._sample("messages",
                (self._sim.now, len(self._parts[part].msgbuf)))
        return msgs

    def _mailbox_event(self, msg, part):
        """Handle the mailbox delivery event (scheduled by send)."""
        
        self._parts[part].msgbuf.append(msg)
        if self._parts[part].stats is not None:
            self._parts[part].stats._sample("arrivals", self._sim.now)
            self._parts[part].stats._sample("messages",
                (self._sim.now, len(self._parts[part].msgbuf)))
        if self._parts[part].trap.state == Trap.TRAP_SET:
            self._parts[part].trap.trigger() # release all waiting processes
            self._parts[part].trap = Trap(self._sim) # renew the trap
        for func, args, kwargs in self._parts[part].callbacks:
            func(*args, **kwargs)

def send(name, msg, delay=None, part=0):
    """Send a messsage to a named mailbox.

    Args:
        name (string): the name of the mailbox to which the
                message is expected to be delivered

        msg (object): a message can be any Python object; but it
                cannot be None
        
        delay (float): the delay after which the message is expected
                to be delivered to the mailbox; if it is ignored, the
                delay will be set to be the min_delay of the mailbox
                (which is by default zero); if it is set, the delay
                value must not be smaller than the min_delay of the
                mailbox
        
        part (int): the partition number of the mailbox to which the
                message is expected to be delivered; the default is
                zero

    Returns:
        This method returns the future event scheduled for the message
        delivery. It's an opaque object to the user, but the user can
        use it to cancel or reschedule the event.

    """

    mb = _Sync_.get_mailbox(name)
    if mb is None:
        raise ValueError("send(%s) to mailbox not found" % name)
    return mb.send(msg, delay, part)
