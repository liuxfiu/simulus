import simulus

from random import seed, expovariate, gauss
seed(12345)

def work(sim, params):
    student_id = params.get("student_id")
    print("student %d starts working on homework at %g" % 
          (student_id, sim.now))
    sim.sleep(guass(30, 5)) # work on part one
    sim.sleep(expovariate(1/10.)) # take some rest
    sim.sleep(guass(60, 10)) # work on part two
    print("student %d finishes working on homework at %g" % 
          (student_id, sim.now))

def assign(sim, params):
    print("homework assigned at "+str(sim.now))
    students = []
    for i in range(10):
        s = sim.process(work, expovariate(1/10.), student_id=i)
        students.append(s)
    sim.join(students)
    print("last student finishes homework at "+str(sim.now))
        
sim = simulus.simulator()
sim.process(assign) 
sim.run()
