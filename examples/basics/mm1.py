import simulus

from random import seed, expovariate
seed(123)

def job(idx):
    r.acquire()
    print("%g: job(%d) gains access " % (sim.now,idx))
    sim.sleep(expovariate(1))
    print("%g: job(%d) releases" % (sim.now,idx))
    r.release()
    
def arrival():
    i = 0
    while True:
        i += 1
        sim.sleep(expovariate(0.95))
        print("%g: job(%d) arrives" % (sim.now,i))
        sim.process(job, i)

sim = simulus.simulator()
r = sim.resource()
sim.process(arrival)
sim.run(10)
