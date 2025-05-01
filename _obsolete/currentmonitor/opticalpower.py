#====================================================================
# Settings
#====================================================================

# FTP
pw='SWxpa2VyYXRzYW5kY2F0c3ZlcnltdWNo='
un='fujiwa27'
sname='individual.utoronto.ca'

# LabJack
t7name="OpticalPower"
myip="192.168.1.145"

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
fs.append(photodiode("MOT Trap","USER_RAM1_F32",1.00))
fs.append(photodiode("MOT Repump","USER_RAM0_F32",1.00)) 
fs.append(photodiode("K Trap Shutter","USER_RAM0_I32",1.00)) 
fs.append(photodiode("Rb Trap Shutter","USER_RAM1_I32",1.00)) 
fs.append(photodiode("K Ready","USER_RAM2_I32",1.00)) 
fs.append(photodiode("Rb Ready","USER_RAM3_I32",1.00)) 
fs.append(photodiode("MOT Trap   K","USER_RAM3_F32",1.00))
fs.append(photodiode("MOT Repump K","USER_RAM2_F32",1.00)) 
fs.append(photodiode("MOT Trap   Rb","USER_RAM5_F32",1.00))
fs.append(photodiode("MOT Repump Rb","USER_RAM4_F32",1.00)) 
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
ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))

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

numFrames=len(ains)
tLast = datetime.datetime.now().timestamp()
def timeUpdate():
    global tLast
    
    # Grab other labjack voltages   
    tNow = datetime.datetime.now().timestamp()
    #V=grabVoltages();   # Grab all the voltages  
    
    V = ljm.eReadNames(T7, numFrames, ains)
    
    dT = (tNow-tLast)
    tLast = tNow
    
    # Update the clock 
    string = datetime.datetime.now().strftime('%Y.%m.%d %I:%M:%S.%f %p') 
    lbl.config(text = string + ' (' + str(round(dT*1000)) + ' ms)')  


    # Reset Ready values    
    if ((V[4]==1) & (V[5]==1)):
        ljm.eWriteNames(T7, 2, ['USER_RAM2_I32', 'USER_RAM3_I32'],[0, 0])
      
    mainStr = ''
    # Create updated string
    for f,val in zip(fs,V):
        val=val/f.Scale                
        mainStr = mainStr + (f.name).ljust(15,' ') + "{0:.1f}".format(val*1000) + ' mV' + '\n'

    # Update web server
    ftpupdate(V)            

    # Assign String
    m2.config(text=mainStr,justify='l')
    m2.after(200, timeUpdate) 

        
#=============================================================================
# GUI Objects
#=============================================================================
# Main window
app = tkinter.Tk()
app.title("Photodiode Monitor")
app.geometry("1200x1000")


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
