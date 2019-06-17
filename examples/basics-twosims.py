import simulus
from random import seed, randint, uniform

def handle(sim, params):
    print("simulator %s handles event at time %g" % (sim.name, sim.now))

sim1 = simulus.simulator(name="sim1", init_time=10)
sim2 = simulus.simulator(name="sim2", init_time=-100)
seed(12345)
for i in range(randint(1,10)):
    sim1.sched(handle, offset=uniform(0,100))
for i in range(randint(1,10)):
    sim2.sched(handle, offset=uniform(0,200))
sim1.show_calendar()
sim2.show_calendar()

while True:
    t1, t2 = sim1.peek(), sim2.peek()
    if t1 < simulus.infinite_time:
        sim1.step()
    if t2 < simulus.infinite_time:
        sim2.step()
    if t1 == simulus.infinite_time and \
       t2 == simulus.infinite_time:
        break
