# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-07-05 23:21:36 liux>
###############################################################

__all__ = ["_Trappable"]

class _Trappable(object):
    """The base class for all trappables. 

    This class defines an abstract interface; all subclasses must
    consider overwrite the methods definded here. These methods are
    expected to be invoked from the simulator.wait() function.

    """

    def __init__(self, sim):
        self._sim = sim

    def _try_wait(self): pass
    def _commit_wait(self): pass
    def _cancel_wait(self): pass
    def _true_trappable(self): return self
