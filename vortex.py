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

import wavemeter as wavemeter
from labjack import ljm

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
import csv

# Labckjack configuration
t7name="CurrentMonitor"
myip="192.168.1.124"

#handle=ljm.openS("T7","ETHERNET",'470026765')

t7=ljm.openS("T7","ETHERNET",myip)
info = ljm.getHandleInfo(t7)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
 
numFrames = 1
names = ["DAC0"]
aValues = [2.5]  # [2.5 V, 12345]
ljm.eWriteNames(t7, numFrames, names, aValues)

print("Closing the labjack ... ") 
ljm.close(t7)
print("Program complete.") 

   
wm = wavemeter.WM(publish=False)

f = wm.read_frequency(3)
f0 = 391016.296

print(f)


import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
inst = rm.open_resource('GPIB0::1::INSTR')
print(inst.query("*IDN?"))



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


"""
start=0
step=1
num=105
vals1 = np.arange(0,num)*step+start
vals2 = np.flip(vals1)

valsSet = np.concatenate((vals1,vals2))

valsRead = np.zeros(len(valsSet))
freqRead = np.zeros(len(valsSet))

print(valsSet.shape)
print(valsRead.shape)
print(freqRead.shape)

for j in range(len(valsSet)):
    v = np.round(valsSet[j],1)
    me = ':SOUR:VOLT:PIEZ ' + str(v)
    inst.write(me)
    time.sleep(1)
    vact = inst.query(":sens:volt:piez")
    vact = vact.strip()
    vact = vact.replace("V","")
    vact = float(vact)    
    
    f = wm.read_frequency(3)    
    
    print(str(v) + ' V, ' + str(vact) + ' V, ' + str(f) + ' GHz')

    valsRead[j] = vact
    freqRead[j] = f
    
    data=[v,vact,f]   
        
    with open(r"cora.csv", 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)
        time.sleep(1)
    



#if __name__ == "__main__":
#     app = App()
#     app.protocol("WM_DELETE_WINDOW", app.on_closing)
#     app.mainloop()    
   """
   
"""
start=50
step=.5
num=20
vals1 = np.arange(0,num)*step+start
vals2 = np.flip(vals1)

valsSet = np.concatenate((vals1,vals2))

valsRead = np.zeros(len(valsSet))
freqRead = np.zeros(len(valsSet))
   
   
for j in range(len(valsSet)):
    v = np.round(valsSet[j],1)
    me = ':SOUR:CURR ' + str(v)
    inst.write(me)
    time.sleep(1)
    vact = inst.query(":sens:curr")
    vact = vact.strip()
    vact = vact.replace("mA","")
    vact = float(vact)    
    
    f = wm.read_frequency(3)    
    
    print(str(v) + ' mA, ' + str(vact) + ' mA, ' + str(f) + ' GHz')

    valsRead[j] = vact
    freqRead[j] = f
    
    data=[v,vact,f]   
        
    with open(r"cora.csv", 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)
        time.sleep(1)
"""
  
"""
# Read this frequecny
f0 = 391016.296

delta0=-50.4

I0 = 50.5

while 1:
    now = datetime.now()
    dt_string = now.strftime('%Y/%m/%d %H:%M:%S')    
    f = wm.read_frequency(3)
    
    delta = f-f0

    data = [dt_string,I0,f,delta]
    print(data)
    
    if abs(delta)>.05 :
        if delta>delta0:
            I0 = np.round(I0+.1,1)
        else:
            I0 = np.round(I0-.1,1)
            
        if I0>45 and I0<55 :
            me = ':SOUR:CURR ' + str(I0)
            inst.write(me) 
    
    with open(r"lock_test.csv", 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)
        
    time.sleep(1)
"""
    
inst.close()

