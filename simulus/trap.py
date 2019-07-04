# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 27, 2019
# Last Update: Time-stamp: <2019-07-03 21:02:43 liux>
###############################################################

from .trappable import _Trappable

__all__ = ["Trap"]

class Trap(_Trappable):
    """A one-time signaling mechanism for inter-process communication.

    Trap is one of the two primitive methods in simulus designed for
    simulation processes to synchronize and communicate with one
    another. (The other primitive method is using semaphores.)

    A trap has three states. It's "unset" when the trap is first
    created and and nothing has happended to it. It's "set" when one
    or more processes are waiting for the trap to be triggered. It
    turns to "sprung" when the trap has been triggered, after which
    there will be no more processes waiting for the trap.

    The life of a trap is described below. A trap starts with the
    "unset" state when it's created. When a process waits for the
    trap, the trap goes to "set", at which state other processes may
    wait on the trap while the trap remains in the same state. When a
    process triggers the trap and if the trap is in the "set" state,
    *all* processes waiting on the trap will be unblocked and resume
    execution (it's guaranteed there is at least one waiting process
    when the trap is in the "set" state). The trap will then
    transition into the "sprung" state. When a process triggers the
    trap which is in the "unset" state, the trap will just transition
    to the "sprung" state (since there are no processes currently
    waiting on the trap). If the trap is "sprung", further waiting on
    trap will be considered as an no-op; that is, the processes will
    not be suspended. A trap must not be triggered more than once.

    """

    # a trap is in one of the three states
    TRAP_UNSET  = 0
    TRAP_SET    = 1
    TRAP_SPRUNG = 2

    def __init__(self, sim):
        """A trap can only be created using simulator's trap() function; it
        starts from "unset" state and there are no waiting processes."""

        super(Trap, self).__init__(sim)
        self.state = Trap.TRAP_UNSET
        self.blocked = []

    def wait(self):
        """A process waits on the trap."""

        # we must be in the process context
        p = self._sim.cur_process()
        if p is None:
            raise Exception("Trap.wait() outside process context")

        if self.state == Trap.TRAP_UNSET or \
           self.state == Trap.TRAP_SET:
            # when the trap is unset or set, suspend the process
            self.state = Trap.TRAP_SET
            self.blocked.append(p)
            p.suspend()
        else:
            # nothing to be done when the trap is sprung; there are no
            # blocked processes
            assert len(self.blocked) == 0
                
    def trigger(self):
        """Triggering a trap would unblock all waiting processes."""
        
        if self.state == Trap.TRAP_UNSET:
            # no one to wake up when the trap is unset
            assert len(self.blocked) == 0
            self.state = Trap.TRAP_SPRUNG
        elif self.state == Trap.TRAP_SPRUNG:
            # a trap can only be triggered at most once
            raise Exception("Trap.trigger() duplicate action")
        else:
            # when the trap is set, there is at least one process
            # blocked by the trap
            self.state = Trap.TRAP_SPRUNG
            assert len(self.blocked) > 0
            for p in self.blocked:
                p.acting_trappables.append(self)
                p.activate()
            self.blocked.clear()

    def _try_wait(self):
        """Conditional wait on the trap.
        
        This function is supposed to be called by the simulator's
        wait() function, and should not by the users directly. The
        function behaves the same as the wait() function, except that
        it's a non-block call: It returns True, if the process needs
        to be suspended; or False if the process should not be
        suspended.  This function is useful if a process wants to
        conditionally wait on multiple trappables.

        """

        # we must be in the process context
        p = self._sim.cur_process()
        assert p is not None
        
        if self.state == Trap.TRAP_UNSET or \
           self.state == Trap.TRAP_SET:
            # when the trap is unset or set, suspend the process
            self.state = Trap.TRAP_SET
            self.blocked.append(p)
            return True
        else:
            # nothing to be done when the trap is sprung; there are no
            # blocked processes
            assert len(self.blocked) == 0
            return False

    def _cancel_wait(self):
        """Cancel the conditional wait.
        
        This function is supposed to be called by the simulator's
        wait() function, and should not by the users directly. This
        function is called when somehow the previous try-wait didn't
        happen (because of timeout or because the some other wait
        condition has been fulfilled (e.g., the process may wait on
        multiple trappables and one of them, other than this one, has
        been triggered).

        """

        # we must be in the process context
        p = self._sim.cur_process()
        assert p is not None
        
        # the trap must have been set previously
        assert self.state == Trap.TRAP_SET

        self.blocked.remove(p)
        if len(self.blocked) == 0:
            self.state = Trap.TRAP_UNSET
