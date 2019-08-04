import simulus, random
from concurrent.futures import ProcessPoolExecutor

random.seed(13579)

T = 25000
N = 1

def efunc(sim):
    print('%g: efunc()' % sim.now)
    sim.sched(efunc, sim, offset=random.expovariate(1))

def pfunc(sim):
    while True:
        print('%g: pfunc()' % sim.now)
        sim.sleep(offset=random.expovariate(1))

def gfunc(sim):
    print('%g: gfunc()' % sim.now)
    sim.process(gfunc, sim, offset=random.expovariate(1))
    
def esim():
    sim = simulus.simulator()
    for _ in range(N):
        sim.sched(efunc, sim, offset=random.expovariate(1))
    return sim

def psim():
    sim = simulus.simulator()
    for _ in range(N):
        sim.process(pfunc, sim, offset=random.expovariate(1))
    return sim

def gsim():
    sim = simulus.simulator()
    for _ in range(N):
        sim.process(gfunc, sim, offset=random.expovariate(1))
    return sim

s = simulus.sync([esim(), psim(), gsim()])
s.run(T/N)
