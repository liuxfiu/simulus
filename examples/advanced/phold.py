import simulus
import random
random.seed(12345)

job_count = 5
node_count = 4
lookahead = 1

def generate(sim, idx):
    while True:
        msg = mboxs[idx].recv(isall=False)
        print("%g: n%d recv j%d," % (sim.now, idx, msg), end=' ')
        
        target = sim.rng().randrange(node_count)
        delay = sim.rng().expovariate(1)+lookahead
        s.send(sim, 'mb%d'%target, msg, delay)
        print("sent n%d with d=%g (%g)" % (target, delay, sim.now+delay))

# create simulators and mailboxes
sims = []
mboxs = []
for idx in range(node_count):
    sim = simulus.simulator()
    sims.append(sim)
    
    mb = sim.mailbox(name='mb%d'%idx, min_delay=lookahead)
    mboxs.append(mb)
    
    sim.process(generate, sim, idx)

# create initial jobs
for idx in range(job_count):
    target = random.randrange(node_count)
    delay = random.expovariate(1)+lookahead
    mboxs[target].send(idx, delay)
    print("-init- sent j%d to n%d with d=%g" %
          (idx, target, delay))

s = simulus.sync(sims)
#s = simulus.sync(sims, enable_smp=True)
s.run(100)
