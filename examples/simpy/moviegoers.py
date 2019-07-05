"""This example is modified from the simpy's movie renege example; we
use the same settings as simpy so that we can get the same results."""

RANDOM_SEED = 42  # Random seed for repeatability
TICKETS = 50      # Number of tickets per movie
SIM_TIME = 120    # Simulation end time

import simulus
from random import seed, randint, choice, expovariate
from collections import namedtuple

def moviegoer(sim, movie, num_tickets, theater):
    """A moviegoer tries to buy a number of tickets (*num_tickets*) for a
    certain *movie* in a *theater*.

    If the movie becomes sold out, she leaves the theater. If she gets
    to the counter, she tries to buy a number of tickets. If not enough
    tickets are left, she argues with the teller and leaves.

    If at most one ticket is left after the moviegoer bought her
    tickets, the *sold out* event for this movie is triggered causing
    all remaining moviegoers to leave.

    """

    (_, has_sold_out), _ = sim.wait([theater.counter, theater.sold_out[movie]], method=any)
    if has_sold_out:
        # if movie ticket is sold out, renege from queue
        theater.num_renegers[movie] += 1
    else:
        # otherwise, the person finally gets to the counter
        if theater.available[movie] < num_tickets:
            # if not enough tickets left, moviegoer leaves, but only
            # after some serious arguments
            sim.sleep(0.5)
        else:
            # otherwise, just buy the tickets
            theater.available[movie] -= num_tickets
            if theater.available[movie] < 2: # shouldn't this be 1?
                # trigger the "sold out" for the movie
                theater.sold_out[movie].trigger()
                theater.when_sold_out[movie] = sim.now
                theater.available[movie] = 0

            # buying tickets takes time, you know...
            sim.sleep(1)

        # leave the counter
        theater.counter.release()

def customer_arrivals(sim, theater):
    """Create new *moviegoers*..."""

    while True:
        sim.sleep(expovariate(1 / 0.5))
        movie = choice(theater.movies)
        num_tickets = randint(1, 6)
        if theater.available[movie]:
            sim.process(moviegoer, sim, movie, num_tickets, theater)

# Setup and start the simulation
print('Movie renege')
seed(RANDOM_SEED)
sim = simulus.simulator()

# Create movie theater
Theater = namedtuple('Theater', 'counter, movies, available, '
                     'sold_out, when_sold_out, num_renegers')
counter = sim.resource(capacity=1)
movies = ['Python Unchained', 'Kill Process', 'Pulp Implementation']
available = {movie: TICKETS for movie in movies}
sold_out = {movie: sim.trap() for movie in movies}
when_sold_out = {movie: None for movie in movies}
num_renegers = {movie: 0 for movie in movies}
theater = Theater(counter, movies, available, sold_out,
                  when_sold_out, num_renegers)

# Start process and run
sim.process(customer_arrivals, sim, theater)
sim.run(until=SIM_TIME)

# Analysis/results
for movie in movies:
    if theater.sold_out[movie]:
        print('Movie "%s" sold out %.1f minutes after ticket counter '
              'opening.' % (movie, theater.when_sold_out[movie]))
        print('  Number of people leaving queue when film sold out: %s' %
              theater.num_renegers[movie])
