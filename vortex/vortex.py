# newfocus control
#
# Author : C Fujiwara
#
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
#from matplotlib.figure import Figure
import numpy as np
import threading

import tkinter as tk
import time
import csv

# Labckjack configuration
myip="192.168.1.125"

# Open the labjack connection
t7=ljm.openS("T7","ETHERNET",myip)
info = ljm.getHandleInfo(t7)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
 
# On connection write the DAC output (why?)
numFrames = 1
names = ["DAC0"]
aValues = [2.5]  
ljm.eWriteName(t7,"DAC0",2.5)

# Read in initial wavemeter reading
wm = wavemeter.WM(publish=False)
f = wm.read_frequency(4)
f0 = 391016.296
print(f)

# Connect to vortex controller over GPIB
import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
inst = rm.open_resource('GPIB0::1::INSTR')
print(inst.query("*IDN?"))

# Note that in order to change the diode temperature you must connect over RS232


# This portion of code was used to calibrate the voltage control
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
   
   
# This portion of code was used to calibrate the current control
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
  
#====================================================================
# CSV Logging
#====================================================================
import os

fields=['time']
fields.append('frequency (GHz)')

fldr = r'Y:\wavemeter_amar\VortexLockLogs'

# Get the full file name of the log
def getLogName():
    tnow=datetime.now();
    y=tnow.year
    m='%02d' % tnow.month
    d='%02d' % tnow.day
    f1 = os.path.join(fldr,str(y))
    f2= os.path.join(f1,str(y) + '.' + str(m))
    fname= os.path.join(f2,str(m) + '.' + str(d) + '.csv')

    
    if not(os.path.isdir(f1)):
        os.mkdir(f1)
        
    if not(os.path.isdir(f2)):
        os.mkdir(f2)
        
    return fname
       
   # Write the temperature and relative humidites to file   
def doLog(data): 

    # Get the log name file
    fname=getLogName()
        
    if not(os.path.isfile(fname)):
        with open(fname,'w') as f:
            print('Making new log file')
        
    # Check if the existing file has the correct headeres
    with open(fname,'r') as f:
        reader = csv.reader(f)
        headers = next(reader, None)                  
    
    # Choose the write mode depending on the read headers        
    if headers==fields:
        with open(fname,'a',newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data)
            
    else:
        with open(fname,'w',newline='') as f:
            writer = csv.writer(f)
            print('Overwriting old log file as headers dont agree')
            writer.writerow(fields)  
            writer.writerow(data)           
            
#====================================================================
# Main Loop
#====================================================================            

# Fields that are saved for CSV logging
fields=['time','request','read','error','detuning','peizo_set','labjack']

# Deinfe the reosnant frequency to be the B=0 G field from the F=9/2 to F'=11/2 state
f0 = 391016.821

# Initialize stuf
delta0=-40.8
I0 = 50.5
v0 = 4000
stp0 = 1
ljm.eWriteName(t7,"DAC0",v0/1000)

# Wait a moment for the systme to become stable
time.sleep(2)

# Response of the frequency to voltage; calibrated previously
c = .6 # GHz/V

# The main loop
while 1:
    try : 
        # Read the date
        now = datetime.now()
        dt_string = now.strftime('%Y/%m/%d %H:%M:%S')    
        f = wm.read_frequency(4)
        
        # Read the piezo voltage
        v_piezo = inst.query(":sour:volt:piez?")
        v_piezo = v_piezo.strip()
        v_piezo = v_piezo.replace("V","")
        v_piezo = float(v_piezo)         
        
        # Read in request frequency from file
        with open('Y:\wavemeter_amar\lock_freq.txt') as file:
            line = file.readline()    
        
        # If the frequency is a string (ie bad read); print it
        if isinstance(f,str):
            print(f)
        else:     
            # Make sure it is a number
            f_req = float(line)

            # Measure the 
            freq_err = f-f_req        
            detuning = f-f0
            
            data = [dt_string,f_req,f,freq_err,detuning,v_piezo,v0]    
            doLog(data)
    
            print(data)
            
            if abs(freq_err)>.001:
                
                stp = stp0
                        
                if abs(freq_err)>.005 :
                    stp = np.round(abs(freq_err)/c*1000*.8)                
                
                if freq_err>0:
                    v0new  = v0-stp
                else:
                    v0new = v0+stp
                    
                
                if v0new>4500 :     
                    v_piezo_new = v_piezo + 2
                    cmd = ':SOUR:VOLT:PIEZ ' + str(v_piezo_new)
                    #print(cmd)
                    inst.write(cmd)
                    v0new = v0new - 2000
                    #time.sleep(1)
                    #print('incrase piezo by 500 mV')
                    
                if v0new < 100 :   
                    v_piezo_new = v_piezo - 2
                    cmd = ':SOUR:VOLT:PIEZ ' + str(v_piezo_new)
                    #print(cmd)
                    inst.write(cmd)
                    v0new = v0new + 2000
                    #time.sleep(1)       
                    #print('decrease piezo by 500 mV')
    
            
                if v0new < 4500 and v0new>=0:
                    v0 = v0new
                    ljm.eWriteName(t7,"DAC0",v0new/1000)  

            
        time.sleep(1)
    except :
        print('oh no an error occured')

    
print("Closing the labjack ... ") 
ljm.close(t7)
print("Program complete.") 
    
inst.close()

