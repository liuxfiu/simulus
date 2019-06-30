import simulus

def print_message(sim, params):
    for _ in range(10):
        print("Hello world at time "+str(sim.now))
        sim.sleep(1)
    
sim = simulus.simulator()
sim.process(print_message, until=10)
sim.run()
