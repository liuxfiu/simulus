import simulus

from random import seed, expovariate, gauss
seed(12345)

bufsiz = 5 # buffer capacity
items_produced = 0 # keep track the number of items produced
num_producers = 2 # number of producers
num_consumers = 3 # number of consumers

def producer(idx):
    global items_produced
    while True:
        sim.sleep(expovariate(1)) # take time to produce an item
        num = items_produced
        items_produced += 1
        print("%f: p[%d] produces item [%d]" % (sim.now, idx, num))
        s.put(obj=num)
        print("%f: p[%d] stores item [%d] in buffer" % 
              (sim.now, idx, num))
        
def consumer(idx):
    while True:
        num = s.get()
        print("%f: c[%d] retrieves item [%d] from buffer" %
              (sim.now, idx, num))
        sim.sleep(gauss(0.8, 0.2)) # take time to consume the item
        print("%f: c[%d] consumes item[%d]" % (sim.now, idx, num))        

sim = simulus.simulator()
s = sim.store(capacity=bufsiz)
for i in range(num_producers): 
    sim.process(producer, i)
for i in range(num_consumers):
    sim.process(consumer, i)
sim.run(10)
