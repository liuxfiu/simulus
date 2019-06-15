# FILE INFO ###################################################
# Author: Jason Liu <liux@cis.fiu.edu>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-06-15 05:32:44 liux>
###############################################################

"""Simulus is a discrete-event simulator in Python."""

from __future__ import absolute_import

import sys
if sys.version_info[:2] < (3, 7):
    raise ImportError("Simulus requires Python 3.7 and above (%d.%d detected)." %
                      sys.version_info[:2])
del sys

from .simulator import *
