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
        
        # the mailman sort the mails in the moring and only start to
        # get out deliver the mails at 2 PM
        sim.sleep(until=day*24*3600+14*3600)

        # it may take variable amount of time (between 1 to 5 hours)
        # before the mails can be delivered to the mailbox
        delay = randint(3600, 5*3600)
        mb.send('letter for day %d' % day, delay)

        print("%s: mail truck's out, expected delivery at %s" %
              (strnow(), strnow(sim.now+delay)))

        # go to the next day
        day += 1

def receiver():
    day = 0
    while True:
        # come back from work at 5 PM
        sim.sleep(until=day*24*3600+17*3600)
        
        # wait for to check the mailbox within an hour
        _, timedout = sim.wait(mb, 3600)
        if timedout:
            print("%s: mail truck didn't come today" % strnow())
        else:
            for ltr in mb.retval:
                print("%s: receives '%s'" % (strnow(), ltr))

        # go to the next day
        day += 1
        
seed(12345)

sim = simulus.simulator()
mb = sim.mailbox()

sim.process(mailman)
sim.process(receiver)

sim.run(10*24*3600)
