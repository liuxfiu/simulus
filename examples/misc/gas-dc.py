import itertools, random, simulus

GAS_STATION_SIZE = 2000    # gas station reservoir size
GAS_PUMPS = 10             # number of gas pumps
REFUEL_THRESHOLD = 25      # min reservoir level (in %) before calling the tank truck
FUEL_TANK_SIZE = 50        # car's fuel task size
FUEL_TANK_LEVEL = [1, 15]  # min/max tank level before refueling
REFUELING_SPEED = 2        # speed of the pump
TANK_TRUCK_TIME = 300      # tank truck travel time
INTER_ARRIVAL = 5          # inter-arrival time of cars

def car_generator(sim, gas_station, fuel_pump):
    for i in itertools.count():
        sim.sleep(random.expovariate(1.0/INTER_ARRIVAL))
        sim.process(car, sim, gas_station, fuel_pump)

def car(sim, gas_station, fuel_pump):
    fuel_tank_level = random.randint(*FUEL_TANK_LEVEL)
    gas_station.acquire() # dumb wait
    liters_required = FUEL_TANK_SIZE - fuel_tank_level
    fuel_pump.get(liters_required) # another dumb wait
    sim.sleep(liters_required / REFUELING_SPEED)
    gas_station.release()

def gas_station_control(sim, fuel_pump):
    while True:
        if fuel_pump.level/fuel_pump.capacity*100 < REFUEL_THRESHOLD:
            sim.wait(sim.process(tank_truck, sim, fuel_pump))
        sim.sleep(10)  # check every 10 seconds

def tank_truck(sim, fuel_pump):
    sim.sleep(random.expovariate(1.0/TANK_TRUCK_TIME))
    amt = fuel_pump.capacity - fuel_pump.level
    fuel_pump.put(amt)

random.seed(123)
sim = simulus.simulator()
gas_station = sim.resource(GAS_PUMPS)
dc = simulus.DataCollector(levels='timeseries(all)')
fuel_pump = sim.store(GAS_STATION_SIZE, GAS_STATION_SIZE, collect=dc)
sim.process(gas_station_control, sim, fuel_pump)
sim.process(car_generator, sim, gas_station, fuel_pump)
sim.run(until=1000)
dc.report(sim.now)
