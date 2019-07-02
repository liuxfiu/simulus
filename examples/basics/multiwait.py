import simulus

def p1(sim, params):
    sim.sleep(10)
    print("p1 triggers t1 at %g" % sim.now)
    t1.trigger()

    sim.sleep(10)
    print("p1 triggers s1 at %g" % sim.now)
    s1.trigger() # signal and trigger are aliases for semaphore

    sim.sleep(10)
    print("p1 triggers t2 at %g" % sim.now)
    t2.trigger()

    sim.sleep(10)
    print("p1 triggers s2 at %g" % sim.now)
    s2.signal()

def p2(sim, params):
    tp = (t1, s1)
    r = sim.wait(tp)
    print("p2 resumes at %g (ret=%r)" % (sim.now, r))

    tp = [t2, s2]
    r = sim.wait(tp, method=any)
    print("p2 resumes at %g (ret=%r)" % (sim.now, r))

    # find the remaining untriggered trappables (using the 
    # returned mask) and wait for them all
    tp = [t for i, t in enumerate(tp) if not r[i]]
    r = sim.wait(tp)
    print("p2 resumes at %g (ret=%r)" % (sim.now, r))

sim = simulus.simulator()
t1 = sim.trap()
t2 = sim.trap()
s1 = sim.semaphore()
s2 = sim.semaphore()
sim.process(p1)
sim.process(p2)
sim.run()
