# for random distributions, random number generators, statistics
import random
import numpy as np
import scipy.stats as stats

# for simulation
import simulus

from collections import deque

def exp_generator(mean, seed):
    rv = stats.expon(scale=mean)
    rv.random_state = np.random.RandomState(seed)
    while True:
        # 100 random numbers as a batch
        for x in rv.rvs(100):
            yield x

def arrive():
    # add the customer to the end of the queue
    queue.append(sim.now)
    in_systems.append((sim.now, len(queue)))
    
    # schedule next customer's arrival
    sim.sched(arrive, offset=next(inter_arrival_time))
    
    # the arrived customer is the only one in system
    if len(queue) == 1:
        # schedule the customer's departure
        sim.sched(depart, offset=next(service_time))
        
def depart():
    # remove a customer from the head of the queue
    t = queue.popleft()
    in_systems.append((sim.now, len(queue)))
    waits.append(sim.now-t)
    
    # there are remaining customers in system
    if len(queue) > 0:
        # schedule the next customer's departure
        sim.sched(depart, offset=next(service_time))

random.seed(13579) # global random seed

queue = deque()
in_systems = [(0,0)]
waits = []

sim = simulus.simulator('ssq')
inter_arrival_time = exp_generator(1.2, sim.rng().randrange(2**32))
service_time = exp_generator(0.8, sim.rng().randrange(2**32))
sim.sched(arrive, offset=next(inter_arrival_time))
sim.run(10000)

print('wait times: %r...' % waits[:3])
print('number customers in systems: %r...' % in_systems[:3])

waits = np.array(waits)
print("wait time: mean=%g, stdev=%g" % 
      (waits.mean(), waits.std()))

# area under curve divided by time is the 
# average number of customers in system
auc, last_t, last_l = 0, 0, 0
for t, l in in_systems:
    auc += (t-last_t)*last_l
    last_t, last_l = t, l
print("avg number of customers in system = %g" % (auc/last_t))
