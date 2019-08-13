import simulus

from functools import partial
print = partial(print, flush=True)

def p(sim, idx, mbox):
    while True:
        msg = mbox.recv(isall=False)
        print("%g: '%s' rcvd msg '%s'" % (sim.now, sim.name, msg))
        sim.sync().send(sim, 'mb%d'% ((idx+1)%nnodes), msg)
        
nnodes = 15
sims = []
for i in range(nnodes):
    sim = simulus.simulator('sim%d'%i)
    sims.append(sim)
    mbox = sim.mailbox('mb%d'%i, 1)
    sim.process(p, sim, i, mbox)

g = simulus.sync(sims, enable_smp=True)
g.send(sims[0], 'mb0', 'hello') # send initial message to start circulation
g.run(10)
g.run(5, show_runtime_report=True)
