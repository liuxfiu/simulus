import simulus

from random import seed, gauss, uniform
seed(321)

def tom():
    sim.sleep(max(0, gauss(100, 50)))
    print("%g: tom finished" % sim.now)

def jerry():
    print("%g: jerry finished" % sim.now)

def compete():
    tom_won, jerry_won = 0, 0
    for _ in range(10):
        print("<-- competition starts at %g -->" % sim.now)

        p = sim.process(tom) # run, tom, run!
        e = sim.sched(jerry, offset=uniform(50, 150)) # run, jerry, run!
    
        # let the race begin...
        (r1, r2), timedout = sim.wait((p, e), 100, method=any)
        if timedout:
            print("%g: both disqualified" % sim.now)
            sim.kill(p)
            sim.cancel(e)
        elif r1: 
            print("%g: tom wins" % sim.now)
            tom_won += 1
            sim.cancel(e)
        else:
            print("%g: jerry wins" % sim.now)
            jerry_won += 1
            sim.kill(p)
    print("final result: tom:jerry=%d:%d" % (tom_won, jerry_won))
    
sim = simulus.simulator()
sim.process(compete)
sim.run()
