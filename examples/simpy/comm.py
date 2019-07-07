"""This example is modified from the simpy's process communication
example; we use the same settings as simpy so that we can get the same
results."""

import random, simulus

RANDOM_SEED = 42
SIM_TIME = 100

class BroadcastPipe(object):
    """A Broadcast pipe that allows one process to send messages to many.

    This construct is useful when message consumers are running at
    different rates than message generators and provides an event
    buffering to the consuming processes.

    """
    
    def __init__(self, sim, capacity=float('inf')):
        self.sim = sim
        self.capacity = capacity
        self.pipes = []

    def put(self, obj):
        """Broadcast a *value* to all receivers."""
        if not self.pipes:
            raise RuntimeError('There are no output pipes.')
        events = [store.putter(obj=obj) for store in self.pipes]
        self.sim.wait(events, method=all)

    def get_output_conn(self):
        """Get a new output connection for this broadcast pipe."""
        pipe = self.sim.store(self.capacity)
        self.pipes.append(pipe)
        return pipe

def message_generator(name, sim, out_pipe):
    """A process which randomly generates messages."""
    while True:
        # wait for next transmission
        sim.sleep(random.randint(6, 10))

        # messages are time stamped to later check if the consumer was
        # late getting them.  Note, using event.triggered to do this may
        # result in failure due to FIFO nature of simulation yields.
        # (i.e. if at the same sim.now, message_generator puts a message
        # in the pipe first and then message_consumer gets from pipe,
        # the event.triggered will be True in the other order it will be
        # False
        msg = (sim.now, '%s says hello at %d' % (name, sim.now))
        out_pipe.put(obj=msg)

def message_consumer(name, sim, in_pipe):
    """A process which consumes messages."""
    while True:
        # Get event for message pipe
        msg = in_pipe.get()

        if msg[0] < sim.now:
            # if message was already put into pipe, then
            # message_consumer was late getting to it. Depending on what
            # is being modeled this, may, or may not have some
            # significance
            print('LATE Getting Message: at time %d: %s received message: %s' %
                  (sim.now, name, msg[1]))

        else:
            # message_consumer is synchronized with message_generator
            print('at time %d: %s received message: %s.' %
                  (sim.now, name, msg[1]))

        # Process does some other work, which may result in missing messages
        sim.sleep(random.randint(4, 8))

# Setup and start the simulation
print('Process communication')
random.seed(RANDOM_SEED)
sim = simulus.simulator()

# For one-to-one or many-to-one type pipes, use Store
pipe = sim.store()
sim.process(message_generator, 'Generator A', sim, pipe)
sim.process(message_consumer, 'Consumer A', sim, pipe)

print('\nOne-to-one pipe communication\n')
sim.run(until=SIM_TIME)

# For one-to many use BroadcastPipe
# (Note: could also be used for one-to-one,many-to-one or many-to-many)
sim = simulus.simulator()
bc_pipe = BroadcastPipe(sim)

sim.process(message_generator, 'Generator A', sim, bc_pipe)
sim.process(message_consumer, 'Consumer A', sim, bc_pipe.get_output_conn())
sim.process(message_consumer, 'Consumer B', sim, bc_pipe.get_output_conn())

print('\nOne-to-many pipe communication\n')
sim.run(until=SIM_TIME)
