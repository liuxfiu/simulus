import numpy as np

from random import seed, expovariate, gauss
seed(12345)

x = np.array([expovariate(1/0.5) for i in range(1000)])
print("x: sample mean=%g, stdev=%g" % (x.mean(), x.std()))

y = np.array([expovariate(1/10.0) for i in range(1000)])
print("y: sample mean=%g, stdev=%g" % (y.mean(), y.std()))

z = np.array([gauss(1.5, 6.5) for i in range(1000)])
print("z: sample mean=%g, stdev=%g" % (z.mean(), z.std()))
