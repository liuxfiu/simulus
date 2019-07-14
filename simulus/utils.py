# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on July 2, 2019
# Last Update: Time-stamp: <2019-07-14 17:48:25 liux>
###############################################################

# runstats must be installed as additional python package
import runstats
import re

__all__ = ["QDIS", "DataCollector", "TimeSeries", "RunStats", "TimeMarks"]

class QDIS:
    """Queuing disciplines used by semaphores and resources."""
    FIFO        = 0
    LIFO        = 1
    RANDOM      = 2
    PRIORITY    = 3

class TimeSeries(object):
    """A series of time-value pairs."""
    
    def __init__(self, keep_data=False):
        if keep_data: self.d = []
        else: self.d = None
        self.n = 0
        self.a = 0

    def _push(self, d):
        t, v = d
        #print("push: t=%g, v=%d" % d)
        if self.n == 0:
            # the very first entry
            if self.d is not None:
                self.d.append((t,v))
            self.t = t
            self.v = v
            self.n = 1
        elif t > self.t:
            # if it's time in the future, whether or not the value is
            # the same, we enter a new entry
            if self.d is not None:
                self.d.append((t,v))
            self.n += 1
            self.a += (t-self.t)*self.v
            self.t = t
            self.v = v
        elif t == self.t:
            # if it's current time (same as previous entry)
            if v != self.v:
                # if the value is not the same, we update entry in place
                self.v = v
                if self.d is not None:
                    self.d[-1] = (t, v)
            else:
                # if time and value are the same, ignore
                pass
        else:
            raise ValueError("TimeSeries._push(%r) earlier than last entry (%g)" %
                             (d, self.t))
                
    def num(self):
        """Return the number of collected samples."""
        return self.n
    
    def data(self):
        """Return all samples if keep_data was set when intializing the
        timeseries; otherwise, return None."""
        return self.d
    
    def avg(self, t):
        """Return the average value up to the given time."""
        if self.n > 0:
            if t < self.t:
                raise ValueError("TimeSeries.avg(t=%g) earlier than last entry (%g)" %
                                 (t, self.t))
            return (self.a+(t-self.t)*self.v)/t
        else:
            return 0

class RunStats(object):
    """A series of numbers."""
    
    def __init__(self, keep_data=False):
        if keep_data: self.d = []
        else: self.d = None
        self.rs = runstats.Statistics()
        
    def _push(self, d):
        if self.d is not None:
            self.d.append(d)
        self.rs.push(d)

    def num(self):
        """Return the number of collected samples."""
        return len(self.rs)

    def data(self):
        """Return all samples if keep_data was set when intializing the
        timeseries; otherwise, return None."""
        return self.d

    def mean(self):
        """Return the sample mean."""
        if self.num() > 0:
            return self.rs.mean()
    
    def stdev(self):
        """Return the sample standard deviation."""
        if self.num() > 1:
            return self.rs.stddev()

    def var(self):
        """Return the sample variance."""
        if self.num() > 1:
            return self.rs.variance()

    def min(self):
        """Return the minimum of all samples."""
        if self.num() > 0:
            return self.rs.minimum()

    def max(self):
        """Return the maximum of all samples."""
        if self.num() > 0:
            return self.rs.maximum()

class TimeMarks(object):
    """A series of (increasing) time instances."""
    
    def __init__(self, keep_data=False):
        if keep_data: self.d = []
        else: self.d = None
        self.n = 0
        
    def _push(self, t):
        if self.n == 0 or t >= self.t:
            if self.d is not None:
                self.d.append(t)
            self.n += 1
            self.t = t
        else:
           raise ValueError("TimeMarks._push(%g) earlier than last entry (%g)" %
                             (t, self.t)) 

    def num(self):
        """Return the number of collected samples."""
        return self.n
    
    def data(self):
        """Return all samples if keep_data was set when intializing the
        timeseries; otherwise, return None."""
        return self.d
    
    def rate(self, t):
        """Return the arrival rate (the averge number of timemarks up to the
        given time)."""
        if self.n > 0:
            if t < self.t:
                raise ValueError("TimeMarks.rate(t=%g) earlier than last entry (%g)" %
                                 (t, self.t))
            return self.n/t
        else:
            return 0

class DataCollector(object):
    """Statistics collection for resources and facilities."""

    def __init__(self, **kwargs):
        """Initialize the data collector. kwargs is the keyworded arguments as
        a dictionary containing all attributes allowed to be collected
        for the corresponding resource or facility."""
        
        self._attrs = kwargs
        makers = {
            re.compile(r'timeseries\s*(\(\s*(all)?\s*\))?') : TimeSeries,
            re.compile(r'runstats\s*(\(\s*(all)?\s*\))?') : RunStats,
            re.compile(r'timemarks\s*(\(\s*(all)?\s*\))?') : TimeMarks
        }
        for k, v in self._attrs.items():
            if hasattr(self, k):
                raise ValueError("DataCollector() attribute %s already exists" % k)
            for pat, cls in makers.items():
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

    def report(self, t):
        """Print out the collected statistics in a formatted way."""
        
        for k, v in self._attrs.items():
            if isinstance(v, TimeSeries):
                print("%s (timeseries): samples=%d" % (k, v.num()))
                if v.num() > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print("  avg=%g" % v.avg(t))
            elif isinstance(v, RunStats):
                print("%s (runstats): samples=%d" % (k, v.num()))
                if v.num() > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print('  mean = %g' % v.mean())
                    if v.num() > 1:
                        print('  stdev = %g' % v.stdev())
                        print('  var = %g' % v.var())
                    print('  min = %g' % v.min())
                    print('  max = %g' % v.max())
            else:
                assert isinstance(v, TimeMarks)
                print("%s (timemarks): samples=%d" % (k, v.num()))
                if v.num() > 0:
                    d = v.data()
                    if d is not None:
                        print("  data=%r ..." % d[:3])
                    print('  rate = %g' % v.rate(t))
