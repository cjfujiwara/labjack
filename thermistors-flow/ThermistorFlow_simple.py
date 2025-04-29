#===========================================================
# Packages
#===========================================================

import tkinter
import datetime
import numpy as np
from time import strftime
import csv
import os
import time
from labjack import ljm

#===========================================================
# Labjack connection
#===========================================================


#drv='/mnt/Y/'
#fldr='LabJack/Logging/FlowRate'


drv = 'X:\\'
fldr = 'LabJackLogs\\thermistors-flow'

import sys
sys.path.append("X:\\LabJackLogs\\_labjack_keys")
from key_thermistors_flow import *




# open connection to labjack
print("Connecting to Labjack")
T7 = ljm.openS("T7", "ETHERNET", myip) 
info = ljm.getHandleInfo(T7)
print(
    " Device type       : %i \n"
    " Connection type   : %i \n"
    " Serial number     : %i \n"
    " IP address        : %s \n"
    " Port              : %i \n"
    " Max bytes per MB  : %i" %
      (info[0], info[1], info[2], 
       ljm.numberToIP(info[3]), info[4], info[5]))

ljm.eWriteName(T7,"DAC0",4.5)

ps=[]
pFs=[]
Npoints=300
#===========================================================
# Thermistor Class 3
#===========================================================
class thermistor3:
    def __init__(self, name,AIN):
        self.name = name    
        self.AIN = AIN
        #self.setpoint = setpoint
        #self.oldname = oldname
        #self.oldch = oldch
        
    def VtoT(self,v):

        

       T=(v+3.1311)/0.1273
       return T  
   
    def grabVoltage(self):
        print("here I grab the voltage from the labjack")
        
    def grabTemperature(self):
        v=ljm.eReadName(T7, self.AIN)
        T=self.VtoT(v)
        return T
#===========================================================
# Thermistor Class 2
#===========================================================
class thermistor2:
    def __init__(self, name,AIN):
        self.name = name    
        self.AIN = AIN
        #self.setpoint = setpoint
        #self.oldname = oldname
        #self.oldch = oldch
        
    def VtoT(self,v):
# The thermistors are Digikey 490-4662-ND.  These are 30k resistors
# They have a B = 4100 coefficient and callibration temperature of
# 25C.  They are in a wheatstone comparitor circuit which trips the
# interlock.  The ADC reads a votlage on the thermistor which is in
# a voltage divider with a 100kOhm reference resistor with the a
# 15V supply.
        
       B=4250              # B coeffcients
       R0=100              # Resistance at 25C
       V0=5.02              # Total voltage
       R1=100              # Reference resistor is 100kohm
       T0=25+273.16        # Calibration temperature in K                
       Rt=R1/(V0/v-1)      # Convert voltage on thermistor to voltage    
       T=(1/T0+np.log(Rt/R0)/B)**(-1)-273.16  # Invert Steinhart Equation          
       return T  
   
    def grabVoltage(self):
        print("here I grab the voltage from the labjack")
        
    def grabTemperature(self):
        v=ljm.eReadName(T7, self.AIN)
        T=self.VtoT(v)
        return T

#===========================================================
# Thermistor Class
#===========================================================
class thermistor:
    def __init__(self, name,AIN,setpoint,oldname,oldch):
        self.name = name    
        self.AIN = AIN
        self.setpoint = setpoint
        self.oldname = oldname
        self.oldch = oldch
        
    def VtoT(self,v):
# The thermistors are Digikey 490-4662-ND.  These are 30k resistors
# They have a B = 4100 coefficient and callibration temperature of
# 25C.  They are in a wheatstone comparitor circuit which trips the
# interlock.  The ADC reads a votlage on the thermistor which is in
# a voltage divider with a 100kOhm reference resistor with the a
# 15V supply.
        
       B=4100              # B coeffcients
       R0=30               # Resistance at 25C
       V0=15               # Total voltage
       R1=100              # Reference resistor is 100kohm
       T0=25+273.16        # Calibration temperature in K                
       Rt=R1/(V0/v-1)      # Convert voltage on thermistor to voltage    
       T=(1/T0+np.log(Rt/R0)/B)**(-1)-273.16  # Invert Steinhart Equation          
       return T  
   
    def grabVoltage(self):
        print("here I grab the voltage from the labjack")
        
    def grabTemperature(self):
        v=ljm.eReadName(T7, self.AIN)
        T=self.VtoT(v)
        return T
    
#===========================================================
# Flow Meters
#===========================================================   
    
class flowmeter:
    def __init__(self, name,AIN,c):
        self.name=name
        self.AIN=AIN
        self.Scale=c
        
    def grabFlow(self):
        v=ljm.eReadName(T7,self.AIN)
        F=v/self.Scale
        return F
        
#===========================================================
# Initiate Sensors
#===========================================================   
    # Use the pin mapping of the MUX 80 Board
        
print("Creating thermistor and flow meter objects...")    
# Create the list of all thermistor objects
ts=[]

# X3 MOT Thermistors
ts.append(thermistor2("X MOT Shim","AIN68"))  # FIO4
ts.append(thermistor2("Y MOT Shim","AIN69"))  # FIO5
ts.append(thermistor2("Z MOT Shim","AIN70"))  # FIO6

# X2 Thermistors
ts.append(thermistor("MOT Top","AIN0",2.83,"MOT Top",1))
ts.append(thermistor("MOT Bot","AIN1",2.92,"MOT Bot",2))
ts.append(thermistor("11 Extra Top","AIN2",2.89,
                     "Coil 12 (new) Top",3))
ts.append(thermistor("11 Extra Bot","AIN3",2.92,
                     "Coil 12 (new) Bot",4))
ts.append(thermistor("Coil 12A","AIN120",2.93,"Vert 1",5))      # AIN6 on X2
ts.append(thermistor("Coil 12B","AIN121",2.88,"Vert 2",6))      # AIN7 on X2
ts.append(thermistor("Coil 13","AIN122",2.88,"Vert 3",7))       # AIN8 on X2
ts.append(thermistor("Coil 14","AIN123",2.95,"Vert 4",8))       # AIN9 on X2
ts.append(thermistor("Coil 15","AIN124",1.87,"QP Bot",9))       # AIN10 on X2
ts.append(thermistor("Coil 16","AIN125",1.88,"QP Top",10))      # AIN11 on X2
ts.append(thermistor("Fesh Bot","AIN126",2.96,"Fesh Bot",11))   # AIN12 on X2
ts.append(thermistor("Fesh Top","AIN127",2.93,"Fesh Top",12))   # AIN13 on X2 

# X3 Thermistors and flow meters
ts.append(thermistor2("Fesh Term 1","AIN64"))  # FIO0 on X3
ts.append(thermistor2("Fesh Term 2","AIN65"))  # FIO1 on X3
ts.append(thermistor2("Fesh Term 3","AIN66"))  # FIO2 on X3
ts.append(thermistor2("Fesh Term 4","AIN67"))  # FIO3 on X3

ts.append(thermistor3("X Sci Shim","AIN57"))  # on X3 
ts.append(thermistor3("Y Sci Shim","AIN58"))  # on X3
ts.append(thermistor3("Z Sci Shim","AIN59"))  # on X3

# Create list of all the flow meter objects
fs=[]
fs.append(flowmeter("CATS 1-13 and FETs","AIN54",0.59)) # AIN6 on X3
fs.append(flowmeter("QP Top","AIN50",1.83))             # AIN2 on X3 (1.89)
fs.append(flowmeter("QP Bot","AIN71",1.86))             # FIO7 on X3 (1.89)
fs.append(flowmeter("Feshbach Total","AIN48",4.40))     # AIN0 on X3
fs.append(flowmeter("Feshbach Bottom","AIN55",8.81))    # AIN7 on X3 
fs.append(flowmeter("Feshbach Top","AIN56",8.81))       # AIN8 on X3
fs.append(flowmeter("Nufern Process","AIN49",8.81))     # AIN1 on X3
fs.append(flowmeter("Feshbach House","AIN51",1.87))     # AIN3 on X3
fs.append(flowmeter("Nufern House","AIN52",1.87))       # AIN4 on X3 
fs.append(flowmeter("Transport House","AIN53",1.87))    # AIN5 on X3

ains=[]
for t in ts:
    ains.append(t.AIN)
  
for f in fs:
    ains.append(f.AIN)
    
def grabVoltages():
    numFrames=len(ains)
    results = ljm.eReadNames(T7, numFrames, ains)
    return results   

#===========================================================
# CSV Logging (only do flow rates)
#===========================================================
    


fields=['time']
for f in fs:
    fields.append(f.name + ' (lpm)')


def liveSave(ts,V,fs,V2):
    fname = drv + '/thermistor_flow.csv'     
    file=open(fname,'w+')

    tnow=datetime.datetime.now()
    tlabel=tnow.strftime('%y-%m-%d_%H-%M-%S')  
    file.write('Date,' + tlabel +'\n')
        
       # Convert voltage to temperature
    for t,val in zip(ts,V):
        val=t.VtoT(val)
        file.write(t.name + ',' + str(round(val,2)) + '\n')  
    for f,val in zip(fs,V2):
        val=val/f.Scale     
        file.write(f.name + ',' + str(round(val,2)) + '\n')  
    file.close()    


# Get the full file name of the log
def getLogNameFlow():
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
def doLogFlow(flows): 

    tnow=datetime.datetime.now()
    tlabel=tnow.strftime("%m/%d/%Y, %H:%M:%S")
    # Format the data
    data=[tlabel]
    for f in flows:
        data.append(str(round(f,2)))

    # Get the log name file
    fname=getLogNameFlow()
        
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

#===========================================================
# FTP STuff
#===========================================================

import base64
from ftplib import FTP

#try:
ftp=FTP(sname)
ftp.login(user=un,
          passwd=base64.b64decode(pw).decode('utf-8'))
#except:
 #   pass
    #ftp.retrlines('LIST')

def ftpupdate(Ts,Fs):
    fname='flows_magnets'
    file=open(fname,'w+')
    
    file.write(strftime('%Y/%m/%d %I:%M:%S %p') +'\n')
    for T,Tobj in zip(Ts,ts):
        file.write(Tobj.name + ',' + str(round(T,2)) + '\n')
    for F,Fobj in zip(Fs,fs):
        file.write(Fobj.name + ',' + str(round(F,2)) + '\n')    
    file.close()    
    filename=fname
    with open(filename, "rb") as file:
        
    # use FTP's STOR command to upload the file
        ftp.storbinary("STOR %s" % filename, file)  

#===========================================================
# Update Function
#===========================================================

tLastFlowLog=datetime.datetime.now()
tLastFlowLog=tLastFlowLog.timestamp()-10000

def timeUpdate():
    global tLastFlowLog
    
    # Update the clock 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string)    

    mainStr=''    
    
    # Log Magnetic Field
    #v = logField() 
    #B = 500*v # 500 mG/V        
    #mainStr = mainStr + "Magnetic Field".ljust(20,' ') + \
     #   "{0:.2f}".format(B) + ' mG' + '\n'
    
    # Line break
    mainStr = mainStr + '\n'    
    
    # Grab other labjack voltages   
    V=grabVoltages();   # Grab all the voltages    
    V2=V[len(ts):]      # Flow meter voltages come after thermistor    
    myfs=[]             # flow meter flows (lpm)
    myTs=[]             # temperature readings (C)  
    
    # Convert voltage to temperature
    for t,val in zip(ts,V):
        val=t.VtoT(val)
        myTs.append(val) 
        mainStr = mainStr + (t.name).ljust(20,' ') + \
            "{0:.2f}".format(val) + ' C' + '\n'
        
    # Linebreak
    mainStr = mainStr + '\n'
    
    # Convert voltage to flow rate
    for f,val in zip(fs,V2):
        val=val/f.Scale        
        myfs.append(val)         
        mainStr = mainStr + (f.name).ljust(20,' ') + \
            "{0:.2f}".format(val) + ' lpm' + '\n'
            
    try:
        liveSave(ts,V,fs,V2)
    except:
        print('oh no')

    # Update web server
    try: 
        ftpupdate(myTs,myfs)
    except:
        print("unable to update ftp")    
    
    # Log the flow rate every thirty seconds
    tFlowLogNow=datetime.datetime.now().timestamp()
    if tFlowLogNow-tLastFlowLog>30:    
        doLogFlow(myfs)
        tLastFlowLog=tFlowLogNow   
        

    m2.config(text=mainStr,justify='l')
    m2.after(100, timeUpdate) 

        
#===========================================================
# Main GUI
#===========================================================
# Main window
app = tkinter.Tk()
app.title("Water, Thermistor, and Field Monitor")
app.geometry("400x950")


# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",bg="white",
                    font=("DejaVu Sans Mono",18))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,
                fill="both",side="top")

# Main Strin Text
m2 = tkinter.Label(left_frame,text="text",bg="white",
                   font=("Courier New",16))
m2.pack(side="left",anchor='nw')    

# Wait a hot second
time.sleep(.5)

#===========================================================
# Main Loop
#===========================================================


# Initiate clock fucntions
timeUpdate()

#Start the GUI (dont know what this really does)
app.mainloop()

# Close the LabJack connection
print("Closing the labjack") 
ljm.close(T7)
print("I think the labjack closed?")

# Close the FTP connection
ftp.quit()
