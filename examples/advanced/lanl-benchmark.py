"""LANL PDES Benchmark is a model for benchmarking parallel discrete
event simulation performance; the model considers different
communication patterns and workloads, memory operations, and
computational workloads.

The model is described in the paper: "Parameterized benchmarking of
parallel discrete event simulation systems: communication,
computation, and memory", by Eunjung Park, Stephan Eidenbenz,
Nandakishore Santhi, Guillaume Chapuis, and Bradley Settlemyer,
appeared in the Proceedings of the 2015 Winter Simulation Conference.

The model has been slightly modified for parameterization. The code
has been modified from the simian code maintained by Stephan Eidenbenz
<eidenben@lanl.gov>, and rewritten for simulus.

"""

import sys, math, random, argparse, simulus

# logging information (for debugging)
import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# set the default global random seed (one may change it using -s or
# --seed command-line option)
random.seed(12345) 

"""Command-line arguments are configurable model parameters:

General Parameters
==================

n_ent: number of nodes (or entities); each node is a simulus simulator
        by itself

lookahead (optional): the min delay for events sent between the nodes;
        default is 1.0

end_time: duration of simulation; setting end_time to (n_ent * s_ent *
	lookahead) will result in, on average, one simulation event
	per synchronization window when running in parallel mode

time_bins (optional): the number of equal-size time bins in which the
        number of send events is collected for reporting; default is 1

Communication Parameters
========================

s_ent: average number of send events per node

p_recv (optional): parameter for geometric distribution of receive
        nodes; node i receives a fraction of p_recv*(1-p_recv)**i of
        all events: if p_recv = 0, it's uniform distribution; if
        p_recv = 1, only node 0 receives events; default is 0

i_recv (optional): receive distribution is inverted; default is False

p_send (optional): parameter for geometric distribution of send nodes;
        node i sends a fraction of p_send*(1-p_send)**i of all events:
        if p_send = 0, it's uniform distribution; if p_send = 1, only
        node 0 sends events; default is 0

i_send (optional): send distribution is inverted; default is False

q_frac (optional): fraction of events in the event queue; default is 0

Memory Parameters
=================

m_ent: average memory footprint per node, as the number of elements in
        a list (8 byte per element)

p_list (optional): parameter for geometric distribution of linear list
        sizes; node i has a fraction of p_list*(1-p_list)**i of all
        list elements: if p_list = 0, it's uniform distribution; if
        p_list = 1, node 0 has all the list elements; default is 0

i_list (optional): list element distribution is inverted; default is
        False

Computation Parameters
======================

ops_ent (optional): average operations per handler per node; the
        computation is implemented by calculating a weighted sum of
        the first k list elements with randomly drawn weights (so that
        the calculation cannot be optimized away); default is 0

ops_sigma (optional): standard deviation in the numer of operations
        per handler per node, as a fraction of the average operations;
        default is 0

cache_friendliness (optional): the fraction of list elements accessed
        during operations; default is 1.0

"""

# parsing command line arguments
parser = argparse.ArgumentParser(
    parents=[simulus.parser], # allow -h or --help to show simulus arguments
    description='LaPDES (LANL PDES) benchmark model.')

# general parameters
parser.add_argument('n_ent', metavar='N_ENT', type=int, help='number of nodes')
parser.add_argument('-la', '--lookahead', type=float, metavar='LOOKAHEAD', default=1.0, help='min delay')
parser.add_argument('end_time', metavar='END_TIME', type=float, help='duration of simulation')
parser.add_argument('-tb', '--time_bins', metavar='TIME_BINS', type=int, default=1, help='the number of equal-size time bins for reporting')

# communication parameters
parser.add_argument('s_ent', metavar='S_ENT', type=int, help='avg number of send events per node')
parser.add_argument('-pr', '--p_recv', metavar='P_RECV', type=float, default=0, help='parameter for geometric distribution of receive nodes')
parser.add_argument('-ir', '--i_recv', action="store_true", default=False, help='receive distribution is inverted')
parser.add_argument('-ps', '--p_send', metavar='P_SEND', type=float, default=0, help='parameter for geometric distribution of send nodes')
parser.add_argument('-is', '--i_send', action="store_true", default=False, help='send distribution is inverted')
parser.add_argument('-qf', '--q_frac', metavar='Q_FRAC', type=float, default=0, help='fraction of events in the event queue')

# memory parameters
parser.add_argument('m_ent', metavar='M_ENT', type=int, help='avg list size per node') 
parser.add_argument('-pl', '--p_list', metavar='P_LIST', type=float, default=0, help='parameter for geometric distribution of list sizes')
parser.add_argument('-il', '--i_list', action="store_true", default=False, help='list distribution is inverted')

# computation parameters
parser.add_argument('-op', '--ops_ent', metavar='OPS_ENT', type=float, default=0, help='avg operations per handler per node')
parser.add_argument('-os', '--ops_sigma', metavar='OPS_SIGMA', type=float, default=0, help='standard deviation in fraction of operations per handler per node')
parser.add_argument('-cf', '--c_friend', metavar='C_FRIEND', type=float, default=1, help='fraction of list elements accessed during operations')

args = parser.parse_args()

if args.n_ent < 1: raise ValueError('n_ent(%d) must be positive' % args.n_ent)
else: print('number of nodes (n_ent): %d' % args.n_ent)
if args.lookahead <= 0: raise ValueError('lookahead(%g) must be positive' % args.lookahead)
else: print('min delay (lookahead): %g' % args.lookahead)
if args.end_time <= 0: raise ValueError('end_time(%g) must be positive' % args.end_time)
else: print('duration of simulation (end_time): %g' % args.end_time)
if args.time_bins < 1: raise ValueError('time_bins(%d) must be positive' % args.time_bins)
else: print('number of bins for reporting (time_bins): %d' % args.time_bins)

if args.s_ent < 1: raise ValueError('s_ent(%d) must be positive' % args.s_ent)
else:
    print('avg number of send events per node (s_ent): %d' % args.s_ent)
    total_sends = args.n_ent*args.s_ent
    print('(total number of send events: %d)' % total_sends)
if args.p_recv < 0 or args.p_recv > 1: raise ValueError('p_recv(%g) must be in range [0, 1]' % self.p_recv)
else: print('parameter for geometric distribution of receive nodes (p_recv): %g' % args.p_recv)
print('receive distribution is inverted (i_recv): %r' % args.i_recv)
if args.p_send < 0 or args.p_send > 1: raise ValueError('p_send(%g) must be in range [0, 1]' % self.p_send)
else: print('parameter for geometric distribution of send nodes (p_send): %g' % args.p_send)
print('send distribution is inverted (i_send): %r' % args.i_send)
if args.q_frac < 0 or args.q_frac > 1: raise ValueError('q_frac(%g) must be in range [0, 1]' % self.q_frac)
else: print('fraction of events in event queue (q_frac): %g' % args.q_frac)

if args.m_ent < 0: raise ValueError('m_ent(%d) must be non-negative' % args.m_ent)
else:
    print('avg list size per node (m_ent): %d' % args.m_ent)
    total_mems = args.n_ent*args.m_ent
    print('(total memory footprint: %d)' % total_mems)
if args.p_list < 0 or args.p_list > 1: raise ValueError('p_list(%g) must be in range [0, 1]' % self.p_list)
else: print('parameter for geometric distribution of list sizes (p_list): %g' % args.p_list)
print('list distribution is inverted (i_list): %r' % args.i_list)

if args.ops_ent < 0: raise ValueError('ops_ent(%d) must be non-negative' % args.ops_ent)
else:
    print('avg operations per handler per node (ops_ent): %g' % args.ops_ent)
    total_ops = args.n_ent*args.ops_ent
    print('(avg operations per handler: %d)' % total_ops)
if args.ops_sigma < 0 or args.ops_sigma > 1: raise ValueError('ops_sigma(%g) must be in range [0, 1]' % self.ops_sigma)
print('standard deviation in fraction of operations per handler per node (ops_sigma): %g' % args.ops_sigma)
if args.c_friend < 0 or args.c_friend > 1: raise ValueError('c_friend(%g) must be in range [0, 1]' % self.c_friend)
else: print('fraction of list elements accessed during operations (c_friend): %g' % args.c_friend)

class node(object):
    def __init__(self, sim, idx):
        self.sim = sim
        self.idx = idx
        self.mbox = sim.mailbox(name='mb%d'%idx, min_delay=args.lookahead)
        self.mbox.add_callback(self.recv_handler)
        if idx == 0:
            self.stat_mbox = sim.mailbox(name='statmb', min_delay=args.lookahead)
            self.stat_mbox.add_callback(self.output_handler)
        
        # 1. compute number of events that the node will send and then
        # calculate the (mean) inter-send time
        if args.p_send == 0:
            prob = 1.0/float(args.n_ent)
        else:
            if args.i_send:
                prob =  args.p_send*(1-args.p_send)**(args.n_ent-1-idx)
            else:
                prob =  args.p_send*(1-args.p_send)**idx
            prob = prob/(1-(1-args.p_send)**args.n_ent) # normalize
        mysends = int(prob*total_sends)
        if mysends > 0:
            self.inter_send_time = args.end_time/mysends 
        else:
            self.inter_send_time = simulus.infinite_time

        # 2. allocate appropriate memory space through list size, and number of ops
        if args.p_list == 0:
            prob =  1.0/float(args.n_ent)
        else:
            if args.i_list:
                prob =  args.p_list*(1-args.p_list)**(args.n_ent-1-idx)
            else:
                prob =  args.p_list*(1-args.p_list)**idx
            prob = prob/(1-(1-args.p_list)**args.n_ent) # normalize
        self.list_size = int(prob*total_mems)
        self.list = [sim.rng().random() for _ in range(self.list_size)]
        self.active_elements = int(args.c_friend*self.list_size)
        self.ops = int(prob*total_ops)
        log.info('node %d: sends=%d, inter-send=%g, list=%d, active=%d, ops=%d' %
                 (idx, mysends, self.inter_send_time, self.list_size, self.active_elements, self.ops))

        # 3. initialize the events (q_frac of them)
        tosched = int(args.q_frac*mysends)+1
        self.last_sched = sim.now
        for i in range(tosched):
            t = sim.rng().expovariate(1.0/self.inter_send_time)
            self.last_sched += t
            if self.last_sched < args.end_time:
                sim.sched(self.send_handler, until=self.last_sched)
            else: break

        # 4. set up statistics
        self.send_count, self.recv_count =  0, 0
        self.ops_max, self.ops_min, self.ops_mean = 0.0, float("inf"), 0.0
        self.time_sends = [0]*args.time_bins
        if idx == 0:
            self.stats_received  = 0
            self.g_send_count, self.g_recv_count = 0, 0
            self.g_ops_max, self.g_ops_min, self.g_ops_mean = 0.0, float("inf"), 0.0
            self.g_time_sends = [0]*args.time_bins
                
        # 5. schedule data collection at end of time
        sim.sched(self.finish_handler, until=args.end_time)

    def send_handler(self):
        self.send_count += 1
        self.time_sends[int(self.sim.now/args.end_time*args.time_bins)] += 1

        t = self.sim.rng().expovariate(1.0/self.inter_send_time)
        self.last_sched += t
        if self.last_sched < args.end_time: 
            self.sim.sched(self.send_handler, until=self.last_sched)
        
        if self.sim.now+args.lookahead <= args.end_time:
            if args.p_recv == 1: d = 0
            elif args.p_recv == 0: d = self.sim.rng().randrange(args.n_ent)
            else:
                u = self.sim.rng().uniform((1-args.p_recv)**args.n_ent, 1.0)
                d = int(math.ceil(math.log(u)/math.log(1.0-args.p_recv)))-1
            if args.i_recv: d = args.n_ent-1-d
            self.sim.sync().send(self.sim, 'mb%d'%d, 0)

    def recv_handler(self):
        self.mbox.retrieve(isall=False)
        self.recv_count += 1
        
        if args.ops_sigma > 0:
            r_ops = max(0, int(self.sim.rng().gauss(self.ops, self.ops*args.ops_sigma)))
        else:
            r_ops = float(self.ops)
        self.ops_max = max(self.ops_max, r_ops)
        self.ops_min = min(self.ops_min, r_ops)
        self.ops_mean = (self.ops_mean*(self.recv_count-1)+r_ops)/self.recv_count

        if self.ops > 0:
            r_active_elements = int(self.active_elements*r_ops/self.ops)
        else:
            r_active_elements = self.active_elements
        r_active_elements = min(r_active_elements, self.list_size)
        r_active_elements = max(0, r_active_elements)
        if r_active_elements > 0:
            r_ops_per_element = int(r_ops/r_active_elements)
        else:
            r_ops_per_element = 0
            
        # do the work!!
        value = 0.0
        for i in range(r_active_elements):
            for j in range(r_ops_per_element):
                value += self.list[i]*self.sim.rng().random()
            self.list[i] += value
        
    def finish_handler(self):
        # send stats to node 0 for outputting of global stats
        msg = [self.idx, self.send_count, self.recv_count, \
               self.ops_min, self.ops_mean, self.ops_max, self.time_sends]
        #print("%g: %d sched output d=%g" % (self.sim.now, self.idx, float(self.idx*1e-12+args.lookahead)))
        self.sim.sync().send(self.sim, 'statmb', msg, args.lookahead+self.idx*1e-12)

    def output_handler(self):
        msg = self.stat_mbox.retrieve(isall=False)

        if self.stats_received == 0:
            # Only write header line a single time
            header = "{0:>8}{1:>10}{2:>10}     {3:<14}{4:<10}{5:<11}    {6}\n".format(
                "idx", "sends", "recvs", "ops(min", "avg", "max)", "timebin sends")
            sys.stdout.write(header)
        s = ("["+', '.join(['%d']*len(msg[6]))+"]") % tuple(msg[6])
        str_out = "{0:>8}{1:>10,}{2:>10,}         {3:<10,}{4:<10,.1f}{5:<10,}     {6}\n".format(
            msg[0], msg[1], msg[2], msg[3], msg[4], msg[5], s)
        sys.stdout.write(str_out)

        self.stats_received += 1
        self.g_ops_mean = (msg[2]*msg[4]+self.g_ops_mean*self.g_recv_count)/(self.g_recv_count+msg[2])
        self.g_send_count += msg[1]
        self.g_recv_count += msg[2]
        self.g_ops_min = min(self.g_ops_min, msg[3])
        self.g_ops_max = max(self.g_ops_max, msg[5])
        for i in range(args.time_bins):
            self.g_time_sends[i] += msg[6][i]
                
        if self.stats_received == args.n_ent:
            sys.stdout.write("===================== LANL PDES BENCHMARK Collected Stats from All Ranks =======================\n")
            header = "{0:>8}{1:>10}{2:>10}     {3:<14}{4:<10}{5:<11}    {6}\n".format(
                "idx", "sends", "recvs", "ops(min", "avg", "max)", "timebin sends")
            sys.stdout.write(header)
            s = ("["+', '.join(['%d']*len(self.g_time_sends))+"]") % tuple(self.g_time_sends)
            str_out = "{0:>8}{1:>10,}{2:>10,}         {3:<10,}{4:<10,.1f}{5:<10,}     {6}\n".format(
                args.n_ent, self.g_send_count, self.g_recv_count, self.g_ops_min,
                self.g_ops_mean, self.g_ops_max, s)
            sys.stdout.write(str_out)
            sys.stdout.write("=================================================================================================\n")
        
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

# get the total number of processes used to run the simulation (psize)
# as well as the rank of this process (rank), assuming that we are
# using MPI; if not, rank will be zero and psize will be one
rank = simulus.sync.comm_rank()   # process rank
psize = simulus.sync.comm_size()  # total processes

# create simulators and nodes
sims = [] # all simulators instantiated on this machine
for s in range(BLOCK_LOW(rank, psize, args.n_ent), BLOCK_LOW(rank+1, psize, args.n_ent)):
    sim = simulus.simulator(name='sim%d'%s)
    sims.append(sim)
    node(sim, s)

# create the synchronized group and run the simulation
syn = simulus.sync(sims, enable_smp=True, enable_spmd=True)
#syn = simulus.sync(sims)
if rank > 0: syn.run()
else:
    syn.run(args.end_time)
    syn.show_runtime_report(prefix='>')
    syn.run(args.lookahead+0.1) # just run a little longer for gathering stats
