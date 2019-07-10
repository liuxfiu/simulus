# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-07-09 15:04:33 liux>
###############################################################

__all__ = ["_Sync_", "sync"]

class _Sync_(object):
    # a map from names to simulator instances
    named_simulators = {}

    # a map from names to mailbox instances
    named_mailboxs = {}

    @staticmethod
    def get_simulator(name):
        """Return the simulator with the given name, or None if no such
        simulator can be found."""
        return _Sync_.named_simulators[name]

    @staticmethod
    def register_simulator(name, sim):
        # may possibly replace an earlier simulator of the same name
        _Sync_.named_simulators[name] = sim
    
    @staticmethod
    def get_mailbox(name):
        """Return the mailbox with the given name, or None if no such
        mailbox can be found."""
        return _Sync_.named_mailboxs[name]

    @staticmethod
    def register_mailbox(name, mb):
        # may possibly replace an earlier mailbox of the same name
        _Sync_.named_mailboxs[name] = mb

def sync(sims, lookahead):
    raise NotImplementedError("simulus.sync() not implemented")
