# for random distributions, random number generators, statistics
import random
import numpy as np
import scipy.stats as stats

# for simulation
import simulus

random.seed(13579) # global random seed

def exp_generator(mean, seed):
    rv = stats.expon(scale=mean)
    rv.random_state = np.random.RandomState(seed)
    while True:
        # 100 random numbers as a batch
        for x in rv.rvs(100):
            yield x

def truncnorm_generator(a, b, seed):
    rv = stats.truncnorm(a, b)
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
    server.acquire()
    sim.sleep(next(service_time))
    server.release()

def sim_run(a, b):
    global sim, inter_arrival_time, service_time, server
    sim = simulus.simulator()
    inter_arrival_time = exp_generator(1.2, sim.rng().randrange(2**32))
    service_time = truncnorm_generator(a, b, sim.rng().randrange(2**32))
    dc = simulus.DataCollector(system_times='dataseries')
    server = sim.resource(collect=dc)
    sim.process(gen_arrivals)
    sim.run(1000)
    return dc.system_times.mean()

x = np.linspace(0.1, 3.0, 30)
y = []
e1 = []
e2 = []
for b in x:
    z = []
    for _ in range(25):
        z.append(sim_run(0, b))
    z = np.array(z)
    y.append(z.mean())
    e1.append(np.percentile(z, 5))
    e2.append(np.percentile(z, 95))

print('b\tmean\tlow\thigh')
for a, b, c, d in zip(x, y, e1, e2):
    print('%.1f\t%.4f\t%.4f\t%.4f' % (a, b, c, d))

