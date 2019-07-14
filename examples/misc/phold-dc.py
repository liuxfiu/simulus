import simulus

from random import seed, expovariate, randrange
seed(12345)

job_count = 100
node_count = 4
lookahead = 1

def generate(idx):
    while True:
        msg = mb[idx].recv(isall=False)
        target = randrange(node_count)
        mb[target].send(msg, expovariate(1)+lookahead)

sim = simulus.simulator()

dc = simulus.DataCollector(
    messages='timeseries(all)',
    arrivals='timemarks(all)',
    retrievals='timemarks(all)'
)
mb = []
for idx in range(node_count):
    if idx>0: mb.append(sim.mailbox())
    else: mb.append(sim.mailbox(collect=dc))
    sim.process(generate, idx)

for idx in range(job_count):
    target = randrange(node_count)
    delay = expovariate(1)+lookahead
    mb[target].send(idx, delay)

sim.run(100)
dc.report(sim.now)
