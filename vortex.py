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
from threading import Thread

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

#import pyvisa
#rm = pyvisa.ResourceManager()
#rm.list_resources()
#inst = rm.open_resource('GPIB0::1::INSTR')
#print(inst.query("*IDN?"))

#inst.close()

class vortex_controller(Thread):
    def __init__(self,instrument):
        super().__init__()
        self.instrument = instrument
        
        self.CurrentSense = 0
        self.CurrentSet = 0
        self.VoltageSense = 0
        self.VoltageSet = 0
        
    def run(self):
        self.AcqStatus.config(text='acquiring ... ',fg='green')
        self.AcqStatus.update()  


class App(tk.Tk):
    def __init__(self):        
        # Create the GUI object
        super().__init__()
        self.title('Vortex Controller')
        self.geometry("1280x780")
        
    def create_frames(self):
        self.Fopt = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fopt.pack(side='left',anchor='nw',fill='y')
        
        # Connect Frame
        self.Fconnect = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fconnect.grid(row=1,column=1,sticky='we')
        
        # Voltage output
        self.Foutput = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Foutput.grid(row=2,column=1,sticky='we')
        
        # Acquisition
        self.Facquire = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Facquire.grid(row=3,column=1,sticky='we')
        
        # Peak Analysis Settings
        self.Fpeak = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fpeak.grid(row=4,column=1,sticky='we')
        
        # Peak Analysis Output
        self.Fpeakout = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fpeakout.grid(row=5,column=1,sticky='we')
        
        # Lock Settings
        self.Flock = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Flock.grid(row=6,column=1,sticky='we')
        
        # Plots
        self.Fplot = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fplot.pack(side='right',fill='both',expand=1)
        
    def on_closing(self):
        #self.disconnect()
        self.destroy()


if __name__ == "__main__":
     app = App()
     app.protocol("WM_DELETE_WINDOW", app.on_closing)
     app.mainloop()       

print('hi')