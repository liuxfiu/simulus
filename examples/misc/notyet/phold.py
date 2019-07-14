import simulus

from random import seed, expovariate, randrange
from collections import deque

# simulation configs in one place
simcfg = {
    "seed":12345,       # random seed for repeatability
    "num_nodes":10,     # number of nodes in system
    "num_jobs":1,       # number of (initial) jobs at each node
    "mean_svc":0.8,     # mean service time (exponential distributed)
}

class Node:
    def __init__(self, id):
        self.id = id
        self.num_jobs = simcfg['num_jobs'] # initial jobs

        # for statistics; we keep track the arrival time of the jobs
        # and the total wait time for the processed jobs
        self.arrivals = deque([0]*self.num_jobs)
        self.processed = 0
        self.sum_wait = 0.0

    def service(self):
        # service each job, one at a time
        while self.num_jobs > 0:
            # service the job
            svc = expovariate(1.0/simcfg['mean_svc'])
            print("%g: n%d[%d] services for %g (until=%g)" %
                  (sim.now, self.id, self.num_jobs, svc, sim.now+svc))
            sim.sleep(svc)

            # ship the job from this node to the next
            self.num_jobs -= 1
            self.sum_wait += sim.now-self.arrivals.popleft()
            self.processed += 1
            n = randrange(simcfg["num_nodes"])
            nodes[n].num_jobs += 1
            nodes[n].arrivals.append(sim.now)
            print("%g: n%d[%d] ships job to n%d[%d]" %
                  (sim.now, self.id, self.num_jobs, n, nodes[n].num_jobs))
            if n != self.id and nodes[n].num_jobs <= 1:
                sim.process(Node.service, nodes[n])

seed(simcfg['seed'])
sim = simulus.simulator()
nodes = [Node(i) for i in range(simcfg['num_nodes'])]
for n in nodes:
    sim.process(Node.service, n)
sim.run(until=100)

total_wait = sum([n.sum_wait for n in nodes])
total_jobs = sum([n.processed for n in nodes])
print("average wait time: %g" % (total_wait/total_jobs))
