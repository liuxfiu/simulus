import simulus

from random import seed, expovariate
from statistics import mean, median, stdev

# make it repeatable
seed(12345) 

# configuration of the single server queue: the mean inter-arrival
# time, and the mean service time
cfg = {"mean_iat":1, "mean_svc":0.8}

# keep the time of job arrivals, starting services, and departures
arrivals = []
starts = []
finishes = []

# the producer process waits for some random time from an 
# exponential distribution, and increments the semaphore 
# to represent a new item being produced, and then repeats 
def producer(sim, params):
    mean_iat = params.get("mean_iat")
    sem = params.get("sem")
    while True:
        iat = expovariate(1.0/mean_iat)
        sim.sleep(iat)
        print("%g: job arrives (iat=%g)" % (sim.now, iat))
        arrivals.append(sim.now)
        sem.signal()
        
# the consumer process waits for the semaphore (it decrements
# the value and blocks if the value is non-positive), waits for
# some random time from another exponential distribution, and
# then repeats
def consumer(sim, params):
    mean_svc = params.get("mean_svc")
    sem = params.get("sem")
    while True:
        sem.wait()
        print("%g: job starts service" % sim.now)
        starts.append(sim.now)
        svc = expovariate(1.0/mean_svc)
        sim.sleep(svc)
        print("%g: job departs (svc=%g)" % (sim.now, svc))
        finishes.append(sim.now)

# create an anonymous simulator
sim3 = simulus.simulator()

# create a semaphore with initial value of zero
sem = sim3.semaphore(0)

# start the producer and consumer processes
sim3.process(producer, params=cfg, sem=sem)
sim3.process(consumer, params=cfg, sem=sem)

# advance simulation until 100 seconds
sim3.run(until=100)
print("simulator.run() ends at " + str(sim3.now))

# calculate and output statistics
print(f'Results: jobs=arrival:{len(arrivals)}, starts:{len(starts)}, finishes:{len(finishes)}')
waits = [start - arrival for arrival, start in zip(arrivals, starts)]
totals = [finish - arrival for arrival, finish in zip(arrivals, finishes)]
print(f'Wait Time: mean={mean(waits):.1f}, stdev={stdev(waits):.1f}, median={median(waits):.1f}.  max={max(waits):.1f}')
print(f'Total Time: mean={mean(totals):.1f}, stdev={stdev(totals):.1f}, median={median(totals):.1f}.  max={max(totals):.1f}')
my_lambda = 1.0/cfg['mean_iat'] # mean arrival rate
my_mu = 1.0/cfg['mean_svc'] # mean service rate
my_rho = my_lambda/my_mu # server utilization
my_lq = my_rho*my_rho/(1-my_rho) # number in queue
my_wq = my_lq/my_lambda # wait in queue
my_w = my_wq+1/my_mu # wait in system
print(f'Theoretical Results: mean wait time = {my_wq:.1f}, mean total time = {my_w:.1f}')
