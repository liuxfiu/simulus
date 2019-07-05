import simulus

def print_message():
    for _ in range(10):
        print("Hello world at time", sim.now)
        sim.sleep(1)
    
sim = simulus.simulator()
sim.process(print_message, until=10)
sim.run()
