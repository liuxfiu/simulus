"""This example is modified from the simpy's gas station refueling
example; we use the same settings as simpy so that we can get the same
results."""

RANDOM_SEED = 42           # random seed for repeatability
GAS_STATION_SIZE = 200     # liters
THRESHOLD = 10             # Threshold for calling the tank truck (in %)
FUEL_TANK_SIZE = 50        # liters
FUEL_TANK_LEVEL = [5, 25]  # Min/max levels of fuel tanks (in liters)
REFUELING_SPEED = 2        # liters / second
TANK_TRUCK_TIME = 300      # Seconds it takes the tank truck to arrive
T_INTER = [30, 300]        # Create a car every [min, max] seconds
SIM_TIME = 1000            # Simulation time in seconds

import random, itertools
import simulus

def car_generator(sim, gas_station, fuel_pump):
    """Generate new cars that arrive at the gas station."""
    for i in itertools.count():
        sim.sleep(random.randint(*T_INTER))
        sim.process(car, 'Car %d' % i, sim, gas_station, fuel_pump)

def car(name, sim, gas_station, fuel_pump):
    """A car arrives at the gas station for refueling.

    It requests one of the gas station's fuel pumps and tries to get
    the desired amount of gas from it. If the stations reservoir is
    depleted, the car has to wait for the tank truck to arrive.

    """
    
    fuel_tank_level = random.randint(*FUEL_TANK_LEVEL)
    print('%s arriving at gas station at %.1f' % (name, sim.now))

    start = sim.now
    # Request one of the gas pumps
    gas_station.acquire()

    # Get the required amount of fuel
    liters_required = FUEL_TANK_SIZE - fuel_tank_level
    fuel_pump.get(liters_required)

    # The "actual" refueling process takes some time
    sim.sleep(liters_required / REFUELING_SPEED)

    gas_station.release()
    print('%s finished refueling in %.1f seconds.' %
          (name, sim.now - start))

def gas_station_control(sim, fuel_pump):
    """Periodically check the level of the *fuel_pump* and call the tank
    truck if the level falls below a threshold."""

    while True:
        if fuel_pump.level / fuel_pump.capacity * 100 < THRESHOLD:
            # We need to call the tank truck now!
            print('Calling tank truck at %d' % sim.now)

            # Wait for the tank truck to arrive and refuel the station
            sim.wait(sim.process(tank_truck, sim, fuel_pump))

        sim.sleep(10)  # Check every 10 seconds

def tank_truck(sim, fuel_pump):
    """Arrives at the gas station after a certain delay and refuels it."""
    
    sim.sleep(TANK_TRUCK_TIME)
    print('Tank truck arriving at time %d' % sim.now)
    
    ammount = fuel_pump.capacity - fuel_pump.level
    print('Tank truck refuelling %.1f liters.' % ammount)
    fuel_pump.put(ammount)

# Setup and start the simulation
print('Gas Station refuelling')
random.seed(RANDOM_SEED)

# Create simulator and start processes
sim = simulus.simulator()
gas_station = sim.resource(2)
fuel_pump = sim.store(GAS_STATION_SIZE, GAS_STATION_SIZE)
sim.process(gas_station_control, sim, fuel_pump)
sim.process(car_generator, sim, gas_station, fuel_pump)

# Execute!
sim.run(until=SIM_TIME)
