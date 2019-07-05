import simulus

from random import seed, expovariate, gauss
seed(12345)

def student(student_id):
    print("student %d starts to work at %g" % 
          (student_id, sim.now))
    sim.sleep(gauss(30, 5)) # work on part one
    sim.sleep(expovariate(1/10.)) # take some rest
    sim.sleep(gauss(60, 10)) # work on part two
    print("student %d finishes working at %g" % 
          (student_id, sim.now))

def homework():
    print("homework assigned at "+str(sim.now))
    # five students working on the homework each starts at a random 
    # time (exponentially distributed with mean of 10)
    students = []
    for i in range(5):
        s = sim.process(student, i, offset=expovariate(1/10.))
        students.append(s)
    # wait for all student processes to complete
    sim.wait(students)
    print("last student finishes homework at "+str(sim.now))

sim = simulus.simulator()
sim.process(homework, offset=10) 
sim.run()
