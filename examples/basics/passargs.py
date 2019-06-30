import simulus

def print_params(s, x):
    print("print_params() invoked at time "+str(s.now))
    print("  with msg:", x.get('msg', "hey, how can you forget the message?"))
    print("  all arguments:", x)
    
sim = simulus.simulator()
sim.sched(print_params, until=10, msg="hello", var=False)
sim.sched(print_params, until=20, arg1="here", params={"arg1":10, "arg2":"be good"})
sim.run()
