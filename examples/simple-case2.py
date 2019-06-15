import simulus

# A process for simulus is a python function with two parameters: 
# the first parameter is the simulator, and the second parameter is
# the dictionary containing user-defined parameters for the process
def myproc(sim, params):
    intv = params.get("intv")
    id = params.get("id")
    print(str(sim.now) + ": myproc(%d) runs with params=%r" % (id, params))
    while True:
        # suspend the process for some time
        sim.sleep(intv)
        print(str(sim.now) + ": myproc(%d) resumes execution" % id)

# create an anonymous simulator
sim2 = simulus.simulator()

# start a process 100 seconds from now
sim2.process(myproc, offset=100, intv=10, id=0)
# start another process 5 seconds from now
sim2.process(myproc, offset=5, intv=20, id=1)

# advance simulation until 200 seconds
sim2.run(until=200)
print("simulator.run() ends at " + str(sim2.now))

sim2.run(offset=50)
print("simulator.run() ends at " + str(sim2.now))
