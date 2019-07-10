from time import gmtime, strftime
from random import seed, randint
import simulus

def strnow(t=None):
    if not t: t = sim.now
    return strftime("%H:%M", gmtime(t))

def mailman():
    day = 0
    while True:
        sim.sleep(until=day*24*3600+8*3600) # 8 o'clock
        print('--- day %d ---' % day)
        
        # sort the mails in the moring and get out for delivery at 2
        # o'clock in the afternoon
        sim.sleep(until=day*24*3600+14*3600)

        # it may take variable amount of time (between 1 to 5 hours)
        # before the mails can be delivered to people's mailboxes
        delay = randint(3600, 5*3600)
        mb.send('letter for day %d' % day, delay)
        print("%s mail truck's out, expected delivery at %s" %
              (strnow(), strnow(sim.now+delay)))

        # go to the next day
        day += 1

def patron():
    day = 0
    while True:
        # come back from work at 5 PM
        sim.sleep(until=day*24*3600+17*3600)
        
        # check the mailbox within an hour (until 6 PM)
        rcv = mb.receiver()
        _, timedout = sim.wait(rcv, 3600)
        if timedout:
            print("%s mail truck didn't come today" % strnow())
        else:
            for ltr in rcv.retval:
                print("%s receives '%s'" % (strnow(), ltr))

        # go to the next day
        day += 1
        
seed(12345)

sim = simulus.simulator()
mb = sim.mailbox()

sim.process(mailman)
sim.process(patron)

sim.run(5*24*3600)
