#====================================================================
# Settings
#====================================================================

# LabJack Identifier
# It is usually more reliable to choose the correct SN since that is unique to 
# particular device, while an IP address can be reassigned
my_ip ="192.168.1.125"
my_sn = 470024251
#====================================================================
# Import Packages
#====================================================================

import datetime
import os
import time
from labjack import ljm
import numpy as np
os.system("")
import scipy

#====================================================================
# Labjack connection
#====================================================================

# open connection to labjack
print("Connecting to Labjack")
#T7 = ljm.openS("T7", "ETHERNET", my_ip) # If want to choose using IP
T7 = ljm.openS("T7", "ETHERNET", my_sn) # If want to choose using SN

info = ljm.getHandleInfo(T7)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

# Channels to read
ains=["USER_RAM0_F32","USER_RAM1_F32","USER_RAM2_F32"]

#=============================================================================
# Update Function
#=============================================================================
def clear_line(n=1):
    LINE_UP = '\033[1A'
    LINE_CLEAR = '\x1b[2K'
    for i in range(n):
        print(LINE_UP, end=LINE_CLEAR)
        
numFrames=len(ains)

N = 1000
array = np.zeros((N,4), dtype=float) 
myind = 0

tNow = datetime.datetime.now().timestamp()   
tLast = datetime.datetime.now().timestamp()   

global trig_last
trig_last = False

def timeUpdate():
    global tLast
    global myind
    global array 
    global trig_last 
    
    # Get the time  
    tNow = datetime.datetime.now().timestamp()   
    
    # Read values
    V = ljm.eReadNames(T7, numFrames, ains)    
    dT = (tNow-tLast)
    
    tLast = tNow
    
    # Update the clock 
    string = datetime.datetime.now().strftime('%H:%M:%S.%f') 
    string2 =  string + ' (' + "%.1f" % round(dT*1000,1) + ' ms)'    
    string2 = string2 + ", trig=" + "%u" %  round(V[1])  # 0: PID off, 1: sp, 2: stripe
    string2 = string2 + ", sense=" + "%.4f" % round(V[0],4) + ' V'   
    string2 = string2 + ", out=" + "%.4f" % round(V[2],4) + ' V'  
    
    # Permute the data buffer
    array = np.roll(array,1,axis=0)
    array[0,0] = tNow
    array[0,1] = V[1]
    array[0,2] = V[0]
    array[0,3] = V[2]   
    
    # The current PID status
    trig_now = bool(round(V[1]))        
    
    # Trigger is going from ON to OFF ==> SAVE THE DATA OR SOMETHING
    if not(trig_now) and trig_last:
    #if myind == N-1:
        data=array
        # Get subset of data where where trig is high
        data = array[np.nonzero(array[:,1])[0],:] 
        # Sort data by acquisition time (since data buffer is permuted)
        data = data[data[:,0].argsort(),:]
        output = dict()
        output['acquisitiondate'] = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') 
        output['data'] = data
        scipy.io.savemat('lastlog.mat',output)       
        dt0 = 50
        t = (data[:,0]-data[1,0])*1000
        inds = t>=dt0        
        sensemean = data[inds,2].mean()
        sensestd = data[inds,2].std()
        outmean = data[inds,3].mean()
        outstd = data[inds,3].std()        
        string3 =  string + ", sense=" + "%.3f" % round(sensemean,3) + ' +- ' + \
            "%.3f" % round(sensestd,3) + ' V'
        string3 =  string3 + ", out=" + "%.3f" % round(outmean,3) + ' +- ' + \
            "%.3f" % round(outstd,3) + '  V'        
        clear_line()
        print(string3)
    else:
        clear_line()
        
    myind = myind + 1
    
    if myind == N:
        myind = 0        
 
    # Print current value
    print(string2)
    
    # Update Trigger
    trig_last = trig_now    
    # Wait and update
    time.sleep(0.000001)



#=============================================================================
# Main Loop
#=============================================================================

print('this gets deleted')

while True:
    timeUpdate()

# Close the labjack connection
print("Closing the labjack") 
ljm.close(T7)
print("I think the labjack closed?")
