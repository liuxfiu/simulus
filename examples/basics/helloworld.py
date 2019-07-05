import simulus

def print_message():
    print("Hello world at time", sim.now)
    
sim = simulus.simulator()
sim.sched(print_message, until=10)
sim.run()
