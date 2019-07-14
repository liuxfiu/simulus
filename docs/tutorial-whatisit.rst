What's Simulus?
---------------

Simulus is a process-oriented discrete-event simulator written in
Python. That's quite a mouthful. Let's first break it down what that
really means.

A discrete-event simulator models the world as a sequence of events
that happen in discrete time. The simulator basically processes these
events in order. Such a simulator would keep a simulation clock, which
advances its time (by leaps and bounds) in accordance with the time of
the events being processed along the way.

For example, a professor starts the day with a cup of coffee at 4 AM,
reads for 2 hours, has breakfast, takes shower, and then drives to
school at 7:30 AM. The discrete-event simulator for the professor's
day will go through a sequence of events: a "wake up" event at 4:00, a
"start coffee" event at 4:05, a "start read" event at 4:10, a "finish
coffee" event at 4:20, a "finish read" event at 6:10, a "breakfast"
event at 6:30, a "shower" event at 6:50, a "start driving" event at
7:30, so on and so forth. The clock of the simulator in this case will
go through a sequence of increasing values: 4:00, 4:05, 4:10, ... You
get the gist.

Discrete-event simulation is a very powerful modeling method. You can
think of the entire world, including the activities of the professors,
the students, and all other people, as a sequence of events that
happen over time. The simulator's job is to "play out" the events in
order. By doing so, we hopefully get better understanding of the
world.

Simulus is a "process-oriented" discrete-event simulator. What it
means is that in addition to describing the world as a sequence of
events, one can also model it using processes. As an example, suppose
the world consists of many professors, students, and
people. Previously we described the schedule of one professor. A
different person would have a different schedule and follow a
different sequence of events. Using process-oriented simulation, every
person in this system can be modeled as a separate process or
processes.

Note that people interact in this world. For example, if everyone
starts driving to school or to work in the morning at the same hour,
most may get delayed since congestion would happen on the road. Also,
if a student needs to meet with another student at a coffee shop. They
would not be able to carry on with their next task (say, to work on
their joint project) until both of them are present in the coffee
shop. Simulus provides the needed support for creating and managing
the processes, and having them coordinate with one another, so as to
make it easier for you to model the complexed interactions and
procedures in this world.
