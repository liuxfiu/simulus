import simulus

from random import seed, expovariate, randrange
seed(12345)

job_count = 5
node_count = 4
lookahead = 1

def generate(idx):
    while True:
        msg = mb[idx].recv(isall=False)
        print("%g: node %d received job[%d]," % (sim.now, idx, msg), end=' ')
        target = randrange(node_count)
        delay = expovariate(1)+lookahead
        mb[target].send(msg, delay)
        print("sent to node %d with delay %g" % (target, delay))

sim = simulus.simulator()

mb = [sim.mailbox() for _ in range(node_count)]
for idx in range(node_count):
    sim.process(generate, idx)

# disperse the initial jobs
for idx in range(job_count):
    target = randrange(node_count)
    delay = expovariate(1)+lookahead
    mb[target].send(idx, delay)
    print("init sent job[%d] to node %d with delay %g" %
          (idx, target, delay))

sim.run(5)
