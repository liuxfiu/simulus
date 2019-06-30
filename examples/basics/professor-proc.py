import simulus

from time import gmtime, strftime
def nowstr(sim):
    return strftime("%H:%M:%S", gmtime(sim.now))

def prof_life(sim, params):
    while True:
        start_of_the_day = sim.now
        
        sim.sleep(4*3600) # 4 hours from midnight
        print("professor wakes up at "+nowstr(sim))
        
        sim.sleep(offset=5*60) # 5 minutes from now
        print("professor starts drinking coffee at "+nowstr(sim))
    
        sim.sleep(offset=5*60) # 5 minutes from now
        print("professor starts reading at "+nowstr(sim))

        sim.sleep(offset=(15-5)*60) # 15 minus 5 minutes from now
        print("professor finishes drinking coffee at "+nowstr(sim))

        sim.sleep(offset=2*3600-10*60) # 2 hours minus 10 minutes from now
        print("professor finishes reading at "+nowstr(sim))

        sim.sleep(until=start_of_the_day+6*3600+30*60) # 6:30
        print("professor breakfasts at "+nowstr(sim))
        
        sim.sleep(until=start_of_the_day+6*3600+50*60) # 6:50
        print("professor showers at "+nowstr(sim))

        sim.sleep(until=start_of_the_day+7*3600+30*60) # 7:30
        print("professor leaves home and drives to school at "+nowstr(sim))

        if sim.now < 24*3600:
            # traffic jam at the first day
            sim.sleep(offset=2*3600+45*60) # 2 hours and 45 minutes from now
            print("professor arrives at school at "+nowstr(sim))

            if sim.now < 9*3600:
                # if arrives before the 9 o'clock, attend both meetings
                sim.sleep(until=9*3600)
                print("professor has first meeting at "+nowstr(sim))

                sim.sleep(until=10*3600)
                print("professor has second meeting at "+nowstr(sim))
            else:
                # if late, no the first meeting and resched the second
                sim.sleep(until=11*3600)
                print("professor has second meeting at "+nowstr(sim))
        else:
            # no traffic jam in the following days
            sim.sleep(offset=45*60) # 45 minutes from now
            print("professor arrives at school at "+nowstr(sim))

        # the rest of the day is a blur for the professor
        rest_of_the_day(sim, start_of_the_day)

def rest_of_the_day(sim, start):
    # sleep until the start of the next day
    sim.sleep(until=start+24*3600)
            
sim = simulus.simulator()
sim.process(prof_life) 
sim.run(until=72*3600)
