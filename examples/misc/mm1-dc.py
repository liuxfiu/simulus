import simulus, random

random.seed(123)

def job():
    r.acquire()
    sim.sleep(random.expovariate(1.1))
    r.release()

def arrival():
    while True:
        sim.sleep(random.expovariate(1))
        sim.process(job)

sim = simulus.simulator()

dc = simulus.DataCollector(
    arrivals='timemarks(all)', 
    inter_arrivals='dataseries()',
    system_times='dataseries(all)',
    in_systems='timeseries(all)',
    in_queues='timeseries(all)'
)
r = sim.resource(collect=dc)

sim.process(arrival)
sim.run(1000)
dc.report(sim.now)
