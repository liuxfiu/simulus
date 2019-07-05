"""This example is modified from the simpy's bank renege example; we
use the same settings as simpy so that we can get the same results."""

RANDOM_SEED = 42        # random seed for repeatability
NUM_CUSTOMERS = 5       # total number of customers
INTV_CUSTOMERS = 10.0   # mean time between new customers
MEAN_BANK_TIME = 12.0   # mean time in bank for each customer
MIN_PATIENCE = 1        # min customer patience
MAX_PATIENCE = 3        # max customer patience

import simulus
from random import seed, expovariate, uniform

def source():
    for i in range(NUM_CUSTOMERS):
        sim.process(customer, i)
        sim.sleep(expovariate(1.0/INTV_CUSTOMERS))

def customer(idx):
    arrive = sim.now
    print('%7.4f Customer%02d: Here I am' % (arrive, idx))

    patience = uniform(MIN_PATIENCE, MAX_PATIENCE)
    _, timedout = sim.wait(counter, patience)
    if timedout:
        print('%7.4f Customer%02d: RENEGED after %6.3f' %
              (sim.now, idx, sim.now-arrive))
    else:
        # We got to the counter
        print('%7.4f Customer%02d: Waited %6.3f' %
              (sim.now, idx, sim.now-arrive))
        sim.sleep(expovariate(1.0/MEAN_BANK_TIME))
        print('%7.4f Customer%02d: Finished' % (sim.now, idx))
        counter.release()

print('Bank renege')
seed(RANDOM_SEED)
sim = simulus.simulator()
counter = sim.resource()
sim.process(source)
sim.run()
