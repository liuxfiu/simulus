import simulus

from random import seed, expovariate
seed(12345)

def bcast():
    num = 0
    while True:
        sim.sleep(expovariate(1))
        print("%g: send %d" % (sim.now, num))
        mb.send(num)
        num += 1

def func(idx):
    msgs = mb.check()
    if len(msgs) > 0:
        for m in msgs:
            print("%g: func(%d) checked %d" % (sim.now, idx, m))
    else:
        print("%g: func(%d) checked nothing" % (sim.now, idx))

def proc(idx):
    while True:
        msgs = mb.recv()
        if len(msgs) > 0:
            for m in msgs:
                print("%g: proc(%d) got %d" % (sim.now, idx, m))
        else:
            print("%g: proc(%d) got nothing" % (sim.now, idx))
                

sim = simulus.simulator()
mb = sim.mailbox()
mb.add_callback(func, 0)
mb.add_callback(func, 1)

sim.process(bcast)
sim.process(proc, 2)
sim.process(proc, 3)
sim.run(10)
