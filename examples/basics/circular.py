import simulus

from random import seed, expovariate
seed(12345)

def p(sim, params):
    idx = params['idx']
    while True:
        sems[idx].wait()
        print("p%d wakes up at %g" % (idx, sim.now))
        sim.sleep(expovariate(1))
        sems[(idx+1)%total_procs].signal()
        
sim = simulus.simulator()

total_procs = 10
sems = [sim.semaphore() for _ in range(total_procs)]
for i in range(10):
    sim.process(p, idx=i)
sems[0].signal()
sim.run(20)
