import simulus

from random import seed, expovariate, randint
seed(12345)

def generate():
    num = 0
    while True:
        sim.sleep(expovariate(1))
        print("%g: sent:" % sim.now, end=' ')
        for _ in range(randint(1,5)): # send a bunch
            print("%d" % num, end=' ')
            mb.send(num)
            num += 1
        print('')

def peek():
    msgs = mb.peek() # just peek at the mailbox
    if len(msgs) > 0:
        print("%g: peek() found:" % sim.now, end=' ')
        for m in msgs:
            print("%d" % m, end=' ')
        print('')
    else:
        print("%g: peek() found nothing" % sim.now)

def get_one():
    while True:
        sim.sleep(1)
        msg = mb.recv(isall=False)
        if msg is not None:
            print("%g: get_one() retrieved: %d" % (sim.now, msg))
        else:
            print("%g: get_one() retrieved nothing" % sim.now)

def get_all():
    while True:
        sim.sleep(5)
        msgs = mb.recv()
        if len(msgs) > 0:
            print("%g: get_all() retrieved:" % sim.now, end=' ')
            for m in msgs:
                print("%d" % m, end = ' ')
            print('')
        else:
            print("%g: get_all() retrieved nothing" % sim.now)

sim = simulus.simulator()
mb = sim.mailbox()
mb.add_callback(peek)
sim.process(generate)
sim.process(get_one)
sim.process(get_all)
sim.run(8)
