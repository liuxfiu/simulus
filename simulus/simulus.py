# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 3, 2019
# Last Update: Time-stamp: <2019-08-10 07:03:19 liux>
###############################################################

import array, copy, random, uuid

__all__ = ["_Simulus"]

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class _Simulus(object):
    instance = None       
    def __new__(cls):
        if not _Simulus.instance:
            _Simulus.instance = _Simulus.__OneInstance()
        return _Simulus.instance
    def __getattr__(self, name):
        return getattr(self.instance, name)
    def __setattr__(self, name):
        return setattr(self.instance, name)
    
    class __OneInstance:
        """The first simulator creates one and only one instance of this class
        for the entire simulation run. That is, this class is expected
        to be a singleton. Note that there's one and one instance for
        each rank in a distributed simulation scenario."""

        def __init__(self):
            """Initialization is called by the first created simulator when the
            singleton is created. We use this opportunity to
            initialize everything."""

            # turn logging info on if we are in verbose mode
            from simulus import args
            self.args = args
            if args.debug:
                logging.basicConfig(level=logging.DEBUG)
            elif args.verbose:
                logging.basicConfig(level=logging.INFO)

            # initialize mpi if needed
            if args.mpi:
                global MPI
                from mpi4py import MPI
                self.comm_rank = MPI.COMM_WORLD.Get_rank()
                self.comm_size = MPI.COMM_WORLD.Get_size()
                log.info("running in SPMD mode with mpi: comm_size=%d, comm_rank=%d" %
                         (self.comm_size, self.comm_rank))
            else:
                self.comm_rank = 0
                self.comm_size = 1
                log.info("running in non-SPMD mode")

            # set the namespace and the random sequence
            if args.seed is not None and \
               (args.seed < 0 or args.seed >= 2**32):
                errmsg = "command-line argument --seed or -s must be a 32-bit integer"
                log.error(errmsg)
                raise ValueError(errmsg)
            if args.seed is None:
                old_state = random.getstate()

                # if the global seed is not provided, we use the
                # random module's default random sequence, assuming
                # it's been seeded with the same seed (across
                # different runs and across different ranks)
                random.getrandbits(160) # shift global random to avoid collision
                self.namespace = uuid.UUID(int=random.getrandbits(128))
                log.info("[r%d] creating namespace '%s'" % (self.comm_rank, self.namespace))

                # now we get a random sequence for each rank: rank 0
                # inherits the random module's default random
                # sequence; other ranks each create one separate
                # random sequence seeded from the default random
                # sequence and the rank itself
                if self.comm_rank > 0:
                    seed = random.randrange(2**32)
                    seed += self.comm_rank
                    if seed >= 2**32: seed -= 2**32
                    self.rng = random.Random(seed)
                else:
                    self.rng = random.Random()
                    self.rng.setstate(old_state)

                # we rolled the dice to get the namespace and
                # (possibly) seeded the rng for the simulus module,
                # but we don't want to advance the default random
                # sequence of the random module; so we roll it back to
                # the old state
                random.setstate(old_state)
            else:
                # if the global seed is provided, we first use it to
                # create a random sequence so that we can get a
                # namespace to be the same across diffferent ranks and
                # across different ranks; and then we generate a
                # random sequence for the ranks greater than zero
                self.rng = random.Random(args.seed)
                self.rng.getrandbits(160) # we do the same to mirror the above case
                self.namespace = uuid.UUID(int=self.rng.getrandbits(128))
                if self.comm_rank > 0:
                    seed = args.seed+self.comm_rank
                    if seed >= 2**32: seed -= 2**32
                    self.rng = random.Random(seed)

            # a map from names to simulator instances
            self.named_simulators = {}

        def register_simulator(self, name, sim):
            """Register the simulation with the given name. This may replace an
            earlier simulator of the same name."""
            self.named_simulators[name] = sim
    
        def get_simulator(self, name):
            """Return the simulator with the given name, or None if no such
            simulator can be found."""
            return self.named_simulators[name]

        def unique_name(self):
            """Return a unique name created from the random sequence."""
            u = uuid.UUID(int=self.rng.getrandbits(128))
            return str(u)

        def allgather(self, adict):
            """MPI allgather: every rank presents a dictionary 'adict' (it's a
            map from str to int); in the end, every rank gets a union of all 
            dictionaries. Duplicate keys are treated as an error."""
            
            if self.comm_size > 1:
                ret = MPI.COMM_WORLD.allgather(adict)
                adict = ret[0]
                for other_adict in ret[1:]:
                    for k in other_adict.keys():
                        if k in adict:
                            erromsg = "found duplicate key='%s' as %r and %r" % \
                                      (k, adict[k], other_adict(k))
                            log.error(errmsg)
                            raise RuntimeError(errmsg)
                        adict[k] = other_adict[k]
            return adict
       
        def gather(self, obj):
            """MPI gather: every rank presents an object; in the end, rank 0 gets
            a list of all the objects."""
            
            if self.comm_size > 1:
                return MPI.COMM_WORLD.gather(obj)
            else:
                return [obj]

        def bcast(self, obj):
            """MPI broadcast: rank 0 presents an object and in the end all ranks
            receives and returns the object."""
            
            if self.comm_size > 1:
                return MPI.COMM_WORLD.bcast(obj, root=0)
            else:
                return obj

        def allreduce(self, val, op=min):
            """MPI allreduce: every rank presents a value; in the end, every rank
            gets a reduced value, min by default."""
            if self.comm_size > 1:
                val = MPI.COMM_WORLD.allreduce(val, op)
            return val

        def alltoall(self, adict):
            """MPI alltoall: every rank presents a dictionary 'adict' (it's a map
            from rank to a list of picklable objects); in the end, every rank 
            gets a list of all objects destined to the rank."""
            
            if self.comm_size > 1:
                ret = MPI.COMM_WORLD.alltoall([adict.get(i, None) for i in range(self.comm_size)])
                return [itm for s in ret if s is not None for itm in s] # flattens list of lists (or None)
            else:
                return adict.get(0, None)
