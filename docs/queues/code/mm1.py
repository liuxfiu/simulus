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

def gen_arrivals():
    while True:
        sim.sleep(next(inter_arrival_time))
        sim.process(customer)

def customer():
    print('%g: customer arrives (num_in_system=%d->%d)' %
          (sim.now, server.num_in_system(), server.num_in_system()+1))
    server.acquire()
    sim.sleep(next(service_time))
    print('%g: customer departs (num_in_system=%d->%d)' %
          (sim.now, server.num_in_system(), server.num_in_system()-1))
    server.release()

random.seed(13579) # global random seed

sim = simulus.simulator('ssq')
inter_arrival_time = exp_generator(1.2, sim.rng().randrange(2**32))
service_time = exp_generator(0.8, sim.rng().randrange(2**32))
server = sim.resource()
sim.process(gen_arrivals)
sim.run(10)
