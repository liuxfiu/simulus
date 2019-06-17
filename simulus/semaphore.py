# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 15, 2019
# Last Update: Time-stamp: <2019-06-17 15:06:36 liux>
###############################################################

from collections import deque

__all__ = ["_Semaphore"]

class _Semaphore(object):
    """A semaphore used for process synchronization."""

    def __init__(self, sim, val):
        self.sim = sim
        self.val = val
        self.blocked = deque()

    def wait(self):
        if self.sim.cur_proc != None:
            self.val -= 1
            if self.val < 0:
                self.blocked.append(self.sim.cur_proc)
                self.sim.cur_proc.suspend()
        else:
            raise Exception("semaphore.wait() outside process context")

    def signal(self):
        self.val += 1
        if len(self.blocked)>0:
            p = self.blocked.popleft()
            p.activate()
