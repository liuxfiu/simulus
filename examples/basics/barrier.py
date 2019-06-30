import simulus

from random import seed, expovariate
seed(12345)

class Barrier(object):
    def __init__(self, sim, total_procs):
        self.sim = sim
        self.total_procs = total_procs
        # reset the barrier (by creating a new trap and 
        # resetting the count)
        self.trap = self.sim.trap()
        self.num = 0
        
    def barrier(self):
        self.num += 1
        if self.num < self.total_procs:
            # not yet all processes have reached the barrier
            self.trap.wait()
        else:
            # the last process has reached the barrier
            self.trap.trigger()
            # reset the barrier for next time use (by 
            # creating a new trap and resetting the count)
            self.trap = self.sim.trap()
            self.num = 0

def p(sim, params):
    idx = params['idx']
    while True:
        t = expovariate(1)
        print("p%d runs at %g and sleeps for %g" % (idx, sim.now, t))
        sim.sleep(t)
        print("p%d reaches barrier at %g" % (idx, sim.now))
        bar.barrier()
        
sim = simulus.simulator()
bar = Barrier(sim, 10)
for i in range(10):
    sim.process(p, idx=i)
sim.run(10)
