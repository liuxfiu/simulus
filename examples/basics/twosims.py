import simulus

def handle(sim):
    print("'%s' handles event at time %g" % (sim.name, sim.now))

sim1 = simulus.simulator(name="sim1", init_time=100)
sim2 = simulus.simulator(name="sim2", init_time=-100)

for i in range(5, 100, 20):
    sim1.sched(handle, sim1, offset=i)
for i in range(5, 200, 30):
    sim2.sched(handle, sim2, offset=i)
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
