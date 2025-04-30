loc='/dev/ttyUSB0'# location of serial device

from time import strftime
import serial
import time
import tkinter


ser=serial.Serial(port=loc,baudrate=9600)
if ser.isOpen():
    ser.close()

    
# Read temperature data from the chiller
def readTempData(s,msg):
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.15)
    out = s.read(s.inWaiting())    
    #print(out)
    val = int.from_bytes(out,byteorder='little',signed=False)  
    Tf = float(val)/10
    Tc = (Tf-32)*(5/9)
    Tc = round(Tc,1)  

    return Tc

# Read the water temepture    
def readTemp(s):    
    msg = [0x49]
    val = readTempData(s,msg)
    return val 
 
# Read the set point  
def readSP(s):    
    msg = [0x41]
    val = readTempData(s,msg)
    return val     
    
def readFault(s):
    msg = [0x48]
    s.flush()
    s.write(bytearray(msg))    
    time.sleep(.15)
    out = s.read(s.inWaiting())    
    val=int.from_bytes(out,byteorder='big',signed=False)
    
    string='Unrecognized'
    if val==0:
        string = 'None'
    if val==1:
        string = 'Tank Level Low'
    if val==2:
        string = 'Fan Fail'
    if val==8:
        string = 'Pump Fail'
    if val==16:
        string = 'RTD Open'
    if val==32:
        string = 'RTD Short'
    return string

## Clock update function
def timeClock(): 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string) 
    lbl.after(100, timeClock) 
    
# Data update function
def timeUpdate(): 
    T = readTemp(ser)
    S = readSP(ser)    
    F = readFault(ser)
    
    try:    
        ftpupdate(T,S,F)
    except:
        pass
    
    string = \
        'Temperature : ' + str(T) + ' C\n' + \
        'Set Point   : ' + str(S) + ' C\n' + \
        'Faults      : ' + F

    m2.config(text=string,justify='l')
    m2.after(2000, timeUpdate) 
################################
#FTP TESTING

import base64
from ftplib import FTP
pw='SWxpa2VyYXRzYW5kY2F0c3ZlcnltdWNo='
un='fujiwa27'
sname='individual.utoronto.ca'

ftp=FTP(sname)
ftp.login(user=un,passwd=base64.b64decode(pw).decode('utf-8'))
#ftp.retrlines('LIST')

def ftpupdate(T,S,F):
    fname='thermocube_nufern'
    file=open(fname,'w+')
    file.write(strftime('%Y/%m/%d %I:%M:%S %p') +'\n')

    file.write(str(T)+'\n')
    file.write(str(S)+'\n')
    file.write(str(F))
    file.close()
    
    filename=fname
    with open(filename, "rb") as file:
    # use FTP's STOR command to upload the file
        ftp.storbinary("STOR %s" % filename, file)
#    
####################################################
# Create GUI
####################################################
# Main window
app = tkinter.Tk()
app.title('ThermoCube')
app.geometry("350x120")


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

# Perform basic communication test
print('Opening RS232 to chiller on ' + loc)
ser.open()
ser.flush()
time.sleep(.2)
T = readTemp(ser)
S = readSP(ser)    
    
print('Temperature ' + str(T) + ' C')    
print('Set Point   ' + str(S) + ' C')    
  
    
  
# Initiate clock fucntions
timeClock()
timeUpdate()

#Start the GUI (dont know what this really does)
app.mainloop()

print("Closing serial connection with chiller")
ser.close()    
print("goodbye")
ftp.quit()
