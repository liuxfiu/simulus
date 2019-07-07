# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-07-07 08:11:02 liux>
###############################################################

# greenlet must be installed as additional python package
from greenlet import greenlet

from .trappable import _Trappable
from .trap import *
from .event import *

__all__ = ["_Process"]

class _Process(_Trappable):
    """A process is an independent thread of execution."""

    # process runtime state
    STATE_STARTED       = 0
    STATE_RUNNING       = 1
    STATE_SUSPENDED     = 2
    STATE_TERMINATED    = 3
    
    def __init__(self, sim, name, func, usr_args, usr_kwargs):
        """A process can only be created using simulator's process() function;
        a process can be created by an other process or within the
        main function."""

        super().__init__(sim)
        self.name = name
        self.func = func
        #self.params = params
        self.args = usr_args
        self.kwargs = usr_kwargs
        self.state = _Process.STATE_STARTED
        self.main = None
        self.vert = greenlet(self.invoke)
        self.priority = 0
        self.trap = Trap(self._sim)
        self.acting_trappables = []

    def activate(self):
        """Move the process into the ready queue."""
        
        if self.state != _Process.STATE_TERMINATED:
            if self.state != _Process.STATE_RUNNING:
                self.state = _Process.STATE_RUNNING
                self._sim._readyq.append(self)
            # otherwise, it already entered the running queue

        # otherwise, the unblocked process (from trap or semaphore or
        # sleep) has been terminated somehow, in which case we simply
        # ignore its activation

    def deactivate(self, newstate):
        """Change the state of the process from running to another state."""
        self.state = newstate

    def invoke(self):
        """Invoke the start function of the process.

        We use this method to wrap around the start function and have
        greenlet to switch control to here. This is because we can't
        allow the start function to simply return; greenlet would
        behave strangely in that case. To prevent that from
        happenning, we wrap the start function around with this
        method, which ends by manually terminating the current
        process.

        """

        #self.func(self._sim, self.params)
        self.func(*self.args, **self.kwargs)
        self.terminate()

    def run(self):
        """Run this process when it's activated. This has to be called within
        the main loop of the simulator."""

        assert self.state == _Process.STATE_RUNNING
        self.main = greenlet.getcurrent()
        self.vert.switch()

        # ... deprecated code:
        # check if the greenlet has finished itself (this seems to
        # have no effect at all)
        #if self.vert.dead:
        #    #assert self.state == _Process.STATE_RUNNING
        #    self.deactivate(_Process.STATE_TERMINATED)

    def sleep(self, until):
        """Schedule a future wakeup event and switch control to the
        simulator's main loop."""
        
        assert self.state == _Process.STATE_RUNNING
        assert self._sim._theproc == self
        assert self._sim.now <= until

        assert self.vert
        assert not self.vert.dead

        e = _ProcessEvent(self._sim, until, self, self.name)
        self._sim._eventlist.insert(e)
        self.deactivate(_Process.STATE_SUSPENDED)
        self.main.switch()

    def suspend(self):
        """Switch control to the simulator's main loop."""
        
        assert self.state == _Process.STATE_RUNNING
        assert self._sim._theproc == self

        assert self.vert
        assert not self.vert.dead
        
        self.deactivate(_Process.STATE_SUSPENDED)
        self.main.switch()

    def terminate(self):
        """Self-terminate this process. 

        One can call this method explicitly to finish the process'
        execution or return from the start function. In the latter
        case, the start function is wrapped with the invoke() method,
        which calls this method to finish its execution.

        This method triggers the trap for the process termination and
        then switches the control back to the simulator's main loop.

        """

        # remember this is self-termination; however, it's possible
        # that a process got killed and ended up here from the end of
        # the invoke() method (... this is probably not true!)
        if self.state != _Process.STATE_TERMINATED:
            assert self.state == _Process.STATE_RUNNING
            assert self._sim._theproc == self

            assert self.vert
            assert not self.vert.dead
        
            self.deactivate(_Process.STATE_TERMINATED)
            self.trap.trigger()

        #raise greenlet.GreenletExit
        self.main.switch()
   
    def _try_wait(self):
        return self.trap._try_wait()

    def _cancel_wait(self):
        self.trap._cancel_wait()

    def _true_trappable(self):
        return self.trap
