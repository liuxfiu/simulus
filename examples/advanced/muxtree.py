"""Muxtree is a model that builds a simple network of nodes. 

The topology of this model is a tree: the leaves of the tree are
traffic sources and the interior nodes (including the root) of the
tree are multiplexers. Messages are generated from the source node and
travel through a series of multiplexers until it reaches the root of
the tree.  Each multiplexer contains a FIFO queue with a finite-sized
buffer; and each message, upon arriving at the multiplexer, is given a
constant service time. Messages can be dropped if buffer overflow
occurs.

The original muxtree model was developed as an example for the
Dartmouth Scalable Simulation Framework (SSF) written in C++. The
model is ported here for simulus.

"""

import random, simulus
from collections import deque

# global random seed
random.seed(13579)

# model parameters
MUXTREE_LEVELS = 3  # number of levels of multiplexers
MUXTREE_FANIN = 2 # fan-in at each multiplexer
TRANSMISSION_DELAY = 1 # in seconds

SRC_IAT = 1 # inter-arrival time (in seconds)
MUX_BUFSIZ = 6 # size of the FIFO queue
MUX_MST = 1 # mean service time (in seconds)
END_TIME = 100 # duration of simulation

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

class src_node:
    def __init__(self, sim, idx):
        self.sim = sim # owner simulator
        self.idx = idx # source node index
        self.nxt = 'mb_0_%d'%int(idx/MUXTREE_FANIN) # next node's mailbox name
        self.nsent = 0 # total number of messages sent
        self.sim.process(self.on_arrival)
        #print('rank=%d: create src_node(idx=%d): nxt=%r' % (rank, self.idx, self.nxt))
        sim.sched(self.finish_handler, until=END_TIME)

    def on_arrival(self):
        while True:
            self.sim.sleep(self.sim.rng().expovariate(1/SRC_IAT))
            self.sim.sync().send(self.sim, self.nxt, self.idx)
            self.nsent += 1

    def finish_handler(self):
        self.sim.sync().send(self.sim, 'statmb', [self.nsent, 0, 0])

class mux_node:
    def __init__(self, sim, lvl, idx):
        self.sim = sim # owner simulator
        self.lvl = lvl # tree level of this mux node
        self.idx = idx # mux node index within the tree level
        if lvl < MUXTREE_LEVELS-1:
            self.nxt = 'mb_%d_%d' % (lvl+1, int(idx/MUXTREE_FANIN)) # next node's mailbox name
        else:
            self.nxt = None
        self.nrcvd = 0 # total number of message received
        self.nsent = 0 # total number of message sent
        self.nlost = 0 # total number of message lost
        self.mbox = self.sim.mailbox(name='mb_%d_%d'%(lvl,idx), min_delay=TRANSMISSION_DELAY)
        self.queue = self.sim.store()
        self.sim.process(self.arrive)
        self.sim.process(self.serve)
        #print('rank=%d: create mux_node(lvl=%d,idx=%d): mbox=%r, nxt=%r' %
        #      (rank, self.lvl, self.idx, self.mbox.name, self.nxt))
        sim.sched(self.finish_handler, until=END_TIME)
        if lvl == MUXTREE_LEVELS-1 and idx == 0:
            self.stats_received = 0
            self.stat_mbox = self.sim.mailbox(name='statmb', min_delay=TRANSMISSION_DELAY)
            self.stat_mbox.add_callback(self.output_handler)

    def arrive(self):
        while True:
            msg = self.mbox.recv(isall=False)
            #print('arrive:', msg)
            self.nrcvd += 1
            if self.queue.level < MUX_BUFSIZ:
                self.queue.put(obj=msg)
            else:
                self.nlost += 1

    def serve(self):
        while True:
            msg = self.queue.get()
            #print('get:', msg)
            self.sim.sleep(MUX_MST)
            if self.nxt:
                self.sim.sync().send(self.sim, self.nxt, msg)
                self.nsent += 1

    def finish_handler(self):
        self.sim.sync().send(self.sim, 'statmb', [self.nsent, self.nrcvd, self.nlost])

    def output_handler(self):
        s, r, l = self.stat_mbox.retrieve(isall=False)
        if self.stats_received == 0:
            self.g_nsent = s
            self.g_nrcvd = r
            self.g_nlost = l
        else:
            self.g_nsent += s
            self.g_nrcvd += r
            self.g_nlost += l
        self.stats_received += 1
        if self.stats_received == nnodes:
            print("(%d nodes) nsent=%ld, nrcvd=%ld, nlost=%ld" % 
                  (nnodes, self.g_nsent, self.g_nrcvd, self.g_nlost))


rank = simulus.sync.comm_rank()   # process rank
psize = simulus.sync.comm_size()  # total processes

sims = []
nnodes = 1 # number of nodes within the current level
for lvl in range(MUXTREE_LEVELS-1, -1, -1): # go from the root level
    #print('rank=%d, lvl=%d' % (rank, lvl))
    for idx in range(BLOCK_LOW(rank, psize, nnodes), BLOCK_LOW(rank+1, psize, nnodes)):
        sim = simulus.simulator(name='sim_%d_%d'%(lvl,idx))
        sims.append(sim)
        mux_node(sim, lvl, idx)
    nnodes *= MUXTREE_FANIN
for idx in range(BLOCK_LOW(rank, psize, nnodes), BLOCK_LOW(rank+1, psize, nnodes)):
    sim = simulus.simulator(name='sim_s_%d'%idx)
    sims.append(sim)
    src_node(sim, idx)

# now nnodes is the total number of nodes (for all ranks)
nnodes = (1-nnodes*MUXTREE_FANIN)/(1-MUXTREE_FANIN)

if psize > 1:
    syn = simulus.sync(sims, enable_spmd=True)
else:
    syn = simulus.sync(sims)
if rank > 0:
    syn.run()
else:
    syn.run(END_TIME+TRANSMISSION_DELAY+1e-9, show_runtime_report=True)
