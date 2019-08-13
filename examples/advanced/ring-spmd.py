import simulus

from functools import partial
print = partial(print, flush=True)

rank = simulus.sync.comm_rank()
psize = simulus.sync.comm_size()

def p(sim, idx, mbox):
    while True:
        msg = mbox.recv(isall=False)
        print("%g: '%s' rcvd msg '%s'" % (sim.now, sim.name, msg))
        sim.sync().send(sim, 'mb%d'% ((idx+1)%nnodes), msg)
        
nnodes = 15
sims = []
for i in range(rank, nnodes, psize):
    sim = simulus.simulator('sim%d'%i)
    sims.append(sim)
    mbox = sim.mailbox('mb%d'%i, 1)
    sim.process(p, sim, i, mbox)

g = simulus.sync(sims, enable_spmd=True)

if rank > 0: 
    g.run()
else:
    g.send(sims[0], 'mb0', 'hello') # send initial message to start circulation
    g.run(5)
    g.run(10, show_runtime_report=True)
