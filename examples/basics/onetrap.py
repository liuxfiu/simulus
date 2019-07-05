import simulus

def p(idx):
    if idx > 0:
        print("p%d starts at %g and waits on trap" % (idx, sim.now))
        t.wait()
        print("p%d resumes at %g" % (idx, sim.now))
    else:
        print("p%d starts at %g" % (idx, sim.now))
        sim.sleep(5)
        print("p%d triggers the trap at %g" % (idx, sim.now))
        t.trigger()

sim = simulus.simulator()
t = sim.trap()
for i in range(10):
    sim.process(p, i, offset=10+i)
sim.run()
