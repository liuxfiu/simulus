
# Simulus - A discrete-event simulator in Python

Simulus is an open-source discrete-event simulator in Python. Simulus
fully supports the process-oriented simulation world-view.

In the near future, simulus will support parallel and distributed
simulation, and real-time simulation.

## Installation

Run the following to install:

```python
pip install simulus
```

## Usage

Simulus works in two ways. One way is through events. The user schedules events. Simulus makes sure all events are sorted in timestamp order. When an event happens, simulus advances the simulation time to the event and calls the event handler, which is a user defined function. While processing the event, the user can schedule new events into the simulated future. We call this *direct event scheduling*. 

The other way is through processes. The user can create processes and have them run and interact. Each process is a separate thread of control. During its execution, a process may be blocked, either sleeping for some time or requesting for some resource that is currently unavailable. The process can resume execution when the specified time has passed or after the resource blocking condition has been removed. We call this *process scheduling*. 

In simulus, both direct event scheduling and process scheduling can be used together to achieve the modeling tasks.

The following a hello-world example, which simply schedules a function invocation in the simulated future:


```python
import simulus

def print_message():
    print("Hello world at time", sim.now)
    sim.sched(print_message, offset=10)
    
sim = simulus.simulator()
sim.sched(print_message, until=10)
sim.run(100)
```

    Hello world at time 10
    Hello world at time 20
    Hello world at time 30
    Hello world at time 40
    Hello world at time 50
    Hello world at time 60
    Hello world at time 70
    Hello world at time 80
    Hello world at time 90
    Hello world at time 100


The following is the same hello-world example, but instead we use a process: 


```python
import simulus

def print_message():
    while True:
        print("Hello world at time", sim.now)
        sim.sleep(10)
    
sim = simulus.simulator()
sim.process(print_message, until=10)
sim.run(100)
```

    Hello world at time 10
    Hello world at time 20
    Hello world at time 30
    Hello world at time 40
    Hello world at time 50
    Hello world at time 60
    Hello world at time 70
    Hello world at time 80
    Hello world at time 90
    Hello world at time 100


Simulus supports conditional wait and allows events and processes to coexist. The following shows a example that Tom and Jerry entering a race. We model Tom as a process. Each time, Tom calls sleep() to represent running for some time, which is a random variable from a normal distribution with a mean 100 and a standard deviation of 50 (with a cutoff below zero). We model Jerry as an event. Jerry calls sched() to schedule an event to represent running for some time, which is a random variable from a uniform distribution between 50 and 100. Tom and Jerry compete for ten times; the next race starts as soon as the previous one finishes. Whoever runs fastest wins. But if they run for more than 100 seconds, both are disqualified for that race.


```python
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
        print("<--- competition starts at %g -->" % sim.now)

        p = sim.process(tom) # run, tom, run!
        e = sim.sched(jerry, offset=uniform(50, 150)) # run, jerry, run!
    
        # let the race begin...
        (r1, r2), timedout = sim.wait((p, e), 100, method=any)
        if timedout:
            print("%g: both disqualified" % sim.now)
            sim.kill(p) # both tom and ...|
            sim.cancel(e) # jerry can stop running now
        elif r1: 
            print("%g: tom wins" % sim.now)
            tom_won += 1
            sim.cancel(e) # jerry can stop running now
        else:
            print("%g: jerry wins" % sim.now)
            jerry_won += 1
            sim.kill(p) # tom can stop running now
    print("final result: tom:jerry=%d:%d" % (tom_won, jerry_won))

sim = simulus.simulator()
sim.process(compete)
sim.run()
```

    <--- competition starts at 0 -->
    77.5459: jerry finished
    77.5459: jerry wins
    <--- competition starts at 77.5459 -->
    171.749: jerry finished
    171.749: jerry wins
    <--- competition starts at 171.749 -->
    271.749: both disqualified
    <--- competition starts at 271.749 -->
    357.072: tom finished
    357.072: tom wins
    <--- competition starts at 357.072 -->
    430.387: tom finished
    430.387: tom wins
    <--- competition starts at 430.387 -->
    485.297: tom finished
    485.297: tom wins
    <--- competition starts at 485.297 -->
    585.297: both disqualified
    <--- competition starts at 585.297 -->
    611.838: tom finished
    611.838: tom wins
    <--- competition starts at 611.838 -->
    711.838: both disqualified
    <--- competition starts at 711.838 -->
    811.838: both disqualified
    final result: tom:jerry=4:2


Simulus also provides several advanced features to ease the common modeling tasks. For example, simulus provides the modeling abstraction for resources and facilities, so that multiple processes can access single-server or multi-server queues, perform producer-consumer synchronization over bounded buffers, and conduct message-passing communication among them.

For more information, check out the Simulus Tutorial, available at the homepage.
