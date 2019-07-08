
# Quick Start

Simulus is an open-source discrete-event simulator in Python. Simulus implements a process-oriented simulation world-view with several advanced features to ease modeling and simulation tasks with both events and processes.  Simulus will soon add support for parallel and distributed simulation (planned for version 1.2), and real-time simulation (planned for version 1.3).

* Online documentation:
http://simulus.readthedocs.io/

* Source code repository:
https://github.com/liuxfiu/simulus/

* License:
MIT – see the file LICENSE for details.


## Installation

Simulus should run with Python version 2.8 and above. If your python is too old, you should consider updating your Python as well as `pip` (Python’s package manager).

You should be able to install simulus with `pip`:

```
pip install simulus
```

This will install simulus system-wide for all users (assuming you have the necessary privilege on your machine). The installation will also automatically include all Python packages needed by simulus.

You can also install simulus for just yourself, using:

```
pip install --user simulus
```

If you had simulus installed previously, you can always upgrade the existing simulus installation with the newest release, using:

```
pip install --upgrade --user simulus
```


## Basic Usage

We show the basic use of simulus in the following. For more detailed information, you can check out the simulus tutorial mentioned above.

Simulus can work in two ways. One way is through events. The user schedules events. Simulus makes sure all events are sorted in timestamp order. When an event happens, simulus advances the simulation time to the event and calls the event handler, which is just a user-defined function. While processing the event, the user can schedule new events into the simulated future. We call this approach *direct event scheduling*. 

The other way is through processes. The user can create processes and have them run and interact. Each process is a separate thread of control. During its execution, a process may be suspended, by either sleeping for some time or getting blocked when requesting for some resources currently unavailable. The process resumes execution when the specified time has passed or after the resource blocking conditions have been removed. We call this approach *process scheduling*. 

In simulus, both direct event scheduling and process scheduling can be used together seamlessly to achieve the modeling tasks.

The following a hello-world example, which simply schedules a function (a.k.a. an event handler) to be invoked in the simulated future. Inside the function, the user schedules the same function again.


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


The following is the same hello-world example, but instead we use a process. A process is a continous thread of execution. In the example, once started, the process loops forever. Inside each iteration, the process prints out a message and then sleeps for some time.


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


Simulus allows events and processes to coexist. For example, simulus supports conditional-wait on both events and processes. The following shows an example that models Tom and Jerry entering a race. 

Tom is modeled by processes. Each time Tom enters the race, we create a process, which calls `sleep()` to represent the time duration for the run. The time duration is a random variable from a normal distribution with a mean of 100 and a standard deviation of 50 (and a cutoff below zero). Jerry is modeled by events. Each time Jerry enters the race, we schedule an event using `sched()` with a time offset representing the time duration for the run. The time duration is a random variable from a uniform distribution between 50 and 100. 

Tom and Jerry compete for ten times; the next race would start as soon as the previous one finishes. For each race, whoever runs the fastest wins. But if they run for more than 100, both are disqualified for that race. The simulation finds out who eventually wins more races.


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
        # the return values indicate which wait conditions have been satisfied
        if timedout:
            print("%g: both disqualified" % sim.now)
            sim.cancel(p) # both tom and ...
            sim.cancel(e) # jerry can stop running now
        elif r1: 
            print("%g: tom wins" % sim.now)
            tom_won += 1
            sim.cancel(e) # jerry can stop running now
        else:
            print("%g: jerry wins" % sim.now)
            jerry_won += 1
            sim.cancel(p) # tom can stop running now
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


Simulus also provides several advanced features to ease the common modeling and simulation tasks, including those for modeling single-server or multi-server queues, for performing producer-consumer synchronization over bounded buffers, and for conducting message-passing communication among the processes.

For example, simulus provides the modeling abstraction of a "store", which is a facility for storing countable objects (such as jobs in a queue, packets in a network router, and io requests arrived at a storage device), or for storing uncountable quantities or volumes (such as gas in a tank, water in a reservoir, and battery power in a mobile device). The following example shows the use of store as a bounded buffer with multiple producers and consumers.


```python
import simulus

from random import seed, expovariate
seed(12345)

items_produced = 0 # keep track the number of items being produced

def producer(idx):
    global items_produced
    while True:
        sim.sleep(expovariate(1)) # take time to produce an item
        serial_no = items_produced
        items_produced += 1
        print("%f: producer %d produces item [%d]" % (sim.now, idx, serial_no))
        s.put(obj=serial_no)
        print("%f: producer %d stores item [%d] in buffer" % 
              (sim.now, idx, serial_no))
        
def consumer(idx):
    while True:
        serial_no = s.get()
        print("%f: consumer %d retrieves item [%d] from buffer" %
              (sim.now, idx, serial_no))
        sim.sleep(expovariate(1)) # take time to consume the item
        print("%f: consumer %d consumes item [%d]" % (sim.now, idx, serial_no))

sim = simulus.simulator()

# create a buffer with 3 slots
s = sim.store(capacity=3)

# create 2 producers and 3 consumers
for i in range(2): 
    sim.process(producer, i)
for i in range(3):
    sim.process(consumer, i)

sim.run(5)

```

    0.010221: producer 1 produces item [0]
    0.010221: producer 1 stores item [0] in buffer
    0.010221: consumer 0 retrieves item [0] from buffer
    0.364955: consumer 0 consumes item [0]
    0.538916: producer 0 produces item [1]
    0.538916: producer 0 stores item [1] in buffer
    0.538916: consumer 2 retrieves item [1] from buffer
    0.754168: consumer 2 consumes item [1]
    0.998434: producer 0 produces item [2]
    0.998434: producer 0 stores item [2] in buffer
    0.998434: consumer 1 retrieves item [2] from buffer
    1.174799: consumer 1 consumes item [2]
    1.754371: producer 1 produces item [3]
    1.754371: producer 1 stores item [3] in buffer
    1.754371: consumer 0 retrieves item [3] from buffer
    1.833163: producer 0 produces item [4]
    1.833163: producer 0 stores item [4] in buffer
    1.833163: consumer 2 retrieves item [4] from buffer
    1.887065: producer 1 produces item [5]
    1.887065: producer 1 stores item [5] in buffer
    1.887065: consumer 1 retrieves item [5] from buffer
    2.024740: consumer 2 consumes item [4]
    2.321655: consumer 0 consumes item [3]
    2.325417: consumer 1 consumes item [5]
    2.658879: producer 0 produces item [6]
    2.658879: producer 0 stores item [6] in buffer
    2.658879: consumer 2 retrieves item [6] from buffer
    2.692757: producer 1 produces item [7]
    2.692757: producer 1 stores item [7] in buffer
    2.692757: consumer 0 retrieves item [7] from buffer
    2.754613: consumer 2 consumes item [6]
    3.223988: consumer 0 consumes item [7]

