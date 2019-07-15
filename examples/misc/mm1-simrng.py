import numpy # assuming numpy has been installed
import random, simulus

# this determines the random module's default random sequence, 
# which also determines the simulation namespace
random.seed(123)

def job(idx):
    r.acquire()
    print("%g: job(%d) gains access" % (sim.now,idx))
    sim.sleep(rng.gamma(2, 2))
    print("%g: job(%d) releases" % (sim.now,idx))
    r.release()

def arrival():
    i = 0
    while True:
        i += 1
        sim.sleep(rng.pareto(0.95))
        print("%g: job(%d) arrives" % (sim.now,i))
        sim.process(job, i)

sim = simulus.simulator('unique_name')
rng = numpy.random.RandomState(sim.rng().randrange(2**32))
r = sim.resource()
sim.process(arrival)
sim.run(10)
