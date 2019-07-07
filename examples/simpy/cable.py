"""This example is modified from the simpy's event latency example; we
use the same settings as simpy so that we can get the same results."""

SIM_DURATION = 100

import simulus

class Cable(object):
    """This class represents the propagation through a cable."""
    def __init__(self, sim, delay):
        self.sim = sim
        self.delay = delay
        self.store = sim.store()

    def latency(self, value):
        sim.sleep(self.delay)
        self.store.put(obj=value)

    def put(self, value):
        sim.process(self.latency, value)

    def get(self):
        return self.store.get()

def sender(sim, cable):
    """A process which randomly generates messages."""
    while True:
        # wait for next transmission
        sim.sleep(5)
        cable.put('Sender sent this at %d' % sim.now)

def receiver(sim, cable):
    """A process which consumes messages."""
    while True:
        # Get event for message pipe
        msg = cable.get()
        print('Received this at %d while %s' % (sim.now, msg))

# Setup and start the simulation
print('Event Latency')
sim = simulus.simulator()

cable = Cable(sim, 10)
sim.process(sender, sim, cable)
sim.process(receiver, sim, cable)

sim.run(until=SIM_DURATION)
