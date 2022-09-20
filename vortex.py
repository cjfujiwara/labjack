# -*- coding: utf-8 -*-
"""
Created on Tue Sep 20 19:16:53 2022

@author: Sephora
"""

# newfocus control
#
# Author : C Fujiwara
#
# This code runs a GUI which allows for monitoring of the transport currents 
# a labjack T7.  In the laboratory we have current monitors which output a 
# voltage proportional to the current.  The ADCs on a T7 pro are 16bit on a 
# range of +-10V.
#
# For information regarding installation of labjack packages, see the readme
# associated with this python script.
#
# This code uses the stream burst functionality in order to achieve the fastest
# data reads from the ADCs. In this mode, the labjack functions most similarly
# to a oscilloscope.
#
# See the following documentation for detailed information on stream mode
#
# https://labjack.com/support/datasheets/t-series/communication/stream-mode
# https://labjack.com/support/software/api/ljm/function-reference/stream-functions
#
# The measured currents are then compared to known currents traces and the GUI 
# then detects for any large residues in the transport.

print("Loading packages ...")
# Import packages
import sys
from datetime import datetime
from time import strftime
from matplotlib.figure import Figure
import numpy as np
import threading
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
import tkinter as tk
import scipy.io
import time


import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
inst = rm.open_resource('GPIB0::1::INSTR')
print(inst.query("*IDN?"))

inst.close()