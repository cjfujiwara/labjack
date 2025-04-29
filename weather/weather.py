#===========================================================
# weather.py
#===========================================================

# For information on API response and formatting, see the following website
# This program uses the free weather API open weathermap.org  which allows for 
# 1000 API calls per day, which is 86.4 seconds/call. Therefore, this program
# heavily undersamples at once every ten minutes (144 calls/day)
#https://openweathermap.org/current
#===========================================================
# Settings
#===========================================================

drv = 'X:\\'
fldr = 'LabJackLogs\\Temperature-Humidity'

import sys
sys.path.append("X:\\LabJackLogs\\_labjack_keys")
from key_weather import *


#===========================================================
# Packages
#===========================================================
import time
import requests
import datetime
import csv
import os
import tkinter
from time import strftime

#===========================================================
# API Log 
#===========================================================

def doLog():    
    settings = {
        'api_key': mykey,
        'city': mycity,
        'country_code': mycountry,
        'temp_unit': myunit} #unit can be metric, imperial, or kelvin    
    BASE_URL = "http://api.openweathermap.org/data/2.5/" + \
        "weather?appid={0}&q={1},{2}&units={3}"    
    
    # API URL request
    final_url = BASE_URL.format(settings["api_key"],
                                settings["city"],
                                settings["country_code"],
                                settings["temp_unit"])    
    weather_data = requests.get(final_url).json()  
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    dt = weather_data['dt']   
    tStr = time.strftime("%m/%d/%Y, %H:%M:%S",time.localtime(int(dt))) 
    
     # Get the log name file
    fname=getLogName()
        
    if not(os.path.isfile(fname)):
        with open(fname,'w') as f:
            print('Making new log file')
        
    # Check if the existing file has the correct headeres
    with open(fname,'r') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        
    fields = ['time','temperature_C','humidity_percent']
    data = [tStr,float(temp),float(humidity)]
    
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
            
    mainStr = tStr + '\n' + \
        'temperature : ' + "{0:.2f}".format(float(temp)) + ' C \n' +\
        'humidity    : ' + "{0:.2f}".format(float(humidity)) + '%'
    return mainStr
    
    
#===========================================================
# Get Log File Name
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
    
    
#===========================================================
# Update Function
#===========================================================
tLog=datetime.datetime.now()
tLog=tLog.timestamp()-100000
def timeUpdate():   
    global tLog         
    # Update the clock 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string)  
    
    tLogNow=datetime.datetime.now().timestamp()
    if tLogNow-tLog>10*60:    
        # Log the sensor data
        mainStr = doLog() 
        m2.config(text=mainStr,justify='l')
        tLog = tLogNow
            
    m2.after(1000, timeUpdate) 
           
         
#===========================================================
# Main GUI
#===========================================================
# Main window
app = tkinter.Tk()
app.title("Toronto Weather")
app.geometry("400x160")


# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",bg="white",
                    font=("DejaVu Sans Mono",20))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,fill="both",side="top")

# Main Text
m2 = tkinter.Label(left_frame,text="text",bg="white",
                   font=("Courier New",18))
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
