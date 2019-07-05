import simulus

# An event handler is a user-defined function; in this case, we take
# one positional argument 'sim', and place all keyworded arguments in
# the dictionary 'params'
def myfunc(sim, **params):
    print(str(sim.now) + ": myfunc() runs with params=" + str(params))

    # schedule the next event 10 seconds from now
    sim.sched(myfunc, sim, **params, offset=10)

# create an anonymous simulator
sim1 = simulus.simulator() 

# schedule the first event at 10 seconds
sim1.sched(myfunc, sim1, until=10, msg="hello world", value=100)

# advance simulation until 100 seconds
sim1.run(until=100)
print("simulator.run() ends at " + str(sim1.now))

# we can advance simulation for another 50 seconds
sim1.run(offset=50)
print("simulator.run() ends at " + str(sim1.now))
