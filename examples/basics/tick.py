from random import seed, expovariate, randrange
from sys import maxsize 
import simulus

NQ = 5 # number of queues
TKTIME = 2 # interval between clock ticks

seed(12345)

def generator():
    jobid = 0 # job id increases monotonically 
    while True:
        sim.sleep(expovariate(1))
        q = randrange(0, NQ)
        print("%g: job[%d] enters queue %d" % (sim.now, jobid, q))
        queues[q].put(obj=jobid)
        jobid += 1

def checker():
    tick = TKTIME
    while True:
        t = [q.getter() for q in queues]
        qs, timedout = sim.wait(t, until=tick, method=any)
        if timedout:
            print("%g: clock's ticking" % sim.now)
            tick += TKTIME
        else:
            q = qs.index(True)
            print("%g: job[%d] leaves queue %d" % 
                  (sim.now, t[q].retval, q))
        
sim = simulus.simulator()
queues = [sim.store(capacity=maxsize) for _ in range(NQ)]
sim.process(generator)
sim.process(checker)
sim.run(10)
