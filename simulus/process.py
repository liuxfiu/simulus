# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2015
# Last Update: Time-stamp: <2019-06-17 08:00:56 liux>
###############################################################

# greenlet must be installed as additional python package
from greenlet import greenlet
from .event import _ProcessEvent

__all__ = ["_Process"]

# process runtime state
_PSTATE_STARTED       = 0
_PSTATE_RUNNING       = 1
_PSTATE_SUSPENDED     = 2
_PSTATE_TERMINATED    = 3

class _Process(object):
    """A process is an independent thread of execution."""

    def __init__(self, sim, name, func, params):
        self.sim = sim
        self.name = name
        self.params = params
        self.state = _PSTATE_STARTED
        self.main = None
        #self.first_time = True
        #self.vert = greenlet(func)
        self.func = func
        self.vert = greenlet(self.invoke)

    def activate(self):
        assert self.state == _PSTATE_STARTED or \
            self.state == _PSTATE_SUSPENDED or \
            self.state == _PSTATE_RUNNING
        
        if self.state != _PSTATE_RUNNING:
            self.state = _PSTATE_RUNNING
            self.sim.running_procs.append(self)

    def deactivate(self, newstate):
        self.state = newstate

    def invoke(self):
        # we can't allow the function to return; greenlet would behave
        # strangely in that case; to prevent that from happenning, we
        # wrap the function call around with this method, which ends
        # by suspending the current process forever
        self.func(self.sim, self.params)
        self.suspend()

    def run(self):
        # this has to be from the main event loop
        self.main = greenlet.getcurrent()
        # because we wrap around the function call, we no longer need
        # to distinguish between the first caller and subsequent ones
        # self.vert.switch(self.sim, self.params)
        self.vert.switch()

        # check if the greenlet has finished itself (this seems to
        # have no effect at all)
        if self.vert.dead:
            assert self.state == _PSTATE_RUNNING
            self.deactivate(_PSTATE_TERMINATED)

    def sleep(self, until):
        assert self.vert
        assert not self.vert.dead
        assert self.state == _PSTATE_RUNNING
        assert self.sim.cur_proc == self
        assert self.sim.now <= until

        e = _ProcessEvent(until, self, self.name)
        self.sim.event_list.insert(e)
        self.deactivate(_PSTATE_SUSPENDED)
        self.main.switch()

    def suspend(self):
        assert self.vert
        assert not self.vert.dead
        assert self.state == _PSTATE_RUNNING
        assert self.sim.cur_proc == self
        self.deactivate(_PSTATE_SUSPENDED)
        self.main.switch()

#    def terminate(self):
#        assert self.vert
#        assert not self.vert.dead
#        assert self.state == _PSTATE_RUNNING
#        assert self.sim.cur_proc == self
#        self.deactivate(_PSTATE_TERMINATED)
#        raise greenlet.GreenletExit
