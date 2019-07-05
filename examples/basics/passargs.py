import simulus

def print_params_1(a, b, c="named"):
    print("print_params_1(a=%r, b=%r, c=%r) invoked at time %g" %
          (a, b, c, sim.now))

def print_params_2(mysim, a, b, *args, c="named", **kwargs):
    print("print_params_2(a=%r, b=%r, args=%r, c=%r, kwargs=%r) invoked at time %g" %
          (a, b, args, c, kwargs, mysim.now))

class myclass:
    def __init__(self, a):
        self.a = a

    def print_params_3(self, b, c):
        print("print_params_3(a=%r, b=%r, c=%r) invoked at %g" %
              (self.a, b, c, sim.now))
    
sim = simulus.simulator()
sim.sched(print_params_1, "hello", 100, until=10)
sim.sched(print_params_2, sim, "hello", 100, "yes", "no", arg1=True, arg2=2, c=1, until=20)
cls = myclass(10)
sim.sched(myclass.print_params_3, cls, 11, 12, until=30)
sim.run()
