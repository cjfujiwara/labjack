loc='/dev/ttyUSB1'# location of serial device

# Import packages
import serial
import time
import tkinter
from time import strftime
import os
import datetime
import csv


# Close serial connection if open
ser=serial.Serial(port=loc,baudrate=9600)
if ser.isOpen():
    ser.close()
    
def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False
    
def setMode(s):
    msg = [0x40,0x51,0x0D,0x0A] #  @ \x51 \r\n Query Mode
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.2)
    s.flush()
    s.read(s.inWaiting())
    s.flush()

    msg = [0x40, 0x44,0x0D,0x0A] #  @ \x44 \r\n Deviation On (analog out)
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.2)   
    s.flush()
    s.read(s.inWaiting())
    s.flush()

def getData(s):
    msg = [0x40, 0x51,0x0D,0x0A] #  @ \x51 \r\n Query Mode
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.2)
    out = s.read(s.inWaiting())
    s.flush()
    
    out = out[:-2]
    out = out.decode('UTF-8')
    out = out.split(',')
    
    if out[0] :
    
        status = processStatus(out[0])
        unit,display,medium,resolution,averaging = processStateLEDs(out[1])    
       # mode = processSysLEDs(out[2])
    else:
        status = 'BAD'
        unit = '??'
        display = '??'
        medium = '??'
        resolution = '??'
        averaging = '??'
        
        
            
    
    
    return status,unit,display,medium,resolution,averaging
    
def processStatus(instr):
    if ((instr[0]=='+') or (instr[0]=='-')):
        if isfloat(instr):
            return float(instr)
        else:
            return instr[1:].strip()
    else:
        return 'BAD'    
    
    
    
# According to the manual
#  
# UNITS - nm                0x0009 b00 00 00 00 001001
# UNITS - cm-1              0x0012 b00 00 00 00 010010
# UNITS - GHz               0x0024 b00 00 00 00 100100
# DISPLAY - Wavelength      0x0040 b00 00 00 01 000000
# DISPLAY - Deviation       0x0080 b00 00 00 10 000000
# MEDIUM - Air              0x0100 b00 00 01 00 000000
# MEDIUM - Vacuum           0x0200 b00 00 10 00 000000
# RESOLUTION - Fixed        0x0400 b00 01 00 00 000000
# RESOLUTION - Auto         0x0800 b00 10 00 00 000000
# AVERAGING - On            0x1000 b01 00 00 00 000000
# AVERAGING - Off           0x2000 b10 00 00 00 000000
def processStateLEDs(instr):
    unitMask = [0x0009, 0x0012, 0x0024] # nm, cm-1, GHz
    unitLbl = ["nm","cm-1","GHz"]
    unit = "??"
    
    dispMask = [0x0040, 0x0080]         # wavelength, deviation
    dispLbl = ["absolute","deviation"]
    display = "??"
    
    mediMask = [0x0100, 0x0200]         # air, vacuum     
    mediLbl = ["air","vacuum"]
    medium = "??"
    
    resoMask = [0x0400, 0x800]          # fixed, auto
    resoLbl = ["fixed","auto"]    
    resolution = "??"
    
    avgeMask = [0x1000, 0x2000]         # avg on, avg off
    avgeLbl = ["on","off"]
    average = "??"
    
    for m,lbl in zip(unitMask,unitLbl):
        if (int(instr,16) & m):
            unit = lbl
            
    for m,lbl in zip(dispMask,dispLbl):
        if (int(instr,16) & m):
            display = lbl
            
    for m,lbl in zip(mediMask,mediLbl):
        if (int(instr,16) & m):
            medium = lbl
            
    for m,lbl in zip(resoMask,resoLbl):
        if (int(instr,16) & m):
            resolution = lbl
            
    for m,lbl in zip(avgeMask,avgeLbl):
        if (int(instr,16) & m):
            average = lbl    
            
    return unit, display, medium, resolution, average
    
    
# DISPLAY RES               0x0001
# SETPOINT                  0x0002
# # AVERAGED                0x0004
# ANALOG RES                0x0008
# PRESSURE                  0x0010
# TEMPERATURE               0x0020
# HUMIDITY                  0x0040
# QSETUP Restore/Save       0x0080
# REMOTE                    0x0100
# INPUT ATTENUATOR Auto     0x0200
# INPUT ATTENUATOR Manual   0x0400 
def processSysLEDs(instr):
    mask = [0x0001,0x0002,0x0004,0x0008,0x0010,0x0020,0x0040,0x0080,0x0100,0x0200,0x0400]
    modes = ["display resolution","setpont","# averaged", "analog resolution", "pressure", "temperature", "humidity","qsetup restore/save","remote","attenuator auto","attenuator manual"]
    mode = "normal"
    
    for m,lbl in zip(mask,modes):
        if (int(instr,16) & m):
            mode = lbl
    
    
    return mode
#====================================================================
# CSV Logging
#====================================================================

fields=['time']
fields.append('frequency (GHz)')

drv='/mnt/Y/'
fldr='LabJack/Logging/WA-1000'

# Get the full file name of the log
def getLogName():
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
def doLog(freq): 

    tnow=datetime.datetime.now()
    tlabel=tnow.strftime("%m/%d/%Y, %H:%M:%S")
    
    # Format the data
    data=[tlabel]
    data.append(str(freq))

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


## Clock update function
def timeClock(): 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string) 
    lbl.after(100, timeClock) 
    
# Data update function
def timeUpdate(): 
    status,unit,display,medium,resolution,averaging = getData(ser)
    
    if (status != 'BAD'):        
        try:
            rStr = "Measure    : " + str(status) + " " + unit + '\n' + \
                "Display    : "   + display + '\n' + \
                "Medium     : " + medium + '\n' + \
                "Resolution : " + resolution + '\n' + \
                "Averaging  : "  + " " + averaging + '\n'
        
        
            m2.config(text=rStr,justify='l')
            
            string = strftime('%Y.%m.%d %I:%M:%S %p') 
            lbl.config(text = string) 
            
            try:
                
                freq = float(status)
            
                #doLog(freq)
            except:
                print('unable to write log frequency')
        except:
            print('problem')
    
    #t = time.time()
    #try:
    #    fname='gorilla'
    #    file=open(fname,'w+')
    #    file.write(strftime('%Y/%m/%d %I:%M:%S %p') +'\n')
    #    file.write(str(P) + ' ' + Pu + '\n')
    #    file.write(str(F) + ' ' + Fu + '\n')
    #    file.write(str(T) + ' ' + Tu + '\n')
    #    file.write(str(S) + ' ' + Su)
     #   file.close()
        
     #   filename=fname
     #   with open(filename, "rb") as file:
        # use FTP's STOR command to upload the file
      #      ftp.storbinary("STOR %s" % filename, file)  
        #elapsed = time.time() - t
            #print(elapsed)
    #except:
    #    pass

    m2.after(200, timeUpdate) 
 
################################
#FTP TESTING

#import base64
#from ftplib import FTP
#pw='SWxpa2VyYXRzYW5kY2F0c3ZlcnltdWNo='
#un='fujiwa27'
#sname='individual.utoronto.ca'

#ftp=FTP(sname)
#ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))
#ftp.retrlines('LIST')

 

####################################################
# Create GUI
####################################################
# Main window
app = tkinter.Tk()
app.title('WA-1000')
app.geometry("400x200")


# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",bg="white",font=("DejaVu Sans Mono",18))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,fill="both",side="top")


m2 = tkinter.Label(left_frame,text="text",bg="white",font=("DejaVu Sans Mono",18))
m2.pack(side="left",anchor='nw')    

time.sleep(.5)

# Perform basic communication test
print('Opening RS232 to WA-1000 on ' + loc)
ser.open()
ser.flush()
setMode(ser)
ser.flush()
time.sleep(.2)

  
# Initiate clock fucntions
#timeClock()
timeUpdate()

#Start the GUI (dont know what this really does)
app.mainloop()



print("Closing serial connection with wavemeter")
ser.close()    
print("goodbye")

