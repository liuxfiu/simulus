# Simulus - A discrete-event simulator in Python

Simulus is an open-source process-oriented discrete-event simulator in
Python. In the near future, simulus will also support parallel and
distributed simulation, and real-time simulation.

## Installation

Run the following to install:

```
pip install simulus
```

## Usage

Simulus works in two ways. One way is through events. You can schedule
events and process them. We call it *direct event scheduling*. The
other way is through processes. You can create processes and have them
run and interact. We call it *process scheduling*. Of course, there's
a third way, by combining them and having them both.

The following a hello-world example, which simply schedules a function
invocation in the simulated future:

```
import simulus

def print_message(sim, params):
    print("Hello world at time "+str(sim.now))

sim = simulus.simulator()
sim.sched(print_message, until=10)
sim.run()
```

The following is an example that uses processes. In this example, a
homework process is created and scheduled to run at time 10. Then,
five students, each represented also as a process, will spend time
working on the homework. The homework process waits until all the
student processes finish before it ends.

```
import simulus

from random import seed, expovariate, gauss
seed(12345)

def student(sim, params):
    student_id = params.get("student_id")
    print("student %d starts to work at %g" % 
          (student_id, sim.now))
    sim.sleep(gauss(30, 5)) # work on part one
    sim.sleep(expovariate(1/10.)) # take some rest
    sim.sleep(gauss(60, 10)) # work on part two
    print("student %d finishes working at %g" % 
          (student_id, sim.now))

def homework(sim, params):
    print("homework assigned at "+str(sim.now))
    # five students working on the homework each starts at a random 
    # time (exponentially distributed with mean of 10)
    students = []
    for i in range(5):
        s = sim.process(student, expovariate(1/10.), student_id=i)
        students.append(s)
    # wait for all student processes to complete
    sim.wait(students)
    print("last student finishes homework at "+str(sim.now))
        
sim = simulus.simulator()
sim.process(homework, 10) 
sim.run()
```

Simulus also provides advanced features to make common modeling tasks
easier. For example, simulus provides resources and facilities, so
that multiple processes can access multi-server queues, and perform
producer-consumer synchronization over bounded buffers, among other
capabilities. Simulus also supports conditional and timed waits on
multiple resources and facilities.
