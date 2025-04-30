#loc='/dev/ttyUSB0'# location of serial device
loc='COM4'

# Import packages
import serial
import time
import tkinter
from time import strftime


import sys
sys.path.append("X:\\LabJackLogs\\_labjack_keys")
from key_ThermoFlex import *


# Close serial connection if open
ser=serial.Serial(port=loc,baudrate=9600)
if ser.isOpen():
    ser.close()


def readSW(s):
    msg1 = [0xCA,0x00,0x01,0x02,0x00]    
    csum = checkSum(msg1)
    msg2= msg1 + [csum]
    s.flush()
    s.write(bytearray(msg2))
    time.sleep(1)
    out = s.read(s.inWaiting())
    
    if goodCheckSum(out):
        out = out[5:-1]
        out = out.decode("utf-8")
    else:
        out = 'UNABLE TO READ SOFTWARE VERSION'
    
    return out
    
# Read data from the chiller
def readData(s,msg):
    cs = checkSum(msg)
    msg = msg + [cs]
    #time.sleep(.05)
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.2)
    out = s.read(s.inWaiting())

    if (len(out)==9) & (goodCheckSum(out)):
        val,unit = processData(out[5:-1])     
    else:
        val=0
        unit='?'  
    return val,unit
    
# Read pressure
def readPressure(s):    
    msg = [0xCA, 0x00,0x01,0x28,0x00]
    val,unit = readData(s,msg)
    return val, unit 

# Read the flow rate
def readFlow(s):    
    msg = [0xCA, 0x00,0x01,0x10,0x00]
    val,unit = readData(s,msg)
    return val, unit
    
# Read the water temepture    
def readTemp(s):    
    msg = [0xCA, 0x00,0x01,0x20,0x00]
    val,unit = readData(s,msg)
    return val, unit 
 
# Read the set point  
def readSP(s):    
    msg = [0xCA, 0x00,0x01,0x70,0x00]
    val,unit = readData(s,msg)
    return val, unit     

# Process data string    
def processData(x):
    # PYTHON 3
    val = x[1:]
    val = int.from_bytes(val,byteorder='big',signed=False)       
    qB = x[0]
       
    
    pNib = qB >> 4              # Precision nibble
    uNib = qB & 0x0F            # Unit nibble
    
    # Calculate value by inserting deciaml point (exponentiation had some precision issues? IDK)
    val = str(val) 
    val = val[:-pNib] + '.' + val[-pNib:]
    val = float(val)    

    units=['?','C','F','lpm','gpm','?','psi','bar']
    unit=units[uNib]

    return val,unit
    
# Perform check sum on decimal list
def checkSum(msg):
    out = sum(msg[1:])
    out = out & 0xFF
    out = out ^ 0xFF
    return out
    
# Perform check sum on string, skip firsta and last bytes PYTHON 3
def goodCheckSum(x):
    s = sum(x[1:-1])
    s = s & 0xFF
    s = s ^ 0xFF
    return s == x[-1]    
    

## Clock update function
def timeClock(): 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string) 
    lbl.after(100, timeClock) 
    
# Data update function
def timeUpdate(): 
    P,Pu = readPressure(ser)
    F,Fu = readFlow(ser)
    T,Tu = readTemp(ser)
    S,Su = readSP(ser)   
    string = \
        'Pressure    : ' + str(P) + ' ' + Pu + '\n' + \
        'Flow Rate   : ' + str(F) + ' ' + Fu + '\n' + \
        'Temperature : ' + str(T) + ' ' + Tu + '\n' + \
        'Set Point   : ' + str(S) + ' ' + Su
    m2.config(text=string,justify='l')
    
    #t = time.time()
    try:
        fname='gorilla'
        file=open(fname,'w+')
        file.write(strftime('%Y/%m/%d %I:%M:%S %p') +'\n')
        file.write(str(P) + ' ' + Pu + '\n')
        file.write(str(F) + ' ' + Fu + '\n')
        file.write(str(T) + ' ' + Tu + '\n')
        file.write(str(S) + ' ' + Su)
        file.close()
        
        filename=fname
        with open(filename, "rb") as file:
            # use FTP's STOR command to upload the file
            ftp.storbinary("STOR %s" % filename, file)  
            #elapsed = time.time() - t
                #print(elapsed)
    except:
        pass

    m2.after(2000, timeUpdate) 
 
################################
#FTP TESTING

import base64
from ftplib import FTP


try:
    ftp=FTP(sname)
    ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))
    #ftp.retrlines('LIST')
except:
    pass

 

####################################################
# Create GUI
####################################################
# Main window
app = tkinter.Tk()
app.title('ThermoFlex 1400')
app.geometry("350x150")


# Clock Frame
top_frame = tkinter.Frame(app,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock 
lbl = tkinter.Label(top_frame,text="Hello",bg="white",font=("DejaVu Sans Mono",18))
lbl.pack(side="left",anchor="nw")

# Data Frame
left_frame = tkinter.Frame(app,bd=1,bg="white")
left_frame.pack(anchor="nw",expand=True,fill="both",side="top")


m2 = tkinter.Label(left_frame,text="text",bg="white",font=("Courier New",18))
m2.pack(side="left",anchor='nw')    


# Perform basic communication test
print('Opening RS232 to chiller on ' + loc)
ser.open()
ser.flush()
sw='Thermotek Software Version : ' + readSW(ser)
time.sleep(.2)
P,Pu = readPressure(ser)
F,Fu = readFlow(ser)
T,Tu = readTemp(ser)
S,Su = readSP(ser)    
    
print(sw)
print('Pressure    ' + str(P) + ' ' + Pu)    
print('Flow        ' + str(F) + ' ' + Fu)    
print('Temperature ' + str(T) + ' ' + Tu)    
print('Set Point   ' + str(S) + ' ' + Su)    
  
# Initiate clock fucntions
timeClock()
timeUpdate()

#Start the GUI (dont know what this really does)
app.mainloop()

print("Closing serial connection with chiller")
ser.close()    
print("goodbye")

