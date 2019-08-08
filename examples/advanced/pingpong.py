import simulus

def p(g, sim, mbox, mbname):
    while True:
        msg = mbox.recv(isall=False)
        print("%g: '%s' rcvd msg '%s'" % (sim.now, sim.name, msg))
        g.send(sim, mbname, 'pong' if msg=='ping' else 'ping')
        
sim1 = simulus.simulator('sim1')
mb1 = sim1.mailbox('mb1', 1)
mb1.send('ping') # send initial message to start ping-ponging

sim2 = simulus.simulator('sim2')
mb2 = sim2.mailbox('mb2', 1)

g = simulus.sync([sim1, sim2])
sim1.process(p, g, sim1, mb1, 'mb2')
sim2.process(p, g, sim2, mb2, 'mb1')

g.run(10)
