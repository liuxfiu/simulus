import simulus

# An event handler for simulus is a python function with two parameters:
# the first parameter is the simulator, and the second parameters is
# the dictionary containing user-defined parameters for the event handler
def myfunc(sim, params):
    print(str(sim.now) + ": myfunc() runs with params=" + str(params))
    # schedule the next event at 5 seconds from now
    sim.sched(myfunc, params=params, offset=5)

# create an anonymous simulator
sim1 = simulus.simulator() 

# schedule the first event at 10 seconds
sim1.sched(myfunc, until=10, msg="hello world", value=100)

# advance simulation until 100 seconds
sim1.run(until=100)
print("simulator.run() ends at " + str(sim1.now))

# we can advance simulation for another 50 seconds
sim1.run(offset=50)
print("simulator.run() ends at " + str(sim1.now))
