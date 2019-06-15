import simulus

# simulus.sync brings all simulators in synchrony; that is,
# the simulation clock of the simulators from now on will 
# be advanced in a coordinated fashion; when this function 
# returns, the simulation clock of the simulators will be 
# the maximum simulation clock time of all simulators
simulus.sync([sim1, sim2, sim3], lookahead=1.0)
print("sim1.now=" + str(sim1.now))
print("sim2.now=" + str(sim2.now))
print("sim3.now=" + str(sim3.now))

# advance simulation for another 100 seconds (since the 
# simulators are synchronized now; all simulators will 
# advance the time together)
sim1.run(offset=100)
print("simulator.run() ends at " + str(sim1.now))
