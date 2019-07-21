# for random distributions, random number generators, statistics
import random
import numpy as np
import scipy.stats as stats

# for simulation
import simulus

def exp_generator(mean, seed):
    rv = stats.expon(scale=mean)
    rv.random_state = np.random.RandomState(seed)
    while True:
        # 100 random numbers as a batch
        for x in rv.rvs(100):
            yield x

def arrive():
    global num_in_system
    print('%g: customer arrives (num_in_system=%d->%d)' %
          (sim.now, num_in_system, num_in_system+1))
    
    # increment the total number of customers in system
    num_in_system += 1
    
    # schedule next customer's arrival
    sim.sched(arrive, offset=next(inter_arrival_time))
    
    # the arrived customer is the only one in system
    if num_in_system == 1:
        # schedule the customer's departure
        sim.sched(depart, offset=next(service_time))

def depart():
    global num_in_system
    print('%g: customer departs (num_in_system=%d->%d)' %
          (sim.now, num_in_system, num_in_system-1))
    
    # decrement the total number of customers in system
    num_in_system -= 1
    
    # there are remaining customers in system
    if num_in_system > 0:
        # schedule the next customer's departure
        sim.sched(depart, offset=next(service_time))

random.seed(13579) # global random seed

sim = simulus.simulator('ssq')
inter_arrival_time = exp_generator(1.2, sim.rng().randrange(2**32))
service_time = exp_generator(0.8, sim.rng().randrange(2**32))

num_in_system = 0
sim.sched(arrive, offset=next(inter_arrival_time))
sim.run(10)
