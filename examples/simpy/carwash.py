"""This example is modified from the simpy's carwash example; we use
the same settings trying to get the same results, but we won't be able
to do that, because simpy and simulus handle process scheduling and
sort simultaneous events differently."""

RANDOM_SEED = 42  # Random seed for repeatability
NUM_MACHINES = 2  # Number of machines in the carwash
WASHTIME = 5      # Minutes it takes to clean a car
T_INTER = 7       # Create a car every ~7 minutes
SIM_TIME = 20     # Simulation time in minutes

import simulus
from random import seed, randint

class Carwash(object):
    """A carwash has a limited number of machines (NUM_MACHINES) to
    clean cars in parallel. Cars have to request one of the
    machines. When they get one, they can start the washing process
    and wait for it to finish (which takes ``washtime`` minutes)."""

    def __init__(self, sim, num_machines, washtime):
        self.sim = sim
        self.machine = sim.resource(num_machines)
        self.washtime = washtime

    def wash(self, carname):
        """The washing process. It takes a car (the name of which is given)
        and tries to clean it."""
        self.sim.sleep(WASHTIME)
        print("Carwash removed %d%% of %s's dirt." %
              (randint(50, 99), carname))

def car(sim, name, cw):
    """The car process (each car has a name) arrives at the carwash (cw)
    and requests a cleaning machine.  It then starts the washing
    process, waits for it to finish and leaves to never come back..."""

    print('%s arrives at the carwash at %.2f.' % (name, sim.now))
    cw.machine.acquire()

    print('%s enters the carwash at %.2f.' % (name, sim.now))
    cw.wash(name)

    print('%s leaves the carwash at %.2f.' % (name, sim.now))
    cw.machine.release()

def setup(sim, num_machines, washtime, t_inter):
    """Create a carwash, a number of initial cars and keep creating cars
    approx. every ``t_inter`` minutes."""

    # Create the carwash
    carwash = Carwash(sim, num_machines, washtime)

    # Create 4 initial cars
    for i in range(4):
        sim.process(car, sim, 'Car %d' % i, carwash)

    # Create more cars while the simulation is running
    while True:
        sim.sleep(randint(t_inter - 2, t_inter + 2))
        i += 1
        sim.process(car, sim, 'Car %d' % i, carwash)

# Setup and start the simulation
print('Carwash')
seed(RANDOM_SEED)

# Create a simulator and start the setup process
sim = simulus.simulator()
sim.process(setup, sim, NUM_MACHINES, WASHTIME, T_INTER)

# Execute!
sim.run(until=SIM_TIME)
