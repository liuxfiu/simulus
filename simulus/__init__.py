# FILE INFO ###################################################
# Author: Jason Liu <jasonxliu2010@gmail.com>
# Created on June 14, 2019
# Last Update: Time-stamp: <2019-09-07 09:14:34 liux>
###############################################################

"""Simulus is a discrete-event simulator in Python."""

from __future__ import absolute_import
import sys, argparse

if sys.version_info[:2] < (2, 8):
    raise ImportError("Simulus requires Python 2.8 and above (%d.%d detected)." %
                      sys.version_info[:2])

from .utils import *
from .trappable import *
from .trap import *
from .semaphore import *
from .resource import *
from .store import *
from .bucket import *
from .mailbox import *
from .simulator import *
from .sync import *

# parse command line (filter out those arguments known by simulus)
#print('importing simulus... command-line parsing')
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("-s", "--seed", type=int, metavar='SEED', default=None,
                    help="set global random seed")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="enable verbose information")
parser.add_argument("-vv", "--debug", action="store_true",
                    help="enable debug information")
parser.add_argument("-x", "--mpi", action="store_true",
                    help="enable mpi for parallel simulation")
args, sys.argv[1:] = parser.parse_known_args()

__version__ = '1.2.1'
