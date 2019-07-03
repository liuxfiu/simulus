import simulus

from random import seed, expovariate
seed(123)

def job(sim, params):
    rsc.reserve()
    sim.sleep(expovariate(1))
    rsc.release()
    
def arrival_process(sim, params):
    while True:
        sim.sleep(expovariate(1.8))
        sim.process(job)
        
sim = simulus.simulator()
qs = simulus.Resource.default_qstats()
rsc = sim.resource(capacity=2, qstats=qs)
sim.process(arrival_process)
sim.run(1000)

qs.final(sim.now)
qs.report()
