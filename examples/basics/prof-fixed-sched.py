import simulus

from time import gmtime, strftime
def nowstr(sim):
    return strftime("%H:%M:%S", gmtime(sim.now))

def wake_up(sim, params):
    print("professor wakes up at "+nowstr(sim))
    sim.sched(start_coffee, offset=5*60) # 5 minutes from now
    sim.sched(breakfast, offset=2*3600+30*60) # 2 hours and 30 minutes from now
    sim.sched(shower, offset=2*3600+50*60) # 2 hours and 50 minutes from now
    sim.sched(leave, offset=3*3600+30*60) # 3 hours and 30 minutes from now
    
def start_coffee(sim, params):
    print("professor starts drinking coffee at "+nowstr(sim))
    sim.sched(finish_coffee, offset=15*60) # 15 minutes from now
    sim.sched(start_read, offset=5*60) # 5 minutes from now

def finish_coffee(sim, params):
    print("professor finishes drinking coffee at "+nowstr(sim))
    
def start_read(sim, params):
    print("professor starts reading at "+nowstr(sim))
    sim.sched(finish_read, offset=2*3600) # 2 hours from now
    
def finish_read(sim, params):
    print("professor finishes reading at "+nowstr(sim))

def breakfast(sim, params):
    print("professor breakfasts at "+nowstr(sim))

def shower(sim, params):
    print("professor shows at "+nowstr(sim))

def leave(sim, params):
    print("professor leaves home and drives to school at "+nowstr(sim))
    sim.sched(arrive, offset=45*60) # 45 minutes from now

def arrive(sim, params):
    print("professor arrives at school at "+nowstr(sim))

def meeting1(sim, params):
    print("professor has first meeting at "+nowstr(sim))

def meeting2(sim, params):
    print("professor has second meeting at "+nowstr(sim))

sim = simulus.simulator()
sim.sched(wake_up, until=4*3600) # 4:00
sim.sched(meeting1, until=9*3600) # 9:00
sim.sched(meeting2, until=10*3600) # 10:00
sim.run()
