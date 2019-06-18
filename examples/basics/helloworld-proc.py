import simulus

def print_message(sim, params):
    print("Hello world at time "+str(sim.now))
    
sim = simulus.simulator()
sim.process(print_message, until=10)
sim.run()
