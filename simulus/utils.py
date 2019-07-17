# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-17 06:29:29 liux>
###############################################################

import math, re

__all__ = ["QDIS", 'WelfordStats', "TimeMarks", "DataSeries", "TimeSeries", "DataCollector"]

class QDIS:
    """Queuing disciplines used by semaphores and resources."""
    FIFO        = 0  # first in first out
    LIFO        = 1  # last in first out
    SIRO        = 2  # service in random order
    PRIORITY    = 3  # priority based

class WelfordStats(object):
    """Welford's one-pass algorithm to get simple statistics (including
    the mean and variance) from a series of data."""
    
    def __init__(self):
        self._n = 0
        self._mean = 0.0
        self._varsum = 0.0
        self._max = float('-inf')
        self._min = float('inf')

    def __len__(self): return self._n
    
    def push(self, x):
        """Add data to the series."""
        self._n += 1
        if x > self._max: self._max = x
        if x < self._min: self._min = x
        d = x-self._mean
        self._varsum += d*d*(self._n-1)/self._n
        self._mean += d/self._n
        
    def min(self): return self._min
    def max(self): return self._max
    def mean(self): return self._mean    
    def stdev(self): return math.sqrt(self._varsum/self._n)
    def var(self): return self._varsum/self._n

class TimeMarks(object):
    """A series of (increasing) time instances."""
    
    def __init__(self, keep_data=False):
        if keep_data: self._data = []
        else: self._data = None
        self._n = 0
        
    def __len__(self):
        """Return the number of collected samples."""
        return self._n

    def _push(self, t):
        if self._n == 0:
            self._last = t
        elif t < self._last:
            raise ValueError("TimeMarks._push(%g) earlier than last entry (%g)" %
                             (t, self._last)) 
        if self._data is not None:
            self._data.append(t)
        self._n += 1
        self._last = t

    def data(self):
        """Return all samples if keep_data has been set when the timemarks was
        initialized; otherwise, return None."""
        return self._data
    
    def rate(self, t=None):
        """Return the arrival rate, which is the averge number of sameples up
        to the given time. If t is ignored, it's up to the time of the
        last entry."""
        if self._n > 0:
            if t is None: t = self._last
            elif t < self._last:
                raise ValueError("TimeMarks.rate(t=%g) earlier than last entry (%g)" %
                                 (t, self._last))
            return self._n/t
        else:
            return 0

class DataSeries(object):
    """A series of numbers."""
    
    def __init__(self, keep_data=False):
        if keep_data: self._data = []
        else: self._data = None
        self._rs = WelfordStats()
        
    def __len__(self):
        """Return the number of collected samples."""
        return len(self._rs)

    def _push(self, d):
        if self._data is not None:
            self._data.append(d)
        self._rs.push(d)

    def data(self):
        """Return all samples if keep_data has been set when the dataseries
        has been initialized; otherwise, return None."""
        return self._data

    def mean(self):
        """Return the sample mean."""
        if len(self._rs) > 0: return self._rs.mean()
        else: return 0
    
    def stdev(self):
        """Return the sample standard deviation."""
        if len(self._rs) > 1: return self._rs.stdev()
        else: return float('inf')

    def var(self):
        """Return the sample variance."""
        if len(self._rs) > 1: return self._rs.var()
        else: return float('inf')

    def min(self):
        """Return the minimum of all samples."""
        if len(self._rs) > 0: return self._rs.min()
        else: return float('-inf')

    def max(self):
        """Return the maximum of all samples."""
        if len(self._rs) > 0: return self._rs.max()
        else: return float('inf')

class TimeSeries(object):
    """A series of time-value pairs."""
    
    def __init__(self, keep_data=False):
        if keep_data: self._data = []
        else: self._data = None
        self._rs = WelfordStats()
        self._area = 0

    def __len__(self):
        """Return the number of collected samples."""
        return len(self._rs)
    
    def _push(self, d):
        t, v = d
        if len(self._rs) == 0:
            self._last_t = t
            self._last_v = v
        elif t < self._last_t:
            raise ValueError("TimeSeries._push(%r) earlier than last entry (%g)" %
                             (d, self._last_t))

        if self._data is not None:
            self._data.append(d)
        self._rs.push(v)
        self._area += (t-self._last_t)*self._last_v
        self._last_t = t
        self._last_v = v
                
    def data(self):
        """Return all samples if keep_data has been set when the timeseries
        was initialized; otherwise, return None."""
        return self._data
    
    def rate(self, t=None):
        """Return the arrival rate, which is the averge number of samples up
        to the given time. If t is ignored, it's up to the time of the
        last entry."""
        if len(self._rs) > 0:
            if t is None: t = self._last_t
            elif t < self._last_t:
                raise ValueError("TimeSeries.rate(t=%g) earlier than last entry (%g)" %
                                 (t, self._last_t))
            return len(self._rs)/t
        else:
            return 0

    def mean(self):
        """Return the sample mean."""
        if len(self._rs) > 0: return self._rs.mean()
        else: return 0
    
    def stdev(self):
        """Return the sample standard deviation."""
        if len(self._rs) > 1: return self._rs.stdev()
        else: return float('inf')

    def var(self):
        """Return the sample variance."""
        if len(self._rs) > 1: return self._rs.var()
        else: return float('inf')

    def min(self):
        """Return the minimum of all samples."""
        if len(self._rs) > 0: return self._rs.min()
        else: return float('-inf')

    def max(self):
        """Return the maximum of all samples."""
        if len(self._rs) > 0: return self._rs.max()
        else: return float('inf')

    def avg_over_time(self, t=None):
        """Return the average value over time. If t is ignored, it's the
        average up to the time of the last entry."""
        if len(self._rs) > 0:
            if t is None: t = self._last_t
            if t < self._last_t:
                raise ValueError("TimeSeries.avg_over_time(t=%g) earlier than last entry (%g)" %
                                 (t, self._last_t))
            return (self._area+(t-self._last_t)*self._last_v)/t
        else:
            return 0

class DataCollector(object):
    """Statistics collection for resources, stores, and mailboxes."""

    def __init__(self, **kwargs):
        """Initialize the data collector. kwargs is the keyworded arguments;
        it's a dictionary containing all attributes allowed to be
        collected at the corresponding resource or facility."""
        self._attrs = kwargs
        patterns = {
            re.compile(r'timemarks\s*(\(\s*(all)?\s*\))?') : TimeMarks,
            re.compile(r'dataseries\s*(\(\s*(all)?\s*\))?') : DataSeries,
            re.compile(r'timeseries\s*(\(\s*(all)?\s*\))?') : TimeSeries
        }
        for k, v in self._attrs.items():
            if hasattr(self, k):
                raise ValueError("DataCollector attribute %s already exists" % k)
            for pat, cls in patterns.items():
                m = pat.match(v)
                if m is not None:
                    if m.group(2): v = cls(True)
                    else: v = cls(False)
                    setattr(self, k, v)
                    self._attrs[k] = v
                    break
            else:
                raise ValueError("DataCollector() %r has unknown value (%r)" % k, v)

    def _sample(self, k, v):
        if k in self._attrs:
            getattr(self, k)._push(v)

    def report(self, t=None):
        """Print out the collected statistics nicely. If t is provided, it's
        expected to the the simulation end time; if t is ignored, the
        statistics are up to the time of the last sample."""
        
        for k, v in self._attrs.items():
            if isinstance(v, TimeMarks):
                print("%s (timemarks): samples=%d" % (k, len(v)))
                if len(v) > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print('  rate = %g' % v.rate(t))
            elif isinstance(v, DataSeries):
                print("%s (dataseries): samples=%d" % (k, len(v)))
                if len(v) > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print('  mean = %g' % v.mean())
                    if len(v) > 1:
                        print('  stdev = %g' % v.stdev())
                        print('  var = %g' % v.var())
                    print('  min = %g' % v.min())
                    print('  max = %g' % v.max())
            elif isinstance(v, TimeSeries):
                print("%s (timeseries): samples=%d" % (k, len(v)))
                if len(v) > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print('  rate = %g' % v.rate(t))
                    print('  mean = %g' % v.mean())
                    if len(v) > 1:
                        print('  stdev = %g' % v.stdev())
                        print('  var = %g' % v.var())
                    print('  min = %g' % v.min())
                    print('  max = %g' % v.max())
                    print("  avg_over_time=%g" % v.avg_over_time(t))
