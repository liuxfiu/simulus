# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-06 06:06:16 liux>
###############################################################

# runstats must be installed as additional python package
from runstats import Statistics

__all__ = ["QDIS", "DataCollector"]

class QDIS:
    """Queuing disciplines used by semaphores and resources."""
    FIFO        = 0
    LIFO        = 1
    RANDOM      = 2
    PRIORITY    = 3

class DataCollector:
    """Collect data and statistics for resources and facilities."""

    def __init__(self, params=None, **kargs):
        # consolidate arguments
        if params is None:
            params = kargs
        else:
            try:
                params.update(kargs)
            except AttributeError:
                raise TypeError("DataCollector() params not a dictionary");
        self.params = params

        for k, v in self.params.items():
            if 'all' == v:
                # a list of all samples
                setattr(self, k+'_all', [])
            elif 'sum' == v:
                # running statistics
                setattr(self, k+'_sum', Statistics())
            elif 'cnt' == v:
                # counting the number so far
                setattr(self, k+'_cnt', 0)
            elif 'acc' == v:
                # accumulating area under value over time
                setattr(self, k+'_acc', 0)
                setattr(self, k+'_acc_t', 0)
                setattr(self, k+'_acc_v', 0)
            else:
                raise ValueError("DataCollector() unknown value type (%s)" % v)

    def sample(self, k, v):
        if k in self.params:
            if 'all' == self.params[k]:
                getattr(self, k+'_all').append(v)
            elif 'sum' == self.params[k]:
                getattr(self, k+'_sum').push(v)
            elif 'cnt' == self.params[k]:
                n1 = k+'_cnt'
                x = getattr(self, n1) + 1
                setattr(self, n1, x)
            elif 'acc' == self.params[k]:
                n1, n2, n3 = k+'_acc', k+'_acc_t', k+'_acc_v'
                x = getattr(self, n1) + (v[0]-getattr(self, n2))*getattr(self, n3)
                setattr(self, n1, x)
                setattr(self, n2,  v[0])
                setattr(self, n3,  v[1])

    def finalize(self, time):
        for k, v in self.params.items():
            if 'all' == v:
                pass
            elif 'sum' == v:
                pass
            elif 'cnt' == v:
                n1, n2 = k+'_cnt', k+'_rate'
                x = getattr(self, n1)
                setattr(self, n2, x/time)
            elif 'acc' == v:
                n1, n2, n3 = k+'_acc', k+'_acc_t', k+'_acc_v'
                x = getattr(self, n1) + (time-getattr(self, n2))*getattr(self, n3)
                setattr(self, n1, x)
                setattr(self, n2, time)
                setattr(self, k+'_avg', x/time)

    def report(self):
        for k, v in self.params.items():
            if 'all' == v:
                print("%s all samples = %r" % (k, getattr(self, k+'_all')))
            elif 'sum' == v:
                rs = getattr(self, k+'_sum')
                if len(rs) > 0:
                    print(k+' summary:')
                    print('  mean = %g' % rs.mean())
                    print('  stdev = %g' % rs.stddev())
                    print('  var = %g' % rs.variance())
                    print('  min = %g' % rs.minimum())
                    print('  max = %g' % rs.maximum())
                else:
                    print(k+': no samples')
            elif 'cnt' == v:
                print("%s rate = %r" % (k, getattr(self, k+'_rate')))
            elif 'acc' == v:
                print("%s avg = %r" % (k, getattr(self, k+'_avg')))
