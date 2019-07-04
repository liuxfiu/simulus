# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-07-03 21:53:39 liux>
###############################################################

__all__ = ["_Sync_", "sync"]

class _Sync_(object):
    # a map from names to simulator instances
    named_simulators = {}

    @staticmethod
    def get_simulator(name):
        """Return the simulator with the given name, or None if no such
        simulation can be found."""
        return _Sync_.named_simulators[name]

    @staticmethod
    def register_simulator(name, sim):
        # may possibly replace an earlier simulator of the same name
        _Sync_.named_simulators[name] = sim
    
def sync(sims, lookahead):
    raise Exception("simulus.sync() not implemented")
