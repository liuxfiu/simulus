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

# we keep the account of the number of jobs in the system (those who
# have arrived but not yet departed); this is used to indicate whether
# there's a consumer process currently running; the value is more than
# 1, we don't need to create a new consumer process
jobs_in_system = 0

# the producer process waits for some random time from an exponential
# distribution to represent a new item being produced, creates a
# consumer process when necessary to represent the item being
# consumed, and then repeats
def producer(sim, mean_iat, mean_svc):
    global jobs_in_system
    while True:
        iat = expovariate(1.0/mean_iat)
        sim.sleep(iat)
        #print("%g: job arrives (iat=%g)" % (sim.now, iat))
        arrivals.append(sim.now)
        jobs_in_system += 1
        if jobs_in_system <= 1:
            sim.process(consumer, sim, mean_svc)
        
# the consumer process waits for the semaphore (it decrements
# the value and blocks if the value is non-positive), waits for
# some random time from another exponential distribution, and
# then repeats
def consumer(sim, mean_svc):
    global jobs_in_system
    while jobs_in_system > 0:
        #print("%g: job starts service" % sim.now)
        starts.append(sim.now)
        svc = expovariate(1.0/mean_svc)
        sim.sleep(svc)
        #print("%g: job departs (svc=%g)" % (sim.now, svc))
        finishes.append(sim.now)
        jobs_in_system -= 1

# create an anonymous simulator
sim3 = simulus.simulator()

# start the producer process only
sim3.process(producer, sim3, cfg['mean_iat'], cfg['mean_svc'])

# advance simulation until 100 seconds
sim3.run(until=1000)
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
