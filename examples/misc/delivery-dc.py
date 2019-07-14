import simulus

from random import seed, expovariate, randint
seed(12345)

def generate():
    num = 0
    while True:
        sim.sleep(expovariate(1))
        for _ in range(randint(1,5)): # send a bunch
            mb.send(num)
            num += 1

def get_one():
    while True:
        sim.sleep(1)
        msg = mb.recv(isall=False)

def get_all():
    while True:
        sim.sleep(5)
        msgs = mb.recv()

sim = simulus.simulator()
dc = simulus.DataCollector(messages='timeseries(all)')
mb = sim.mailbox(collect=dc)
sim.process(generate)
sim.process(get_one)
sim.process(get_all)
sim.run(22)
dc.report(sim.now)
