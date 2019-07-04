# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-07-03 21:03:12 liux>
###############################################################

"""Simulus is a discrete-event simulator in Python."""

from __future__ import absolute_import

import sys
if sys.version_info[:2] < (3, 7):
    raise ImportError("Simulus requires Python 3.7 and above (%d.%d detected)." %
                      sys.version_info[:2])
del sys

from .utils import *
from .trappable import *
from .trap import *
from .semaphore import *
from .resource import *
from .simulator import *
