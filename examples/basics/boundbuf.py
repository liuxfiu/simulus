import simulus

from random import seed, expovariate, gauss
seed(12345)

bufsiz = 5 # buffer capacity
items_produced = 0 # keep track the number of items produced
items_consumed = 0 # ... and consumed
num_producers = 2 # number of producers
num_consumers = 3 # number of consumers

def producer(sim, params):
    global items_produced
    idx = params['idx']
    while True:
        sim.sleep(expovariate(1)) # take time to produce an item
        num = items_produced
        items_produced += 1
        print("%f: p[%d] produces item [%d]" % (sim.now, idx, num))
        sem_avail.wait() # require a free slot in buffer
        sem_occupy.signal() # store the item and increase occupancy
        print("%f: p[%d] stores item [%d] in buffer" % 
              (sim.now, idx, num))
        
def consumer(sim, params):
    global items_consumed
    idx = params['idx']
    while True:
        sem_occupy.wait() # require an item from buffer
        sem_avail.signal() # retrieve the item and bump the free slots
        num = items_consumed
        items_consumed += 1
        print("%f: c[%d] retrieves item [%d] from buffer" %
              (sim.now, idx, num))
        sim.sleep(gauss(0.8, 0.2)) # take time to consume the item
        print("%f: c[%d] consumes item[%d]" % (sim.now, idx, num))        

sim = simulus.simulator()
sem_avail = sim.semaphore(bufsiz) # available slots
sem_occupy = sim.semaphore(0) # no items yet
for i in range(num_producers): 
    sim.process(producer, idx=i)
for i in range(num_consumers):
    sim.process(consumer, idx=i)
sim.run(10)
