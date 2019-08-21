import simulus, random, argparse, textwrap
random.seed(12345)

# the following are utility functions to determine the starting and
# ending index of an array that belongs to process id, if the array
# (which has n numbers) is to be divided among p processes, assuming
# the block demposition method is used to assign data to processes,
# where consecutive elements are preferrably assigned to the same
# processes (ref. Michael J. Quinn, "Parallel Programming in C with
# MPI and OpenMP", McGraw-Hill, 2003)
def BLOCK_LOW(id,p,n): return int(id*n/p)
def BLOCK_HIGH(id,p,n): return BLOCK_LOW(id+1,p,n)-1
def BLOCK_SIZE(id,p,n): return BLOCK_LOW(id+1)-BLOCK_LOW(id)
def BLOCK_OWNER(index,p,n): return int((p*(index+1)-1)/n)

class node(object):
    """Each node runs in a simulator (sim), has an index number (node_idx)
    that ranges from zero to the total number of nodes (total_nodes)
    minus one, and a lookahead. It creates a mailbox (mbox) with a
    unique name (using the index number) and with a min delay using
    the given lookahead.  During simulation, each node repeatedly
    receives jobs (from this and other nodes) and then forward them to
    other nodes randomly chosen among all the nodes."""

    def __init__(self, sim, idx, total, lookahead):
        self.sim = sim
        self.node_idx = idx
        self.total_nodes = total
        self.lookahead = lookahead
        self.mbox = sim.mailbox(name='mb%d'%idx, min_delay=lookahead)
        sim.process(self.forward_jobs)

    def forward_jobs(self):
        while True:
            job = self.mbox.recv(isall=False) # one at a time
            target = self.sim.rng().randrange(self.total_nodes)
            delay = self.sim.rng().expovariate(1)+self.lookahead
            self.sim.sync().send(self.sim, 'mb%d'%target, job, delay)
            print("%g: n%d recv j%d, sent to n%d with d=%g (%g)" %
                  (self.sim.now, self.node_idx, job, target, delay, self.sim.now+delay))

# get the total number of processes used to run the simulation (psize)
# as well as the rank of this process (rank), assuming that we are
# using MPI to run this code; if not, rank will be zero and psize will
# be one
rank = simulus.sync.comm_rank()   # process rank
psize = simulus.sync.comm_size()  # total processes

# parsing the command line; the optional arguments used by simulus
# have already been filtered out by simulus when simulus is imported
parser = argparse.ArgumentParser(
    parents=[simulus.parser], # allow -h or --help to show simulus arguments
    description='The PHOLD model.',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=textwrap.dedent('''\
        CHOICE (-c or --choice) can be any of the following:
          1: sequential simulation (default)
          2: parallel simulation on shared-memory multiprocessors
          3: parallel simulation using mpi
          4: parallel simulation with mpi and multiprocessing
    '''))
parser.add_argument('total_nodes', metavar='NNODES', type=int,
                    help='total number of nodes')
parser.add_argument('init_jobs', metavar='NJOBS', type=int,
                    help='total number of initial jobs')
parser.add_argument('endtime', metavar='ENDTIME', type=float,
                    help='simulation end time')
parser.add_argument("-m", "--nsims", type=int, metavar='NSIMS', default=None,
                    help="total number of simulators")
parser.add_argument("-c", "--choice", type=int, metavar='CHOICE', default=1,
                    help="choose simulation method (see below)")
parser.add_argument("-l", "--lookahead", type=float, metavar='LOOKAHEAD', default=1.0,
                    help="min delay of mailboxes")
args = parser.parse_args()
if args.nsims is None:
    args.nsims = args.total_nodes
elif args.nsims < psize or args.nsims > args.total_nodes:
    raise ValueError('nsims must be an integer between PSIZE (%d) and NNODES (%d)' %
                     (psize, args.total_nodes))

if rank == 0:
    print('> MODEL PARAMETERS:')
    print('>> TOTAL NODES:', args.total_nodes)
    print('>> TOTAL INIT JOBS:', args.init_jobs)
    print('>> LOOKAHEAD:', args.lookahead)
    print('>> CHOICE:', args.choice)
    print('>> TOTAL SIMS: ', args.nsims)
    print('>> TOTAL SPMD PROCESSES:', psize)

# create simulators and nodes
sims = [] # all simulators instantiated on this machine
for s in range(BLOCK_LOW(rank, psize, args.nsims), BLOCK_LOW(rank+1, psize, args.nsims)):
    sim = simulus.simulator(name='sim%d'%s)
    sims.append(sim)
    #print('[%d] creating simulator %s...' % (rank, sim.name))

    for idx in range(BLOCK_LOW(s, args.nsims, args.total_nodes),
                     BLOCK_LOW(s+1, args.nsims, args.total_nodes)):
        #print('[%d]  creating node %d...' % (rank, idx))
        node(sim, idx, args.total_nodes, args.lookahead)

if args.choice == 1:
    # case 1: sequential simulation
    if psize > 1:
        raise RuntimeError("You are running MPI; consider CHOICE 3 or 4.")
    syn = simulus.sync(sims)
elif args.choice == 2:
    # case 2: parallel simulation on shared-memory multiprocessors
    if psize > 1:
        raise RuntimeError("You are running MPI; consider CHOICE 3 or 4.")
    syn = simulus.sync(sims, enable_smp=True)
elif args.choice == 3:
    # case 3: parallel simulation with mpi
    syn = simulus.sync(sims, enable_spmd=True)
elif args.choice == 4:
    # case 4: parallel simulation with mpi and multiprocessing
    syn = simulus.sync(sims, enable_smp=True, enable_spmd=True)
else:
    raise ValueError("CHOICE (%d) should be 1-4" % choice)

if rank > 0:
    # only run() without parameters is allowed for higher ranks
    syn.run()
else:
    # create initial jobs (on rank 0)
    for idx in range(args.init_jobs):
        target = random.randrange(args.total_nodes)
        delay = random.expovariate(1)+args.lookahead
        syn.send(sims[0], 'mb%d'%target, idx, delay)
        print("-init- sent j%d to n%d with d=%g" %
              (idx, target, delay))

    # run simulation and get runtime performance report
    syn.run(args.endtime)
    syn.show_runtime_report(prefix='>')
