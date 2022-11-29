# labjackCurrentMonitor.py
#
# Author : C Fujiwara
#d
# This code runs a GUI which allows for monitoring of the transport currents 
# a labjack T7.  In the laboratory we have current monitors which output a 
# voltage proportional to the current.  The ADCs on a T7 pro are 16bit on a 
# range of +-10V.
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
print("labjackCurrentMonitor.py")

print("Loading packages ...")
# Import packages
import sys
from datetime import datetime
from time import strftime
from labjack import ljm
import ljm_stream_util
from matplotlib.figure import Figure
import numpy as np
import threading
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
import tkinter as tk
import scipy.io
import time

####################################################
# Settings
####################################################

# Labckjack configuration
t7name="CurrentMonitor"
myip="192.168.1.124"

# Digital trigger channel
TRIGGER_NAME='DIO0' # aka DIO0, must be DIO0 or DIO1 for triggered stream

# Analog channels to measure
aScanListNames = ["AIN0"]  
numAddresses = len(aScanListNames)

# Names for each analog channel
names = ["cavity"]
         
# ONLY ONE         
# Analog channels to measure
#aScanListNames = ["AIN0"]  
#numAddresses = len(aScanListNames)
# Names for each analog channel
#names = ["Push"]
         
# Default Data acquistiion speed
scanRate = 10000  # Scans per second
numScans = 1000  # Number of scans to perform

# The total sample rate is scanRate * numAdresses and cannot exceed 120 kHz

# gui title
figtitle="Labjack Transport Current Monitor"

# Plotting options
vLim=[-.05, 1.2]      # Voltage y limits
rLim=[-.1, .1]      # Residue Y limits

# Default filename when saving
defaultFname='currentMonitorData.mat'

# Default reference data to load
#defaultRefFile='currentMonitorData.mat'

# Colors and dash types     
myc=['#e41a1c',
     '#377eb8',
    '#4daf4a',
    '#984ea3',
    '#ff7f00',
    '#ffff33']
myd=[[5,1],[3,1,1,1],'']

####################################################
# Load default data
####################################################


#except Exception:
#print("Unable to load reference data, loading dummy data.")
e = sys.exc_info()[1]
print(e)
REFDATA=np.zeros((5,1))
REFTIME=np.zeros((5,1))

# Initialize plotting global variables
PLOTDATA=np.zeros((5,1))
PLOTTIME=np.zeros((5,1))

tAcq="NONE"

####################################################
# Information on Burst Stream
####################################################
# Using software commands to read analog channels is prone to mistimings and
# slow downs due to OS <--> labjack communication. A more robust way of 
# handling timing is use the internal labjack clock to initiated ADC reads and
# then read out the voltages post acquisition. This is known as stream mode
# and makes the lab jack perform most similarly to an oscilloscope. This 
# acquisition can also be externally triggered from FIO0 or FIO1
#
# At lowest gain and resolution, the maximum speed is 100kHz (0.01ms/sample) with
# and effective speed of 6.25 kHz (0.16 ms/sample) for 16 channels.
#
# In practice, the labjack has a finite memory so reads from the OS must be 
# done in parallel with the stream acquisition. According to the manual: 
#
# "When stream is running, there are two sample buffers to consider: the 
# device buffer and the LJM buffer. After starting stream:

# 1) The device acquires a scan of stream data at every scan interval according
#       to its own clock and puts that data into the device buffer.
# 2) At the same time, LJM is running a background thread that moves data from 
#       the device buffer to the LJM buffer.
# 3) At the same time, the user application needs to move data from the LJM 
#       buffer to the user application—this is done using LJM_eStreamRead or 
#       LJM_eStreamBurst."
#
# Our application is high-throughput application with very little latency requirement.
# In otherwords, we have a lot data, but it doesn't need to be analzyed quickly.
# (ie. we use it as a scope)
#
# Example code made by found in the LJM API provided under stream_triggered.py

####################################################
# Labjack Functions
####################################################

# Grab the current time
tnow=datetime.now()

# Open the ab jack
def openLabJack():
   
    print("Opening labjack on ..."+myip)
    handle=ljm.openS("T7","ETHERNET",'470026765')
    #handle=ljm.openS("T7","ETHERNET", myip)# Connect via ip address (faster)
    
    # Try to close stream in case it is running
    try:
        ljm.eStreamStop(handle)   
    except ljm.LJMError:
        pass
    except Exception:
        pass
    
    # Display labjack information
    info = ljm.getHandleInfo(handle)
    print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
          "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
          (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
    
    # By default, configure to software trigger by default
    ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)   # No external trigger
    
    # Stream is timed by internal clock
    ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)    # Internal clock stream
        
    # All negative channels are single-ended, AIN0 and AIN1 ranges are
    # +/-10 V, stream settling is 0 (default) and stream resolution index
    # is 0 (default).
    aNames = ["AIN_ALL_NEGATIVE_CH", "AIN0_RANGE", "AIN1_RANGE",
              "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
    numFrames = len(aNames)
    aValues = [ljm.constants.GND, 10.0, 10.0, 0, 0]      
    
    # Write the analog inputs' negative channels (when applicable), ranges,
    # stream settling time and stream resolution configuration.
    ljm.eWriteNames(handle, numFrames, aNames, aValues)    
    
    # Write GUI connection string
#    lblJack.config(text="%s %s" % (t7name, ljm.numberToIP(info[3])))    
    lblJack.config(text="%s %s" % (t7name, myip))           
    return handle


# Initialize burst stream 
# This is a simplified version of burstStream that automatically
# configures eStreamStart, eStreadRead,and eStreamStop'
# REMOVING AS TRIG STREAM CAN ALSO DO SOFTWARE TIRG
"""
def burstStream(handle):
    aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]  # Scan list addresses for streamBurst       
    # Get the scan rate (Hz) and number of total samples    
    scanRate=float(e1.get())
    numScans=int(e2.get())
    
    # Make sure no external trigger
    ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)   # No external trigger
    
    # Ensure triggered stream is disabled.
    ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

    # Enabling internally-clocked stream.
    ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)
  
    print("")
    print(" Desired Scan rate        : %s Hz" % scanRate)
    print(" Number of Channels       : %s " % len(aScanList))
    print(" Total Sample rate        : %s Hz" % (scanRate * numAddresses))
    print(" Total number of scans    : %s" % numScans)
    print(" Total number of samples  : %s" % (numScans * numAddresses))
    print(" Total Duration           : %s sec" % (numScans / scanRate))

    print("\nStreaming with streamBurst ...")
    start = datetime.now()
    scanRateOut, aData = ljm.streamBurst(handle, numAddresses, aScanList, scanRate, numScans)
    end = datetime.now()
    print("Done")

    skipped = aData.count(-9999.0)
    print("\n Skipped scans            : %0.0f" % (skipped / numAddresses))
    tt = (end - start).seconds + float((end - start).microseconds) / 1000000
    print(" Time taken               : %.2f seconds" % (tt))
    print(" Scan Rate Out            : %s Hz" % scanRateOut)
    
    tVec= np.array(range(numScans))/scanRateOut

    data = np.zeros((numScans,len(aScanListNames)))
    for j in range(len(aScanListNames)):
        data[:,j]=aData[j::len(aScanListNames)]

    return tVec,data    
"""
   
def burstStream(handle,isTrig):   
    # Scan list addresses for streamBurst      
    aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]   
    
    # Get the scan rate (Hz) and number of total samples    
    scanRate=float(e1.get())
    numScans=int(e2.get())
    
    # Scan per read (labjack says a safe value is 1/2, but you can change)
    scansPerRead=int(scanRate/2)        
        
    # Ensure triggered stream is disabled.
    ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", 0)

    # Enabling internally-clocked stream.
    ljm.eWriteName(handle, "STREAM_CLOCK_SOURCE", 0)      
    
    # Display acquisition settings
    print("\n " + "Scan rate".ljust(20) + ": %s Hz" % scanRate)
    print(" " + "Number of Scans".ljust(20) + ": %s" % numScans)
    print(" " + "Total Duration".ljust(20) + ": %s sec" % (numScans / scanRate)) 
    print(" " + "Scans per read".ljust(20) + ": %s" % scansPerRead) 
    print(" " + "Number of Channels".ljust(20) + ": %s" % len(aScanList))
    print(" " + "Total Sample rate".ljust(20) + ": %s Hz" % (scanRate * numAddresses))    
    
    
    # Configure trigger if appropriate    
    if (isTrig):
        print(" " + "Trigger".ljust(20) + ": %s" % TRIGGER_NAME)    
        # Configure pin for triggers
        configureDeviceForTriggeredStream(handle, TRIGGER_NAME)        
        # SEtup timeouts and what not (not sure how this works)
        configureLJMForTriggeredStream()         
        print("\nWaiting for trigger")
        lbl2.config(text="Waiting for trigger ...",bg="orange")    
    else:
        print(" " + "Trigger".ljust(20) + ": %s" % "Software")      
        lbl2.config(text="Starting burst stream ...",bg="orange")   
        
        
    if scanRate*numAddresses>90000:
        print("You cannot request total sample rates >90kHz!. Aborting")
        return 0,0,False
    
    # Initilize Counters
    totScans = 0            # Total scans read
    totSkip = 0             # Total skipped samples
    i = 1                   # Number of reads
    ljmScanBacklog = 0      # Backlog on the LJM
    dataAll=[]              # All data
    isGood=True
    
    # Configure and start stream
    scanRate = ljm.eStreamStart(handle, scansPerRead, numAddresses, aScanList, scanRate)    
    while (totScans < numScans) & isGood:
        ljm_stream_util.variableStreamSleep(scansPerRead, scanRate, ljmScanBacklog)
        try:
            ret = ljm.eStreamRead(handle) # read data in buffer

            # Recrod the data
            aData = ret[0]
            ljmScanBacklog = ret[2]
            scans = len(aData) / numAddresses
            totScans += scans 
            dataAll+=aData
            
            #
            lbl2.config(text="Data stream in progress ... (%i of %i scans)" % (totScans,numScans),bg="red")   

            
            # Count the skipped samples which are indicated by -9999 values. Missed
            # samples occur after a device's stream buffer overflows and are
            # reported after auto-recover mode ends.
            curSkip = aData.count(-9999.0)
            totSkip += curSkip

            # Report on acquisition
            print("eStreamRead %i : %i scans, %0.0f scans skipped, %i device backlog, %i in LJM backlog" % (i,totScans, curSkip/numAddresses, ret[1], ljmScanBacklog))
            
            # Increment read counter    
            i += 1
        except ljm.LJMError as err:
            if err.errorCode == ljm.errorcodes.NO_SCANS_RETURNED:     
                #sys.stdout.write('.')
                sys.stdout.flush()
                continue
            else: 
                ljme = sys.exc_info()[1]
                print(ljme)
                isGood=False  
    lbl2.config(text="Data acquired. Closing data stream",bg="yellow")

    # Update acquisition    
    global tAcq
    
    tAcq = strftime('%Y-%m-%d_%H-%M-%S') 
    
    if isGood:
        lblacq.config(text="Last Acq :" + tAcq)
    
    print("Closing data stream ... ")
    # Stop the stream
    try:
        #print("\nStopping Stream")
        ljm.eStreamStop(handle)   
    except ljm.LJMError:
        ljme = sys.exc_info()[1]
        print(ljme)
    except Exception:
        e = sys.exc_info()[1]
        print(e)      
    
    # Initializeoutput data    
    tVec= (np.array([range(numScans)]).T)/scanRate
    data = np.zeros((numScans,len(aScanListNames)))

    if isGood:
        # Print Summary
        print("\nTotal scans = %i" % (totScans))
        print("Skipped scans = %0.0f" % (totSkip / numAddresses))

        if (len(dataAll)/numAddresses)!=numScans:
            print("Truncating data")
            dataAll=dataAll[0:(numScans*numAddresses)]
            
        lbl2.config(text="Reshaping data ... ",bg="yellow")    

        print("Reshaping data ...")
        data=np.array(dataAll).reshape(numScans,numAddresses)   

    lbl2.config(text="Data acquisition complete.")
    return tVec,data,isGood   

def configureDeviceForTriggeredStream(handle, triggerName):
    """Configure the device to wait for a trigger before beginning stream.

    @para handle: The device handle
    @type handle: int
    @para triggerName: The name of the channel that will trigger stream to start
    @type triggerName: str
    """
    address = ljm.nameToAddress(triggerName)[0]
    ljm.eWriteName(handle, "STREAM_TRIGGER_INDEX", address);

    # Clear any previous settings on triggerName's Extended Feature registers
    ljm.eWriteName(handle, "%s_EF_ENABLE" % triggerName, 0);

    # 5 enables a rising or falling edge to trigger stream
    ljm.eWriteName(handle, "%s_EF_INDEX" % triggerName, 5);

    # Enable
    ljm.eWriteName(handle, "%s_EF_ENABLE" % triggerName, 1);
    
    
    
    
    
# I DONT UNDERSTAND WHAT THIS FUNCTION DOES
def configureLJMForTriggeredStream():
    ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
    ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)

    # By default, LJM will time out with an error while waiting for the stream
    # trigger to occur.

    
####################################################
# Callback functions
####################################################
  
  
def updateDataPlot(tVec,data):
    lbl2.config(text="Updating data plot objects ...",bg="yellow")
    print("Updating data plot objects ... ")
    global PLOTDATA
    
    global PLOTTIME 
    ax1.set_xlim(0,np.amax(tVec))
    #ax2.set_xlim(0,np.amax(tVec))
    for j in range(len(names)):
        plotsData[j].set_data(tVec,data[:,j])
    PLOTDATA=data
    PLOTTIME=tVec
    lbl2.config(text="Data plot objects updated.",bg="yellow") 


    
## Clock update function
def timeClock(): 
    string = strftime('%Y.%m.%d %I:%M:%S %p') 
    lbl.config(text = string) 
    lbl.after(200, timeClock) 

####################################################
# Create GUI and Frames
####################################################

print("Creating main GUI and frames ...")

# Create the main window
w=tk.Tk()
w.title(figtitle)
w.geometry("1400x1200")
w.configure(bg="yellow")

# Top frame bar
top_frame = tk.Frame(w,bd=1,bg="white")
top_frame.pack(anchor="nw",expand=False,fill="x",side="top")

# Add clock  
lbl = tk.Label(top_frame,text="Hello",bg="white",font=("calibri",18))
lbl.pack(side="left")

# Labjack connection info
lblJack=tk.Label(top_frame,text="NO LABJACK",bg="white",font=("calibri",18))
lblJack.pack(anchor="e",side="top")

# Another frame bar
top_frame2 = tk.Frame(w,bd=1,bg="white")
top_frame2.pack(anchor="nw",expand=False,fill="x",side="top")

# Status label
lbl2 = tk.Label(top_frame2,text="PROGRAM STARTINGs ...",bg="red",
                font=("calibri",12),anchor='sw')
lbl2.pack(side="top",fill="x",expand=1)

# Frame for data acquitision
top_frame3= tk.Frame(w,bd=1,bg="white")
top_frame3.pack(anchor="nw",expand=False,fill="x",side="top")


####################################################
# Create Figure Objects
####################################################
print("Making GUI buttons ...")

######################### Triggered acquisition button

# Callback for triggered acquisitino button
def trigAcqCB():
    #print("Triggered data acquisition.")
    bMan.configure(state="disabled")
    bSave.configure(state="disabled")
    bTrig.configure(state="disabled")
    bStop.configure(state="active")
    #bLoad.configure(state="disabled")

    # Start a new python thread
    trigAcqThread=threading.Thread(target=trigAcq)
    trigAcqThread.start()     

def trigAcq():
    lbl2.config(text="Initializing triggered burst stream ...",bg="orange")    
    tvec,data,isGood=burstStream(t7,1)
    
    if isGood:
        lbl2.config(text="Updating plots ...",bg="yellow") 
        updateDataPlot(tvec,data)
#        updateResiduePlot()   
        print('drawing')
        lbl2.config(text="Redrawing figure ...",bg='orange') 
        fig.canvas.draw()
        
        
    lbl2.config(text="Idle ...",bg="light green")      
    bMan.configure(state="active")
    bSave.configure(state="active")
    bTrig.configure(state="active")
    bStop.configure(state="disabled")    
    #bLoad.configure(state="active")
    time.sleep(.2)
    if isGood:
        print("Restarting trigger watch")
        lbl2.config(text="Restarting triggered acquisition ...",bg="orange")
        bMan.configure(state="disabled")
        bSave.configure(state="disabled")
        bTrig.configure(state="disabled")
        bStop.configure(state="active")
     #   bLoad.configure(state="disabled")
        trigAcq()
        
    

    
# Button for triggered acquisition
bTrig=tk.Button(top_frame3,text="start acq",bg="white",
               font=("calibiri",12),command=trigAcqCB)
bTrig.pack(side="left")   
    

######################## Manual acquisition button


def manAcqCB():
    #print("Manual data acquisition.")
    bMan.configure(state="disabled")
    bSave.configure(state="disabled")
    bTrig.configure(state="disabled")
    bStop.configure(state="active")
    #bLoad.configure(state="disabled")
    # Start a new python thread
    manAcqThread=threading.Thread(target=manualAcq)
    manAcqThread.start()    

def manualAcq():
    lbl2.config(text="Initializing manual burst stream ...",bg="orange")    
    tvec,data,isGood=burstStream(t7,0)
    
    if isGood:
        lbl2.config(text="Updating plots ...",bg="yellow") 
        updateDataPlot(tvec,data)
        #updateResiduePlot()
        print('drawing')
        lbl2.config(text="Redrawing figure ...",bg='orange') 
        fig.canvas.draw()

    lbl2.config(text="Idle ...",bg="light green")  
    bMan.configure(state="active")
    bSave.configure(state="active")
    bTrig.configure(state="active")
    bStop.configure(state="disabled")
#    bLoad.configure(state="active")
    print("ready")

  
bMan=tk.Button(top_frame3,text="force acq",bg="white",
          font=("calibiri",12),command=manAcqCB)
bMan.pack(side="left")


######################## Stop stream button
def stopAcqCB():
    print("\nStopping Stream")
    ljm.eStreamStop(t7)       

# Checkbutton for waiting for triggers
bStop=tk.Button(top_frame3,text="abort acq",bg="white",
          font=("calibiri",12),command=stopAcqCB,state="disabled")
bStop.pack(side="left")

bStop.configure(state="disabled")


######################### basic setttings entries
tk.Label(top_frame3,text="scan rate (Hz) ",bg="white").pack(side="left")

e1=tk.Entry(top_frame3,width=7)
e1.insert(10,"%s" % scanRate)
e1.pack(side="left",padx=7)

tk.Label(top_frame3,text="num scans (N) ",bg="white").pack(side="left")

e2=tk.Entry(top_frame3,width=7)
e2.insert(10,"%s" % numScans)
e2.pack(side="left",padx=7)


######################### Save data button, load data button, reference data
def saveDataCB():
    #filename="currentMonitorData.mat"
    #print("Saving plot data to " + filename + " ... ",end='')
    #scipy.io.savemat(filename,{"time":PLOTTIME,"data": PLOTDATA,"names":names})
    #print(" done.")
    file=tk.filedialog.asksaveasfile(defaultextension='.mat',filetypes=[
        ("mat file",".mat"),  
        ("All file",".*")],title="Save the data",
        initialfile=defaultFname)
        
    if file:
        print("Saving data to " + file.name + " ... ")
        scipy.io.savemat(file.name,{
            "AcquisitionDate": tAcq,
            "Time": PLOTTIME,
            "Data": PLOTDATA,
            "Names":names,
            "ScanRate": scanRate,
            "AINs": aScanListNames})
    else:
        print("File save canceled.")
     
bSave=tk.Button(top_frame3,text="save data",bg="white",
          font=("calibiri",12),command=saveDataCB)
bSave.pack(side='right')

def loadDataCB():
    global REFDATA
    global REFTIME
    file=tk.filedialog.askopenfile(defaultextension='.mat',filetypes=[
        ("mat file",".mat")],title="Load reference data")
        
    if file:
        print("Loading reference data from " + file.name + " ...")
        fdata=scipy.io.loadmat(file.name)        
        REFDATA=fdata['Data']
        REFTIME=fdata['Time'] 
        #updateResiduePlot()
        print("drawing")
        lbl2.config(text="Redrawing figure ...",bg="orange")
        fig.canvas.draw()
        lbl2.config(text="Idle ...",bg="light green")

    else:
        print("Load load canceled.")
    
#bLoad=tk.Button(top_frame3,text="load reference",bg="white",
#          font=("calibiri",12),command=loadDataCB)
#bLoad.pack(side='right')

lblacq = tk.Label(top_frame3,text="Last Acq :NONE ",bg="white",
                font=("calibri",12),anchor='sw')
lblacq.pack(side="left")

################################################
print("Initializing graphical plot objects ...")


# Make figure frame
bottom_frame = tk.Frame(w,bg="red")
bottom_frame.pack(side="top",expand=True,fill="both",anchor="n")

## Initialize plots
fig = Figure() # Initialize figure



#fig,(ax1,ax2)=plt.subplots(2,1)

fig.set_facecolor("white")

# Top Axes
ax1= fig.add_subplot(1,1,1)
ax1.set_ylabel("voltage (V)")
ax1.set_xlabel("time (s)")
ax1.xaxis.set_label_position("top")
ax1.xaxis.tick_top()
ax1.set_xlim(0,10)
ax1.set_ylim(vLim[0],vLim[1])
ax1.patch.set_facecolor('#D7D7D7')


# Bottom Axes
#ax2= fig.add_subplot(2,1,2)
#ax2.set_ylabel("residue (V)")
#ax2.set_xlabel("time (s)")
#ax2.set_xlim(0,10)
#ax2.set_ylim(rLim[0],rLim[1])
#ax2.patch.set_facecolor('#D7D7D7')


# Initialize dummy data
plotsData=[]
plotsRes=[]
for j in range(len(names)):
    plotsData.append(ax1.plot([],[],color=myc[j % len(myc)],linestyle='dashed',linewidth=2)[0])
    plotsData[j].set_dashes(myd[j // len(myc)])
    
    
    #plotsRes.append(ax2.plot([],[],color=myc[j % len(myc)],linestyle='dashed',linewidth=2)[0])
    #plotsRes[j].set_dashes(myd[j // len(myc)])


# Make the legend
myleg=fig.legend(plotsData,names,loc="center right",fontsize=10)
fig.subplots_adjust(left=.075, bottom=None, right=0.9, top=None, wspace=None, hspace=None)

for line in myleg.get_lines():
    line.set_linewidth(6.0)

canvas = FigureCanvasTkAgg(fig,master=bottom_frame)
canvas.draw()
canvas.get_tk_widget().pack(fill="both",expand=True)

fig.canvas.draw()

#bg1=fig.canvas.copy_from_bbox(ax1.bbox)
#bg2=fig.canvas.copy_from_bbox(ax2.bbox)

    
####################################################
# Application Start
####################################################


# Open the labjack
t7=openLabJack()

# Teset and print all channels
print(" ")
print("Testing read of all channels")
print(" " + "Trigger" .ljust(8) + " " + TRIGGER_NAME.ljust(6) + " : %s" % ljm.eReadName(t7, TRIGGER_NAME))
for addrName,chName in zip(aScanListNames,names):
    print(" " + chName.ljust(8) + " " + addrName.ljust(6) + " : %.3f" % ljm.eReadName(t7, addrName))
print(" ")

    
# Setup and call eWriteNames to write values to the LabJack.
numFrames = 1
names = ["DAC0"]
aValues = [2.5]  # [2.5 V, 12345]
ljm.eWriteNames(t7, numFrames, names, aValues)

    
    


# Start clock
print("Starting GUI clock")
timeClock()

# Start the GUI
print("Starting GUI mainloop. READY TO USE")
lbl2.config(text="Idle ...",bg="light green")
w.mainloop()
  

# Stop stream (incase it is still open for some reason)
try:
    ljm.eStreamStop(t7)   
except ljm.LJMError:
    ljme = sys.exc_info()[1]
    #print(ljme)
except Exception:
    e = sys.exc_info()[1]
    #print(e)
        
# Close the labjack handle
print("Closing the labjack ... ") 
ljm.close(t7)
print("Program complete.") 
