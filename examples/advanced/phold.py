import simulus, random, sys
random.seed(12345)

# model parameters
node_count = 16 # total number of nodes
job_count = 100 # total number of jobs in system 
lookahead = 1 # min delay for jobs traveling between nodes

# each node repeatedly receives a job and then forward to the next
# node randomly chosen
def generate(sim, mbox, idx):
    while True:
        job = mbox.recv(isall=False) # one at a time
        print("%g: n%d recv j%d," % (sim.now, idx, job), end=' ')
        
        target = sim.rng().randrange(node_count)
        delay = sim.rng().expovariate(1)+lookahead
        grp.send(sim, 'mb%d'%target, job, delay)
        print("sent to n%d with d=%g (%g)" %
              (target, delay, sim.now+delay))

# create simulators and mailboxes
id = simulus.sync.comm_rank()   # process rank
p = simulus.sync.comm_size()    # total processes
print('id=%d, p=%d' % (id, p))

sims = [] # all simulators instantiated on this machine
for idx in range(id, node_count, p):
    sim = simulus.simulator(name='sim%d'%idx)
    sims.append(sim)
    mb = sim.mailbox(name='mb%d'%idx, min_delay=lookahead)
    sim.process(generate, sim, mb, idx)
simnames = [sim.name for sim in sims]

if len(sys.argv) == 2:
    syncase = int(sys.argv[1])
else:
    print("Usage: %s CASE_NUM" % sys.argv[0])
    print("CASE_NUM can be the following:")
    print("  1: sequential simulation")
    print("  2: parallel simulation on shared-memory multiprocessors")
    print("  3: parallel simulation using mpi")
    print("  4: parallel simulation with mpi and multiprocessing")
    sys.exit(-1)

print("syncase =", syncase)
if syncase == 1:
    # case 1: sequential simulation
    grp = simulus.sync(sims)
elif syncase == 2:
    # case 2: parallel simulation on shared-memory multiprocessors
    grp = simulus.sync(sims, enable_smp=True)
elif syncase == 3:
    # case 3: parallel simulation with mpi
    grp = simulus.sync(sims, enable_spmd=True)
elif syncase == 4:
    # case 4: parallel simulation with mpi and multiprocessing
    grp = simulus.sync(sims, enable_smp=True, enable_spmd=True)
else:
    print("ERROR: case number (%d) should be 1-4" % syncase)
    sys.exit(-2)

# create initial jobs
for idx in range(job_count):
    target = random.randrange(node_count)
    delay = random.expovariate(1)+lookahead
    if 'sim%d'%target in simnames:
        grp.send(sims[0], 'mb%d'%target, idx, delay)
        print("-init- sent j%d to n%d with d=%g" %
              (idx, target, delay))

if id > 0: grp.run()
else:
    grp.run(100)
    #grp.show_runtime_report()
