# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-07-13 20:23:25 liux>
###############################################################

import random, uuid, argparse, sys

__all__ = ["_Sync_", "sync"]

class _Sync_(object):
    # make sure we init only once (and only once)
    initialized = False

    @staticmethod
    def init():
        """This method is expected to be called by the simulator()
        function. We use this opportunity to initialize everything
        (making sure we do this only once)."""
        if _Sync_.initialized: return
        _Sync_.initialized = True

        # parse command line
        parser = argparse.ArgumentParser()
        parser.add_argument("-s", "--seed", type=int, metavar='SEED', default=None,
                            help="set global pseudo-random seed")
        parser.add_argument("-v", "--verbose", action="store_true",
                            help="enable verbose information")
        parser.add_argument("-x", "--mpi", action="store_true",
                            help="enable mpi for parallel simulation")
        _Sync_.args, _ = parser.parse_known_args()
        if _Sync_.args.seed is not None and \
           (_Sync_.args.seed < 0 or _Sync_.args.seed >= 2**32):
            raise ValueError("Command argument --seed must be between 0 and 2**32-1")

        # initialize mpi if needed
        if _Sync_.args.mpi:
            global MPI
            from mpi4py import MPI
            _Sync_.comm_rank = MPI.COMM_WORLD.Get_rank()
            _Sync_.comm_size = MPI.COMM_WORLD.Get_size()
            if _Sync_.args.verbose:
                print("[%s] simulus running with mpi: comm_size=%d, comm_rank=%d" %
                      (__file__, _Sync_.comm_size, _Sync_.comm_rank))
        else:
            _Sync_.comm_rank = 0
            _Sync_.comm_size = 1
            if _Sync_.args.verbose:
                print("[%s] simulus running in sequential mode" % __file__)

        if _Sync_.args.seed is None:
            old_state = random.getstate()

            # if the global seed is not provided, we use the random
            # module's default random sequence, assuming it's been
            # seeded with the same seed (across different runs and
            # across different ranks)
            _Sync_.namespace = uuid.UUID(int=random.getrandbits(128))
            if _Sync_.args.verbose:
                print("[%s] simulus namespace %s" %
                      (__file__, _Sync_.namespace))

            # now we get a random sequence for each rank: rank 0
            # inherits the random module's default random sequence;
            # other ranks each create one separate random sequence
            # seeded from the default random sequence and the rank
            # itself
            if _Sync_.comm_rank > 0:
                seed = random.randrange(2**32)
                seed += _Sync_.comm_rank
                if seed >= 2**32: seed -= 2**32
                _Sync_.rng = random.Random(seed)
            else:
                _Sync_.rng = random.Random()
                _Sync_.rng.setstate(old_state)

            # we rolled the dice to get the namespace and (possibly)
            # seeded the rng for the simulus module, but we don't want
            # to advance the default random sequence of the random
            # module; so we roll it back to the old state
            random.setstate(old_state)
        else:
            # if the global seed is provided, we first use it to
            # create a random sequence so that we can get a namespace
            # to be the same across diffferent ranks and across
            # different ranks; and then we generate a random sequence
            # for the ranks greater than zero
            _Sync_.rng = random.Random(_Sync_.args.seed)
            _Sync_.namespace = uuid.UUID(int=_Sync_.rng.getrandbits(128))
            if _Sync_.comm_rank > 0:
                seed = _Sync_.args.seed+_Sync_.comm_rank
                if seed >= 2**32: seed -= 2**32
                _Sync_.rng = random.Random(seed)

        # a map from names to simulator instances
        _Sync_.named_simulators = {}

        # a map from names to mailbox instances
        _Sync_.named_mailboxs = {}

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

    @staticmethod
    def unique_name():
        u = uuid.UUID(int=_Sync_.rng.getrandbits(128))
        return str(u)

def sync(sims, lookahead):
    raise NotImplementedError("simulus.sync() not implemented")
