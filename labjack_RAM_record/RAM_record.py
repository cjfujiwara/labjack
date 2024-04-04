#====================================================================
# Settings
#====================================================================

# FTP
pw='SWxpa2VyYXRzYW5kY2F0c3ZlcnltdWNo='
un='fujiwa27'
sname='individual.utoronto.ca'

# LabJack
t7name="OpticalPower"
myip="192.168.1.126"

# Log Locations
drv='/mnt/Y/'
fldr='LabJack/Logging/Photodiode'

#====================================================================
# Import Packages
#====================================================================

import tkinter
import datetime
import csv
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
T7 = ljm.openS("T7", "ETHERNET", myip) 
info = ljm.getHandleInfo(T7)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

ps=[]
pFs=[]
Npoints=300

#====================================================================
# Photo diodes
#====================================================================    
    
class photodiode:
    def __init__(self, name,AIN,c):
        self.name=name
        self.AIN=AIN
        self.Scale=c
        
    def grabPower(self):
        v=ljm.eReadName(T7,self.AIN)
        F=v/self.Scale
        return F
        
#====================================================================
# Initiate Sensors
#====================================================================    
print("Creating sensor objects...")    

# Create list of all the flow meter objects
fs=[]
fs.append(photodiode("Sense Field (V)","USER_RAM0_F32",1.00))
fs.append(photodiode("PID Status","USER_RAM1_F32",1.00)) 
fs.append(photodiode("Output","USER_RAM2_F32",1.00)) 

ains=[]

  
for f in fs:
    ains.append(f.AIN)
    
def grabVoltages():
    numFrames=len(ains)
    results = ljm.eReadNames(T7, numFrames, ains)
    return results   

#====================================================================
# CSV Logging (incomplete)
#====================================================================

fields=['time']
for f in fs:
    fields.append(f.name + ' (lpm)')


# Get the full file name of the log
def getLogNamePD():
    tnow=datetime.datetime.now();
    y=tnow.year
    m='%02d' % tnow.month
    d='%02d' % tnow.day
    f1=drv +fldr +'/' + str(y)
    f2=f1 + '/' + str(y) + '.' + str(m)
    fname=f2 + '/' + str(m) + '_' + str(d) + '.csv'
    
    if not(os.path.isdir(f1)):
        os.mkdir(f1)
        
    if not(os.path.isdir(f2)):
        os.mkdir(f2)
        
    return fname
 
# Write the temperature and relative humidites to file   
def doLogPD(pds): 

    tnow=datetime.datetime.now()
    tlabel=tnow.strftime("%m/%d/%Y, %H:%M:%S")
    # Format the data
    data=[tlabel]
    for f in pds:
        data.append(str(round(f,2)))

    # Get the log name file
    fname=getLogNamePD()
        
    if not(os.path.isfile(fname)):
        with open(fname,'w') as f:
            print('Making new log file')
        
    # Check if the existing file has the correct headeres
    with open(fname,'r') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
    
    # Choose the write mode depending on the read headers        
    if headers==fields:
        with open(fname,'a') as f:
            writer = csv.writer(f)
            writer.writerow(data)
            
    else:
        with open(fname,'w') as f:
            writer = csv.writer(f)
            print('Overwriting old log file as headers dont agree')
            writer.writerow(fields)  
            writer.writerow(data)
              
#=============================================================================
# FTP STuff
#=============================================================================

import base64
from ftplib import FTP

ftp=FTP(sname)
#ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))

def ftpupdate(V):
    fname='pds'
    file=open(fname,'w+')
    
    file.write(datetime.datetime.now().strftime('%Y/%m/%d %I:%M:%S.%f %p') +'\n')

    for val,Fobj in zip(V,fs):
        file.write(Fobj.name + ',' + str(round(1000*val,2)) + '\n')    
    file.close()    
    filename=fname
    with open(filename, "rb") as file:        
        ftp.storbinary("STOR %s" % filename, file)  


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
    string2 = string2 + ", trig=" + "%u" %  round(V[1])
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
        output['data'] = data
        scipy.io.savemat('bob.mat',output)   
        
        
        dt0 = 50
        t = (data[:,0]-data[1,0])*1000
        inds = t>=dt0
        
        sensemean = data[inds,2].mean()
        sensestd = data[inds,2].std()
        
        outmean = data[inds,3].mean()
        outstd = data[inds,3].std()
        
        string3 = 'Last Data'
        string3 =  string3 + string + ", sense=" + "%.3f" % round(sensemean,3) + ' +- ' + \
            "%.3f" % round(sensestd,3) + ' V'
        string3 =  string3 + ", out=" + "%.3f" % round(outmean,3) + ' +- ' + \
            "%.3f" % round(outstd,3) + '  V'
        
        clear_line()
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
    
    #lbl.config(text = string2 + ' (' + str(round(dT*1000)) + ' ms)')  
    #print()
    m2.after(0, timeUpdate) 

#=============================================================================
# GUI Objects
#=============================================================================
# Main window
app = tkinter.Tk()
app.title("Photodiode Monitor")
app.geometry("800x300")

# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",bg="white",font=("DejaVu Sans Mono",18))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,fill="both",side="top")

# Main string output
m2 = tkinter.Label(left_frame,text="text",bg="white",font=("DejaVu Sans Mono",50))
m2.pack(side="left",anchor='nw')    

# Wait a second
time.sleep(.5)

        
#=============================================================================
# Main Loop
#=============================================================================

print('Last Data : None')
print('this gets deleted')

# Initiate clock fucntions
timeUpdate()


# Start the GUI (dont know what this really does)
app.mainloop()

# Close the labjack connection
print("Closing the labjack") 
ljm.close(T7)
print("I think the labjack closed?")

# Stop the FTP update
ftp.quit()
