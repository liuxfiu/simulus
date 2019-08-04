import random, simulus

T = 250000
N = 100

def func():
    #sim.sched(func, offset=random.expovariate(1))
    sim.process(func, offset=random.expovariate(1))
    #while True:
    #    sim.sleep(offset=random.expovariate(1))
    
random.seed(13579)
sim = simulus.simulator()
for _ in range(N):
    #sim.sched(func, offset=random.expovariate(1))
    sim.process(func, offset=random.expovariate(1))

sim.run(T/N)
sim.show_runtime_report()
