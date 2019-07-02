import simulus

from random import seed, gauss, uniform
seed(321)

def tom(sim, params):
    sim.sleep(gauss(100, 50))
    print("%g: tom finished" % sim.now)

def jerry(sim, params):
    print("%g: jerry finished" % sim.now)

def compete(sim, params):
    for _ in range(10):
        print("competition starts at %g -->" % sim.now)

        p = sim.process(tom) # run, tom, run!
        t1 = sim.trap(p)
    
        e = sim.sched(jerry, uniform(50, 150)) # run, jerry, run!
        t2 = sim.trap(e)
    
        # let the race begin...
        (r1, r2), timedout = sim.wait((t1, t2), 100, method=any)
        if timedout:
            print("%g: both disqualified" % sim.now)
            sim.kill(p)
            sim.cancel(e)
        elif r1: 
            print("%g: tom wins" % sim.now)
            sim.cancel(e)
        else:
            print("%g: jerry wins" % sim.now)
            sim.kill(p)

sim = simulus.simulator()
sim.process(compete)
sim.run()
