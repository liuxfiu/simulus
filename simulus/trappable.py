# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-07-08 16:32:13 liux>
###############################################################

__all__ = ["Trappable"]

class Trappable(object):
    """The base class for all trappables. 

    This class defines an abstract interface; all subclasses must
    consider overwrite the methods definded here. These methods are
    expected to be invoked from the simulator.wait() function.

    """

    def __init__(self, sim):
        self._sim = sim
        self.retval = None

    def _try_wait(self): pass
    def _commit_wait(self): pass
    def _cancel_wait(self): pass
    def _true_trappable(self): return self
