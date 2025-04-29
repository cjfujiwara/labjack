#===========================================================
# humidity.py
#===========================================================
# This python script communicates with the humidity sensors
# connected to a labjack. Data is saved to a network drive,
# and live data is sent to an FTP server.  Slack alarms are 
# also an option. 
#
# Long term plotting is done with auxillary programs.

#===========================================================
# Settings
#===========================================================

#drv='/mnt/Y/'
#fldr='LabJack/Logging/Temperature-Humidity'

drv = 'X:\\'
fldr = 'LabJackLogs\\Temperature-Humidity'

import sys
sys.path.append("X:\LabJackLogs\\_labjack_keys")
import key_temp_humidity

keys = key_temp_humidity.mykeys()


sn = keys['sn']
t7name = keys['t7name']
myip=keys['myip']
slack_token=keys['slack_token']
pw = keys['pw']
un=keys['un']
sname=keys['sname']


#print(keys['sn'])

#python "X:\LabJackLogs\\_labjack_keys\\key_temp_humidity"



doFTP       = 1
doSlack     = 0


#===========================================================
# Packages
#===========================================================
import datetime
import numpy as np
import csv
import os
from time import strftime
import time

import tkinter

from labjack import ljm

import base64
from ftplib import FTP

# Import stuff for slack tokens
#from slackclient import SlackClient

#===========================================================
# Slack Functions
#===========================================================
# Functions for sending text and image messages to slack
# Storing the token as text is bad practice as it's like a password

# Send a text message over slack
#if doSlack:
#    sc = SlackClient(slack_token)

#def slackMessage(txt):
#    sc.api_call(
#        "chat.postMessage",
#        channel="lab_alerts",
#        text=txt
#  )
  
# Send a slack image.  We always send the temp image image.png
"""
def slackImage(txt):
    fig.savefig("image.png")
    sc.api_call(
    "files.upload",
    channels="lab_alerts",
    file=open("./image.png","rb"),
    initial_comment=txt
)    
"""
#===========================================================
# LabJack
#===========================================================

def connectLabJack():
    # Open connection to labjack
    print("connecting to lab jack")
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
    return T7

T7 = connectLabJack()
#===========================================================
# Temperature and Humitidy Sensors
#===========================================================
# The humidity sensors communicate on a SPI interface.  This means that 
# multiple sensors can share the same data pin, but they each need their
# own enable pin. Generally it is considered bad practice to have more than five
# devices ona  single data channel.
      
# When this code was initially written in 2020, we use the sensors from Labjack
# ******* INESRT, which have been discontinued.
      
## Define sensor class which is just a list of pins
class humidityA:
    def __init__(self, name,data,clock,power,enable,TLIM,RLIM):
        self.name=name
        self.data=data          # Data pin
        self.clock=clock        # Clock pin (timing)
        self.power=power        # Power pin
        self.enable=enable      # Enable pin           
        self.TLIM=TLIM          # Temperature alert limits
        self.RLIM=RLIM          # Humidtiy alert limits
      
# Create list of sensors
print("Initializing humidity sensor objects...")

sensors=[]
sensors.append(humidityA("MOT Optics",14,15,16,"CIO1",
                         [20, 25.5],[29, 42]))
sensors.append(humidityA("XDTs / Y Lattice",14,15,16,"CIO2",
                         [20, 25.5],[29, 42]))
sensors.append(humidityA("Nufern",14,15,16,"CIO3",
                         [22, 27],[29, 42]))
sensors.append(humidityA("Plug / X Lattice",0,1,2,"FIO3",
                         [20, 25.5],[29, 42]))
sensors.append(humidityA("ALS",0,1,2,"FIO4",
                         [20, 27],[28.0, 42]))
sensors.append(humidityA("Z Lattice",0,1,2,"FIO5",
                         [20, 25.5],[29, 42]))
sensors.append(humidityA("Top Breadboard",8,9,10,"EIO3",
                         [20, 26],[28, 42]))
sensors.append(humidityA("Above Machine Cloud" ,8,9,10,"EIO4",
                         [22, 26],[28, 42]))

# Create list of enable pins
epins=[]
fields=['time']

for s in sensors:
    epins.append(s.enable)
    ljm.eWriteName(T7,s.enable,0)
    fields.append(s.name + ' TEMP')
    fields.append(s.name + ' RH')    


# Reads all and output the temperatures and humidities
def readSensors():    
    rhs=[]              # List for humidities
    temps=[]            # List for temperatures
    
    # Disable all sensors by clearing all enable pins
    ljm.eWriteNames(T7, len(sensors),epins,[0]*len(sensors)) 

    # Iterate over each sensor
    for s in sensors:
        # Configure the SPI pins data, clock, power, and enable
        names=["SBUS0_DATA_DIONUM",
               "SBUS0_CLOCK_DIONUM",
               "SBUS_ALL_POWER_DIONUM",
               s.enable] 
        ljm.eWriteNames(T7, len(names),names,
                        [s.data,s.clock,s.power,1])  
        
        # Read sensors
        results = ljm.eReadNames(T7, 2,
                                 ["SBUS0_TEMP","SBUS0_RH"])
        # Process the data from the sensors
        temp=results[0]-273.15  # Kelvin to C
        rh=results[1]           # relative humidity
        
        # Append data to output
        temps.append(temp)        
        rhs.append(rh)
        
        # Disable the current sensr
        ljm.eWriteName(T7, s.enable, 0)
    return temps,rhs 
    
#===========================================================
# Logging
#===========================================================
    

# Get the full file name of the log
def getLogName():
    tnow=datetime.datetime.now();
    y=tnow.year
    m='%02d' % tnow.month
    d='%02d' % tnow.day
    f1=drv +fldr +'\\' + str(y)
    f2=f1 + '\\' + str(y) + '.' + str(m)
    fname=f2 + '\\' + str(m) + '_' + str(d) + '.csv'
    if not(os.path.isdir(f1)):
        os.mkdir(f1)
        
    if not(os.path.isdir(f2)):
        os.mkdir(f2)

    return fname
 
# Write the temperature and relative humidites to file   
def doLog(temps,rhs): 

    tnow=datetime.datetime.now()
    tlabel=tnow.strftime("%m/%d/%Y, %H:%M:%S")
    # Format the data
    data=[tlabel]
    for T,RH in zip(temps,rhs):
        data.append(str(round(T,2)))
        data.append(str(round(RH,2)))

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
        with open(fname,'a') as f:
            writer = csv.writer(f)
            writer.writerow(data)
            
    else:
        with open(fname,'w') as f:
            writer = csv.writer(f)
            print('Overwriting old log file as headers dont agree')
            writer.writerow(fields)  
            writer.writerow(data)

#===========================================================
# FTP STuff
#===========================================================


def ftpupdate(Ts,RHs):
    fname='temp_humiditiy'
    file=open(fname,'w+')
    
    file.write(strftime('%Y/%m/%d %I:%M:%S %p') +'\n')
    for T,RH,s in zip(Ts,RHs,sensors):
        file.write(s.name + ',' + str(round(T,2)) + \
            ',' + str(round(RH,2)) + '\n')
   
    file.close()    
    filename=fname
    with open(filename, "rb") as file:
        
    # use FTP's STOR command to upload the file
        ftp.storbinary("STOR %s" % filename, file)
#

#===========================================================
# Update Function
#===========================================================

tLastRead = datetime.datetime.now().timestamp() - 10000
def timeUpdate():
    global tLastRead
    tNow = datetime.datetime.now().timestamp()
                
    # Update the clock 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string)    

    if ((tNow-tLastRead) > 10):
        update()
        tLastRead = tNow
    m2.after(500, timeUpdate)     

tVec=np.array([]) 
sendAlarm=False
talarm=datetime.datetime.now()
talarm=talarm.timestamp()-10000
def update():
    # Initialize global variables (clunky)
    global talarm               # Last time an alarm was sent
    global sendAlarm    
    alarm=False;    

    try:
        # Read all sensor data
        Ts,RHs=readSensors()        
    
        # Log the sensor data
        doLog(Ts,RHs)
        
        if doFTP:      
            try: 
                ftpupdate(Ts,RHs)
            except:
                print("unable to update ftp")    
                ftp.quit()
            
        msgs=[]    
        mainStr = strftime('%Y.%m.%d %I:%M:%S %p') + '\n'
        
        # Iterate over each sensor to update graphics
        for T,RH,s in zip(Ts,RHs,sensors):  
            mainStr = mainStr + (s.name).ljust(30,' ') + \
                "{0:.2f}".format(T) + ' C' + '     ' \
                "{0:.2f}".format(RH) + '%' + '\n'
           
            # Check for alarms trips
            if T<s.TLIM[0]:        
                alarm=True              
                msg=("Warning : " + s.name + " temperature too low at " + 
                    str(round(T,2)) + " C." + " (SP: " + str(round(s.TLIM[0],2)) + " C)")
                msgs.append(msg)
            if T>s.TLIM[1]:
                alarm=True
                msg=("Warning : " + s.name + " temperature too high at " + 
                    str(round(T,2)) + " C." + " (SP: " + str(round(s.TLIM[1],2)) + " C)")
                msgs.append(msg)             
            if RH<s.RLIM[0]:
                alarm=True
                msg=("Warning : " + s.name + " relative humidity too low at " + 
                    str(round(RH,2)) + "%." + " (SP: " + str(round(s.RLIM[0],2)) + " %)")
                msgs.append(msg)            
            if RH>s.RLIM[1]:
                alarm=True
                msg=("Warning : " + s.name + " relative humidity too high at " + 
                    str(round(RH,2)) + "%." + " (SP: " + str(round(s.RLIM[1],2)) + " %)")
                msgs.append(msg)
            
                
        if alarm:
            tAlarmNow=datetime.datetime.now().timestamp()
            if tAlarmNow-talarm>30*60:            
                mstr = "Supressing alarm for 30 minutes"
                msg = '\n'.join(msgs)  
                msg = '\n'.join([msg, mstr])     
                if doSlack:
                    try:
                        slackMessage(msg)
                    except:
                        print('unable to send slack message')
                        
                talarm=tAlarmNow
                
        m2.config(text=mainStr,justify='l',bg="white")
    except:
        m2.config(bg="red")
        time.sleep(1)
           
         
#===========================================================
# Main GUI
#===========================================================
# Main window
app = tkinter.Tk()
app.title("Room Temperature and Humidity")
app.geometry("700x300")


# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",
                    bg="white",font=("DejaVu Sans Mono",18))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,
                fill="both",side="top")

# Main String
m2 = tkinter.Label(left_frame,text="text",bg="white",
                   font=("Courier New",16))
m2.pack(side="left",anchor='nw')    

# Wait a hot second
time.sleep(.5)

#===========================================================
# Main Loop
#===========================================================

# Connect to FTP server
if doFTP:
    ftp=FTP(sname)
    ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))


# Initiate clock fucntions
timeUpdate()

#Start the GUI (dont know what this really does)
app.mainloop()

# Close the labjack
print("Closing the labjack") 
ljm.close(T7)
print("I think the labjack closed?")

# Close FTP connection
if doFTP:
    ftp.quit()