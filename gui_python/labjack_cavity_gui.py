# labjack_cavity_gui.py
# Author  : C Fujiwara
# Created : 2021.12.10
# Last Edit : (see GitHub)
#
# This GUI is used to run a labjack T7 as an oscilloscope for monitoring and 
# a spectrum from a Fabry-Perot Interferometer.  Using a reference laser
# as a source for peaks, it locks the separation between two peaks.
#
# This code was written as Cora's first real forray into GUI programming for 
# python using the tkinter packages.  I also only have a vague understanding
# of matplotlib as well. So this code could be optimized further. My primary
# coding expertise is from MATLAB.
#
# READ ABOUT STRING VAR
#https://www.pythontutorial.net/tkinter/tkinter-stringvar/

# Options
font_name = 'arial narrow'
font_name_lbl = 'arial narrow bold'

#%% Packages

# tkinter is the main GUI package
import tkinter as tk

# Import packages
import sys
import datetime
from labjack import ljm
import time
from threading import Thread
import queue
from matplotlib.dates import DateFormatter

import ljm_stream_util
import code
# matplotlib packages
from matplotlib.gridspec import GridSpec
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)

# Math
import numpy as np
import scipy
import scipy.signal
# Convert RGB triplet to tk color that is interprable
def _from_rgb(rgb):
    """translates an rgb tuple of int to a tk friendly color code
    """
    return "#%02x%02x%02x" % rgb  


class stream(Thread):
    def __init__(self,handle):
        super().__init__()
        self.handle = handle
        self.goodStream         = True


        # Stream Properties
        self.scanrate           = None
        self.numscans           = None
        self.scansperread       = None

        # Read Channels
        self.InputChannels      = None
        self.TriggerChannel     = None       
        self.AcqStatus          = None
        
        # Data
        self.t                  = None
        self.y1                  = None
        self.y2                  = None

        self.lastacquisition    = None 
        
        self.delay              = None
       
    def run(self):
        self.AcqStatus.config(text='acquiring ... ',fg='green')
        self.AcqStatus.update()  
        
        # Scan list addresses for streamBurst    
        nAddr = len(self.InputChannels)
        aScanList = ljm.namesToAddresses(nAddr, self.InputChannels)[0]   
        
        # Get the scan rate (Hz) and number of total samples    
        scanrate = float(self.scanrate)
        numscans=int(self.numscans)
        scansperread=int(self.scansperread)
        Tacquire = numscans/scanrate  
        
        # Initilize Counters
        totScans = 0            # Total scans read
        totSkip = 0             # Total skipped samples
        i = 1                   # Number of reads
        ljmScanBacklog = 0      # Backlog on the LJM
        dataAll=[]              # All data
        sleepTime = float(scansperread)/float(scanrate)
        
        # Wait until trigger level is appropriate
        tLevel = 0;
        while (tLevel == 0):
            tLevel=ljm.eReadName(self.handle,self.TriggerChannel)
            time.sleep(0.005)     

        # Configure and start stream
        scanrate = ljm.eStreamStart(self.handle, scansperread, nAddr, aScanList, scanrate)   
        t2 = time.time()
        time.sleep(sleepTime + 0.01)
        
        while (totScans < numscans) & self.goodStream:
            try:                
                ret = ljm.eStreamRead(self.handle) # read data in buffer
                aData = ret[0]
                #ljmScanBacklog = ret[2]
                scans = len(aData) / nAddr
                totScans += scans 
                dataAll+=aData  
                # -9999 values are skipped ones
                curSkip = aData.count(-9999.0)
                totSkip += curSkip                    
                #print("eStreamRead %i : %i scans, %0.0f scans skipped, %i device backlog, %i in LJM backlog" % (i,totScans, curSkip/nAddr, ret[1], ljmScanBacklog))

                i += 1                
                if totScans<numscans:
                    time.sleep(sleepTime)

            except ljm.LJMError as err:
                if err.errorCode == ljm.errorcodes.NO_SCANS_RETURNED:  
                    if ((time.time()-t2)-Tacquire)>2:
                        self.AcqStatus.config(text='ACQUISITION TIMEOUT',fg='red')
                        self.AcqStatus.update()
                        self.goodStream=0
                    sys.stdout.flush()
                    continue
                else: 
                    ljme = sys.exc_info()[1]
                    print(ljme)
                    self.goodStream=False  

        try:
            ljm.eStreamStop(self.handle)   
        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)                
        if self.goodStream:  
            #t3=time.time()

            self.AcqStatus.config(text='processing stream ... ',fg='green')
            self.AcqStatus.update()     
            
            tVec = np.linspace(0,numscans-1,numscans)/scanrate
            data = np.zeros((numscans,nAddr))
            data = np.array(dataAll).reshape(numscans,nAddr)   

            # Convert data to mV and ms
            self.t = 1000*tVec
            self.y1 = 1000*data[:,0]
            self.y2 = 1000*data[:,1]    

            #self.lastacquisition = tAcq
            self.lastacq = time.time()
            if totSkip>0:
                print("lost frames : " + str(totSkip))
        else:
            time.sleep(0.1)
            
        self.AcqStatus.config(text='idle ',fg='brown')
        self.AcqStatus.update()     
        #time.sleep(.5)



class App(tk.Tk):
    def __init__(self):        
        # Create the GUI object
        super().__init__()
        self.title('Labjack Cavity')
        self.geometry("1280x780")
        
        self.connectOptions = [
        "IP address (ETH)",
        "serial number (USB)",
        "serial number (ETH)"
        ]    
        self.vcmdNum = (self.register(self.validNum),'%P')

        # Internal Labjack Settings
        self.isConnected = False
        self.TriggerChannel = "DIO0"
        self.InputChannels = ["AIN0", "AIN1"]
        self.OutputChannel = "DAC0"

        self.autoTrack = tk.IntVar(self)

        self.connectMode = tk.StringVar(self)   # Connect Mode
        self.connectStr = tk.StringVar(self)    # Connect String    
        
        self.output = tk.StringVar(self)        # Output Voltage 
        self.outputMax = tk.StringVar(self)     # Output Voltage Max
        self.outputMin = tk.StringVar(self)     # Output Voltage Min

        self.scanrate = tk.StringVar(self)      # Scan Rate 
        self.numscans = tk.StringVar(self)      # Output Voltage
        self.scansperread = tk.StringVar(self)  # Output Voltage Max 
        self.delay = tk.StringVar(self)         # Output Voltage Min 

        self.tstart = tk.StringVar(self)        # Tstart
        self.tend = tk.StringVar(self)          # T end
        self.minpeak = tk.StringVar(self)       # Minimum Peak Height
        self.FSR = tk.StringVar(self)           # Minimum Peak Height

        self.FSRtime = tk.StringVar(self)       # Tstart
        self.dT = tk.StringVar(self)            # T end
        self.dF = tk.StringVar(self)            # Minimum Peak Height

        self.dFset = tk.StringVar(self)         # Tstart
        self.hys = tk.StringVar(self)           # T end
        self.dV = tk.StringVar(self)            # Minimum Peak Height  
        
        self.t = np.linspace(0, 300, 301)
        self.y1 = np.exp(-self.t)
        self.y2 = np.sin(2 * np.pi * self.t/50)
                
        self.doAutoAcq = False
        self.doLock = False
        
        self.tHis=[]
        self.vHis=[]
        self.nHis=400
        self.dfHis=[]
        
        self.defaultSettings()        
        self.create_frames()        
        self.create_widgets() 
        self.create_plots()
        
        self.set_state(self.Foutput,'disabled')
        self.set_state(self.FacqButt,'disabled')
        self.set_state(self.FlockButt,'disabled')
        
            
        
    def process_stream(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.process_stream(thread))

        else:
            #self.AcqStatus.config(text=thread.Status,fg=thread.StatusColor)
                
            if thread.goodStream:
                self.t = thread.t
                self.y1 = thread.y1
                self.y2 = thread.y2
                self.lastAcquisition = thread.lastacquisition                
                self.update()
                
            if self.doAutoAcq:    
                self.after(int(self.delay.get()),self.doTrigAcq())
            else:
                self.forcebutt['state']='normal'
                self.acqbutt['state']='normal' 
                self.set_state(self.acqtbl,'normal')
                self.set_state(self.Fpeak,'normal')


    #Define a Function to enable the frame
    def set_state(self,frame,mystate):
        children = frame.winfo_children()
        for child in children:
            wtype = child.winfo_class()
            if wtype not in ('Frame','Labelframe'):
                child.configure(state=mystate)            
            else:
                self.set_state(child,mystate)
    
    def create_frames(self):
        self.Fopt = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fopt.pack(side='left',anchor='nw',fill='y')
        
        # Connect Frame
        self.Fconnect = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fconnect.grid(row=1,column=1,sticky='we')
        
        # Voltage output
        self.Foutput = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Foutput.grid(row=2,column=1,sticky='we')
        
        # Acquisition
        self.Facquire = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Facquire.grid(row=3,column=1,sticky='we')
        
        # Peak Analysis Settings
        self.Fpeak = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fpeak.grid(row=4,column=1,sticky='we')
        
        # Peak Analysis Output
        self.Fpeakout = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fpeakout.grid(row=5,column=1,sticky='we')
        
        # Lock Settings
        self.Flock = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Flock.grid(row=6,column=1,sticky='we')
        
        # Plots
        self.Fplot = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fplot.pack(side='right',fill='both',expand=1)
        
    def defaultSettings(self):
        self.connectStr.set('470026765')   
        self.connectMode.set(self.connectOptions[2])
        
        #self.connectStr.set('192.168.0.177')   
        #self.connectMode.set(self.connectOptions[0])
        
        self.connectStr.set('192.168.1.125')   
        self.connectMode.set(self.connectOptions[0])
        
        # Output voltage default values
        self.output.set('??')
        self.outputMax.set('2500')
        self.outputMin.set('0')    
        
        self.scanrate.set('20000')
        self.numscans.set('5500')
        self.scansperread.set('5500')
        self.delay.set('500')

        self.tstart.set('110')
        self.tend.set('210')
        self.minpeak.set('500')
        self.FSR.set('1500')
        
        self.FSRtime.set('??')
        self.dT.set('??')
        self.dF.set('??')    
        
        self.dFset.set('-200')
        self.hys.set('50')
        self.dV.set('1')  
        
    def set_output_state(self,state):
        self.bDa['state'] = state
        self.bDb['state'] = state
        self.bDc['state'] = state
        self.bDd['state'] = state
        self.bDe['state'] = state
        self.bDf['state'] = state

    def create_widgets(self):
        # Connect Label
        tk.Label(self.Fconnect,text='Labjack Connection',font=(font_name_lbl,"12"),
                 bg='white',justify='left',bd=0).grid(row=1,column=1,columnspan=3,stick='w') 
        
        # Connect Status
        self.ConnectStatus = tk.Label(self.Fconnect,font=(font_name,"10"),
                 bg='white',justify='left',bd=0,fg='red',text='disconnected')
        self.ConnectStatus.grid(row=2,column=1,columnspan=3,stick='w')         
        
        # Help Button
        tk.Button(self.Fconnect,text='help',font=(font_name,"10"),
                  width=6,bd=3).grid(row=3,column=1)        
        # Connect
        self.b1=tk.Button(self.Fconnect,text="connect",bg=_from_rgb((80, 200, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.connect)
        self.b1.grid(row=3,column=2,sticky='EW')   
        
        # Disconnect
        self.b2=tk.Button(self.Fconnect,text="disconnect",bg=_from_rgb((255, 102, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.disconnect,state='disabled')
        self.b2.grid(row = 3, column=3,sticky='NSEW')
        
        # Connect options       
        tk.OptionMenu(self.Fconnect, self.connectMode, *self.connectOptions).grid(
            row=4,column=1,columnspan=3,sticky='NSEW')  
        # Connect string
        tk.Entry(self.Fconnect,bg='white',textvariable=self.connectStr,
                 font=(font_name,"10"),justify='center').grid(row=5,column=1,columnspan=3,sticky='NSEW')  
        tk.Label(self.Foutput,text='Output',font=(font_name_lbl,"12"),bg='white',justify='left',height=1,bd=0).grid(row=1,column=1,sticky='w')
        
        # Frame for output voltage increment
        f = tk.Frame(self.Foutput,bd=1,bg="white",highlightbackground="grey",highlightthickness=1) 
        f.grid(row=2,column=1)      
        
        # Down 100 mV
        self.bDa=tk.Button(f,text="-100",bg=_from_rgb((255,0,24)),font=(font_name,"10"),
                  width=4,bd=3,command=lambda: self.increment(-100))
        self.bDa.grid(row=1,column=1,sticky='w')  
        
        # Down 20 mV
        self.bDb=tk.Button(f,text="-20",bg=_from_rgb((255,165,44)),font=(font_name,"10"),
                  width=4,bd=3,command=lambda: self.increment(-20))
        self.bDb.grid(row=1,column=2,sticky='w')
           
        # Down 5 mV
        self.bDc=tk.Button(f,text="-5",bg=_from_rgb((255, 255, 65)),
                  font=(font_name,"10"),width=2,bd=3,command=lambda: self.increment(-5))
        self.bDc.grid(row=1,column=3,sticky='w')   
        
        # Up 5 mV
        self.bDd=tk.Button(f,text="+5",bg=_from_rgb((0, 128, 24)),font=(font_name,"10"),
                  width=2,bd=3,fg='white',command=lambda: self.increment(5))
        self.bDd.grid(row=1,column=4,sticky='w'  )
        
                
        # Up 20 mV
        self.bDe=tk.Button(f,text="+ 20",bg=_from_rgb((0, 0, 249)),font=(font_name,"10"),
                  width=4,bd=3,fg='white',command=lambda: self.increment(20))
        self.bDe.grid(row = 1, column=5,sticky='nwse')          
        # Up 100 mV
        self.bDf=tk.Button(f,text="+ 100",bg=_from_rgb((134, 0, 125)),font=(font_name,"10"),
                  width=4,bd=3,fg='white',command=lambda: self.increment(100))
        self.bDf.grid(row = 1, column=6,sticky='nwse')          
                
        # Frame for output voltages
        tbl = tk.Frame(self.Foutput,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        tbl.grid(row=3,column=1,sticky='nswe')
        
        # Output Voltage
        tk.Label(tbl,text='output (mV)',font=(font_name,"10"),bg='white'
                 ,justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')  
        tk.Label(tbl,bg='white',font=(font_name,"10"),justify='center',textvariable=self.output,
                 width=14,borderwidth=1,relief='groove').grid(row = 1, column=2,columnspan=1,sticky='NSEW')   
        
        # Max Voltage
        tk.Label(tbl,text='output MAX (mV)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl,bg='white',font=(font_name,"10"),justify='center',textvariable=self.outputMax,
                 width=10,validatecommand=self.vcmdNum,validate='key').grid(row = 2, column=2,columnspan=1,sticky='NSEW')   
        # Min Voltage
        tk.Label(tbl,text='output MIN (mV)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl,bg='white',font=(font_name,"10"),justify='center',textvariable=self.outputMin,
                 width=10,validatecommand=self.vcmdNum,validate='key').grid(row = 3, column=2,columnspan=1,sticky='NSEW')    
        
        # Acquisition Settings
        tk.Label(self.Facquire,text='Acquisition',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')                    
                     
        # Acqsuisition Status
        self.AcqStatus = tk.Label(self.Facquire,font=(font_name,"10"),
                 bg='white',justify='left',bd=0,fg='red',text='not acquiring')
        self.AcqStatus.grid(row=2,column=1,columnspan=3,stick='w') 
                     
        # Frame for acquisition buttons
        self.FacqButt= tk.Frame(self.Facquire,bd=1,bg="white",highlightbackground="grey",
                      highlightthickness=1)
        self.FacqButt.grid(row=3,column=1,sticky='w')

        # force acquisition
        self.forcebutt=tk.Button(self.FacqButt,text="force acq.",bg='white',font=(font_name,"10"),
                  width=9,bd=3,command=self.forceacq)
        self.forcebutt.grid(row = 1, column=1,sticky='w')  

        # Start acquisition
        self.acqbutt=tk.Button(self.FacqButt,text="start acq.",bg=_from_rgb((85, 205, 252)),
                  font=(font_name,"10"),width=9,bd=3,command=self.startacq)
        self.acqbutt.grid(row=1,column=2,sticky='w')   

        # Stop acquisition
        tk.Button(self.FacqButt,text="stop acq.",bg=_from_rgb((247, 168, 184)),
                  font=(font_name,"10"),width=9,bd=3,command=self.stopacq).grid(row = 1, column=3,sticky='w')  

        self.acqtbl = tk.Frame(self.Facquire,bd=1,bg="white",highlightbackground="grey",
                        highlightthickness=1)
        self.acqtbl.grid(row=4,column=1,columnspan=3,sticky='nswe')        

        # Scan Rate
        tk.Label(self.acqtbl,text='scan rate (Hz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')
                    
        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.scanrate,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=1,column=2,columnspan=1,sticky='NSEW')   

        # Num Scans
        tk.Label(self.acqtbl,text='num scans',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  

        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.numscans,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=2,column=2,columnspan=1,sticky='NSEW')  

        # Scans Per read
        tk.Label(self.acqtbl,text='scans per read',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  

        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.scansperread,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=3,column=2,columnspan=1,sticky='w')  

        # Delay
        tk.Label(self.acqtbl,text='delay (ms)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=4,column=1,columnspan=1,stick='w')  

        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.delay,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=4,column=2,columnspan=1,sticky='w')  

        # Peaks Analysis Settings
        tk.Label(self.Fpeak,text='Peak Analysis Settings',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')  
        
        
        # Frame for peak analysis settingss
        tbl3 = tk.Frame(self.Fpeak,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        tbl3.grid(row=2,column=1,columnspan=3,sticky='nswe')
        
    
        vcmd1 = (self.register(self.onValidateStart),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        vcmd2 = (self.register(self.onValidateEnd),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')        
        
        # Time Start
        tk.Label(tbl3,text='time start (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.tstart,
                 validatecommand=vcmd1,validate='key').grid(
                     row=1,column=2,columnspan=1,sticky='NSEW')                 
                     
        # Time End
        tk.Label(tbl3,text='time end (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.tend,
                 validatecommand=vcmd2,validate='key').grid(
                     row=2,column=2,columnspan=1,sticky='NSEW')  
        
        # Peak Height
        tk.Label(tbl3,text='min peak (mV)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.minpeak,validatecommand=self.vcmdNum,validate='key').grid(
                     row=3,column=2,columnspan=1,sticky='NSEW')  
        # Peak Height
        tk.Label(tbl3,text='auto time bounds?',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Checkbutton(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 variable=self.autoTrack).grid(
                     row=3,column=2,columnspan=1,sticky='NSEW')  
                     
        # FSR
        tk.Label(tbl3,text='FSR (MHz)',font=(font_name,"10"),bg='white',
                 justify='left',bd=0,width=18).grid(row=5,column=1,columnspan=1,stick='w') 
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.FSR,validatecommand=self.vcmdNum,validate='key').grid(row=5,column=2,columnspan=1,sticky='NSEW')  

        # Peaks Analysis Output
        tk.Label(self.Fpeakout,text='Peak Analysis Output',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')  
        
        # Frame for peak analysis outputs
        tbl4 = tk.Frame(self.Fpeakout,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        tbl4.grid(row=2,column=1,columnspan=3,sticky='nswe')        
        
        # FSR time (ms)
        tk.Label(tbl4,text='FSR time meas. (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')  
        tk.Label(tbl4,textvariable=self.FSRtime,font=(font_name,"10"),bg='white',
                 justify='left',bd=0,width=14,borderwidth=1,relief='groove').grid(
                     row=1,column=2,columnspan=1,stick='w')  
                  
        # dT
        tk.Label(tbl4,text='\u0394T meas. (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  
        tk.Label(tbl4,textvariable=self.dT,font=(font_name,"10"),bg='white',justify='left',
                 bd=0,width=14,borderwidth=1,relief='groove').grid(
                     row=2,column=2,columnspan=1,stick='w')  
        
        # dF
        tk.Label(tbl4,text='\u0394f meas. (MHz)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Label(tbl4,textvariable=self.dF,font=(font_name,"10"),bg='white',justify='left',
                 bd=0,width=14,borderwidth=1,relief='groove').grid(
                     row=3,column=2,columnspan=1,stick='ew')        
        
        # Lock Settings Label
        tk.Label(self.Flock,text='Lock Settings',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                                     row=1,column=1,columnspan=1,sticky='w')  
                     
                             
        # Acqsuisition Status
        self.LockStatus = tk.Label(self.Flock,font=(font_name,"10"),
                 bg='white',justify='left',bd=0,fg='red',text='lock not engaged')
        self.LockStatus.grid(row=2,column=1,columnspan=3,stick='w') 
                     
        # Lock Button Frame
        self.FlockButt = tk.Frame(self.Flock,bd=1,bg="white",
                             highlightbackground="grey",highlightthickness=1)
        self.FlockButt.grid(row=3,column=1,sticky='w')

        
        # Start Lock
        self.dolockbutt=tk.Button(self.FlockButt,text="engage lock",bg=_from_rgb((137, 207, 240)),font=(font_name,"10"),
                  width=15,bd=3,command=self.startlock)
        self.dolockbutt.grid(row = 1, column=1,sticky='w')  
        
        # Stop Lock
        self.nolockbutt=tk.Button(self.FlockButt,text="stop lock",bg=_from_rgb((255, 165, 0)),font=(font_name,"10"),
                  width=14,bd=3,command=self.stoplock)
        self.nolockbutt.grid(row = 1, column=2,sticky='w')  
        
        # Table For Lock Settings
        self.locktable = tk.Frame(self.Flock,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        self.locktable.grid(row=4,column=1,columnspan=3,sticky='nswe')
        
        # df set
        tk.Label(self.locktable,text='\u0394f set (MHz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')
        tk.Entry(self.locktable,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.dFset).grid(
            row=1,column=2,columnspan=1,sticky='NSEW')   
        
        # hysteresis
        tk.Label(self.locktable,text='hysteresis (MHz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')
        tk.Entry(self.locktable,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.hys,validatecommand=self.vcmdNum,validate='key').grid(
            row=2,column=2,columnspan=1,sticky='NSEW')  
        
        # step size
        tk.Label(self.locktable,text='\u0394V output step (mV)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')
        tk.Entry(self.locktable,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.dV,validatecommand=self.vcmdNum,validate='key').grid(
            row = 3, column=2,columnspan=1,sticky='NSEW')  
        
    def validNum(self,P):
        if P.isnumeric():
            return True
        else:
            return False

    def onValidateStart(self, d, i, P, s, S, v, V, W):
        
        # valid percent substitutions (from the Tk entry man page)
        # note: you only have to register the ones you need; this
        # example registers them all for illustrative purposes
        #
        # %d = Type of action (1=insert, 0=delete, -1 for others)
        # %i = index of char string to be inserted/deleted, or -1
        # %P = value of the entry if the edit is allowed
        # %s = value of entry prior to editing
        # %S = the text string being inserted or deleted, if any
        # %v = the type of validation that is currently set
        # %V = the type of validation that triggered the callback
        #      (key, focusin, focusout, forced)
        # %W = the tk name of the widget

        if (P.isnumeric()):     
            try:
                self.pT1.set_xdata(int(P)*np.array([1, 1]))
                self.canvas.draw()
            except:
                pass

            return True

        else:
            return False
        
    def onValidateEnd(self, d, i, P, s, S, v, V, W):
        
        # valid percent substitutions (from the Tk entry man page)
        # note: you only have to register the ones you need; this
        # example registers them all for illustrative purposes
        #
        # %d = Type of action (1=insert, 0=delete, -1 for others)
        # %i = index of char string to be inserted/deleted, or -1
        # %P = value of the entry if the edit is allowed
        # %s = value of entry prior to editing
        # %S = the text string being inserted or deleted, if any
        # %v = the type of validation that is currently set
        # %V = the type of validation that triggered the callback
        #      (key, focusin, focusout, forced)
        # %W = the tk name of the widget

        if (P.isnumeric()):
            try:
                self.pT2.set_xdata(int(P)*np.array([1, 1]))
                self.canvas.draw()
            except:
                pass
            return True

        else:
            return False
   
        
    def create_plots(self):
        # Acquisition Label
        tk.Label(self.Fplot,text='Plots',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).pack(side='top',anchor='nw')                    

        self.fig = Figure()
        self.fig.autofmt_xdate()
        gs = GridSpec(3, 1, figure=self.fig)        
        self.ax1 = self.fig.add_subplot(gs[:-1, :])
        self.ax1.set_ylabel("cavity voltage (mV)",color='black')
        self.ax1.set_xlabel("time (ms)")
        self.p1, = self.ax1.plot(self.t,self.y1,color='black')
        self.ax1.set_xlim([0,300])
        
        self.ax1.grid(True)
        
        self.pdT, = self.ax1.plot(np.array([0,1]),np.array([1000,1000]),color='blue')
        self.pdT.set_visible(False)
        
        self.pFSR, = self.ax1.plot(np.array([0,1]),np.array([1000,1000]),color='red')
        self.pFSR.set_visible(False)    
        
        self.pT1, = self.ax1.plot(np.array([1,1])*int(self.tstart.get()),np.array([0,1300]),color='g',linestyle='dashed')
        self.pT2, = self.ax1.plot(np.array([1,1])*int(self.tend.get()),np.array([0,1300]),color='g',linestyle='dashed')
       
        self.ax1.tick_params(axis='y', labelcolor='black')        
        
        tHisFake = [datetime.datetime.now()-datetime.timedelta(1e-4), datetime.datetime.now()]
        dfFake = [0, 0]
        vFake = [1.25, 1.25]        
        
        color = 'tab:blue'
        self.ax2 = self.ax1.twinx()  # instantiate a second axes that shares the same x-axis
        color = 'tab:red'
        self.ax2.set_ylabel('cavity ramp (mV)', color=color)  # we already handled the x-label with ax1
        self.p2,=self.ax2.plot(self.t, self.y2, color=color)
        self.ax2.tick_params(axis='y', labelcolor=color)
        
        self.ax3 = self.fig.add_subplot(gs[-1, :])
        self.p3,=self.ax3.plot(tHisFake, dfFake, color='black')
        self.ax3.set_ylabel(r"$\Delta f~\mathrm{measure}~(\mathrm{MHz})$")
        self.ax3.set_xlabel("time")
        myFmt = DateFormatter('%H:%M:%S')
        self.ax3.xaxis.set_major_formatter(myFmt)
        
        self.ax3.grid(True)
        
        color = 'tab:blue'
        self.ax4 = self.ax3.twinx()  # instantiate a second axes that shares the same x-axis
        self.ax4.set_ylabel('output (mV)', color=color)  # we already handled the x-label with ax1
        self.p4,=self.ax4.plot(tHisFake,vFake, color=color)
        self.ax4.tick_params(axis='y', labelcolor=color)
        self.ax4.xaxis.set_major_formatter(myFmt)

        self.fig.tight_layout()
        
        
        # creating the Tkinter canvas
        # containing the Matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.fig,master = self.Fplot)  
        self.canvas.draw()
          
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().pack(side='top',fill='both',expand=True)
        
        # creating the Matplotlib toolbar
        #toolbar = NavigationToolbar2Tk(canvas,
                                       #frame_plot)
        #toolbar.update()
          
        # placing the toolbar on the Tkinter window
        #canvas.get_tk_widget().pack()
        
        
                #canvas1.get_tk_widget().pack(side="top",fill='both',expand=True)
                #canvas1.pack(side="top",fill='both',expand=True)
             
    def configLJM(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
                                ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
                                ljm.constants.STREAM_SCANS_RETURN_ALL)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)  
        #ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 30)  


    def configTrig(self):
        address = ljm.nameToAddress(self.TriggerChannel)[0]
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", address);
    
        # Clear any previous settings on triggerName's Extended Feature registers
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 0);
    
        # 5 enables a rising or falling edge to trigger stream
        #ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.TriggerChannel, 4);
        #ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.TriggerChannel, 1);
        
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.TriggerChannel, 12);
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.TriggerChannel, 0);       
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_B" % self.TriggerChannel, 1);       


        # Enable
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 1);
        
    def configMan(self):
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0);
        
    def connect(self):
        try:
            if self.connectMode.get()==self.connectOptions[0]:
                print('Connecting ' + self.connectStr.get() + ' via ethernet')                
                self.handle=ljm.openS("T7","ETHERNET", self.connectStr.get())
                self.isConnected = True
            elif self.connectMode.get()==self.connectOptions[1]:
                print('Connecting ' + self.connectStr.get() + ' via USB')                
                self.handle=ljm.openS("T7","USB",self.connectStr.get())
                self.isConnected = True
            elif self.connectMode.get()==self.connectOptions[2]:
                print('Connecting ' + self.connectStr.get() + ' via ethernet')                
                self.handle=ljm.openS("T7","ETHERNET",self.connectStr.get())
                self.isConnected = True
            else:
                self.handle="OH NO"    
                self.isConnected = False
        except ljm.LJMError:
            self.isConnected = False
            print('oh no')
            
        if self.isConnected:
            
            try:
                ljm.eStreamStop(self.handle)   
            except:
                pass

            info = ljm.getHandleInfo(self.handle)
            print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
                  "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
                  (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
            val = ljm.eReadName(self.handle, self.OutputChannel) 
            self.output.set(str(np.round(1000*val,1)))
            self.ConnectStatus.config(text='connected',fg='green')

            ljm.eWriteName(self.handle,'AIN_ALL_NEGATIVE_CH',ljm.constants.GND)
            ljm.eWriteName(self.handle,'AIN0_RANGE',10)
            ljm.eWriteName(self.handle,'AIN1_RANGE',10)
            ljm.eWriteName(self.handle,'STREAM_SETTLING_US',0)
            ljm.eWriteName(self.handle,'STREAM_RESOLUTION_INDEX',0)

            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)    # Internal clock stream
            self.b1['state']='disabled'
            self.b2['state']='normal'
            self.set_state(self.Foutput,'normal')
            self.set_state(self.FacqButt,'normal')

    def disconnect(self):
        if self.isConnected:
            print('disconnecting from labjack')
            ljm.close(self.handle)
            self.isConnected = False
            self.ConnectStatus.config(text='disconnected',fg='red')
            self.b1['state']='normal'
            self.b2['state']='disabled'
            self.set_state(self.Foutput,'disabled')
            self.set_state(self.FacqButt,'disabled')
            self.set_state(self.FlockButt,'disabled')

    def increment(self,inc):
        if self.isConnected:
            oldVal = float(self.output.get())
            newVal = oldVal + inc
            
            Vlow = float(self.outputMin.get())
            Vhigh = float(self.outputMax.get())
            
            if (newVal >= Vlow) & (newVal<=Vhigh):
                ljm.eWriteName(self.handle,self.OutputChannel,newVal/1000)
            elif (newVal < Vlow):
                ljm.eWriteName(self.handle,self.OutputChannel,Vlow/1000)
            elif (newVal > Vhigh):
                ljm.eWriteName(self.handle,self.OutputChannel,Vhigh/1000)
                    
            
            val = ljm.eReadName(self.handle,self.OutputChannel)
            self.output.set(str(np.round(1000*val,1)))

        
    def forceacq(self):
        self.doAutoAcq = False
        self.configMan()
        self.configLJM()      
        
        self.forcebutt['state']='disabled'
        self.acqbutt['state']='disabled'
        self.set_state(self.acqtbl,'disabled')
        self.set_state(self.Fpeak,'disabled')

        stream_thread = stream(self.handle)        
        stream_thread.numscans=int(self.numscans.get())
        stream_thread.scanrate=int(self.scanrate.get())
        stream_thread.scansperread=int(self.scansperread.get())
        stream_thread.InputChannels = self.InputChannels
        stream_thread.TriggerChannel = self.TriggerChannel
        stream_thread.delay=int(self.delay.get())
        stream_thread.AcqStatus=self.AcqStatus        
        
        stream_thread.start()
        self.process_stream(stream_thread)         
        
    def startacq(self):
        self.doAutoAcq = True
        self.configTrig()
        #self.configMan()
        self.configLJM()              

        self.forcebutt['state']='disabled'
        self.acqbutt['state']='disabled'          
        self.set_state(self.acqtbl,'disabled')
        self.set_state(self.Fpeak,'disabled')
        self.dolockbutt['state']='normal'        
        self.doTrigAcq()

        
    def doTrigAcq(self):           
        stream_thread = stream(self.handle)            
        stream_thread.numscans=int(self.numscans.get())
        stream_thread.scanrate=int(self.scanrate.get())
        stream_thread.scansperread=int(self.scansperread.get())
        stream_thread.InputChannels = self.InputChannels
        stream_thread.TriggerChannel = self.TriggerChannel                 
        stream_thread.delay=int(self.delay.get())        
        stream_thread.AcqStatus=self.AcqStatus        
        stream_thread.start()
        self.process_stream(stream_thread)  
            
    def stopacq(self):
        self.doAutoAcq = False
        self.set_state(self.FlockButt,'disabled')

        self.doLock = False
        
    def startlock(self):
        self.doLock = True            
        self.dolockbutt['state']='disabled'
        self.nolockbutt['state']='normal'

        self.LockStatus.config(text='lock engaged',fg='green')
        self.LockStatus.update()     
        
    def stoplock(self):
        self.doLock = False
        self.dolockbutt['state']='normal'
        self.nolockbutt['state']='disabled'

        self.LockStatus.config(text='lock not engaged',fg='red')
        self.LockStatus.update()    
    def update(self): 

        self.p1.set_data(self.t,self.y1)
        self.p2.set_data(self.t,self.y2)
        
        self.ax1.set_xlim(0,np.amax(self.t))
        self.ax1.set_ylim(-100,2000)
        self.ax2.set_ylim(0,1200)        
        
        if int(self.tstart.get())<int(self.tend.get()):
            t = self.t
            y = self.y1 
            
            i1 = t >= int(self.tstart.get())
            i2 = t <= int(self.tend.get())            
            i = i1 & i2            
            y = y[i]
            t = t[i]
    
            # Find peaks
            peaks=scipy.signal.find_peaks(y, height=6,prominence=6) 
            
            yP = y[peaks[0]]
            tP = t[peaks[0]]
      
            # Sort in ascending order
            i = np.argsort(yP)        
            yP = yP[i]
            tP = tP[i]
            
            # Process the peaks if there are four of them
            if tP.size == 4:
                
  
                    
                    
                
                # Get the two biggest peaks and sort by time
                TpA = tP[2:4]
                yA = yP[2:4]            
                iA = np.argsort(TpA)
                TpA = TpA[iA]
                yA = yA[iA]            
    
                # Get teh two smallest peaks and sort by time
                TpB = tP[0:2]
                yB = yP[0:2]            
                iB = np.argsort(TpB)
                TpB = TpB[iB]
                yB = yB[iB] 
                
                if (self.autoTrack.get()==1):
                    tL = np.min([TpA[0],TpB[0]])
                    tH = np.max([TpA[1],TpB[1]])
                    
                    tL = round(tL - 15)
                    tH = round(tH + 15)
       
                    self.tstart.set(str(tL))
                    self.tend.set(str(tH))
                
                # Calculate the FSR            
                FSR_A = np.round(abs(TpA[0]-TpA[1]),2)
                FSR_B = np.round(abs(TpB[0]-TpB[1]),2)
                
                # Calculate the time separation
                dT = np.round(TpB[0]-TpA[0],2)
                dF = np.round(float(self.FSR.get())*dT/FSR_A)
    
                self.dT.set(str(dT))
                self.FSRtime.set(str(FSR_A))
                self.dF.set(str(round(dF,1)))
                
                self.pdT.set_data([TpB[0], TpA[0]],np.mean([yA[0],yB[0]])*np.array([1,1]))
                self.pdT.set_visible(True)
                
                self.pFSR.set_data(TpA,np.mean(yA)*np.array([1,1]))
                self.pFSR.set_visible(True)
                
                # Update the history
                
                tNow = datetime.datetime.now()
                
                if len(self.tHis) == self.nHis:
                    self.tHis.pop(0)
                    self.dfHis.pop(0)
                    self.vHis.pop(0)
                
                self.tHis.append(tNow)
                self.dfHis.append(dF)
                self.vHis.append(float(self.output.get())) 
                
                self.p3.set_data(self.tHis,self.dfHis)
                self.p4.set_data(self.tHis,self.vHis)
                
                self.ax3.set_ylim(np.min(self.dfHis)-10,np.max(self.dfHis)+10)
                self.ax4.set_ylim(np.min(self.vHis)-10,np.max(self.vHis)+10)                
                
                self.ax3.set_xlim(self.tHis[0]-datetime.timedelta(seconds=5),
                                  self.tHis[-1]+datetime.timedelta(seconds=5))
                
                if self.doLock:
                    dFset = int(self.dFset.get())  
                    hys = int(self.hys.get())                
                    err = dF - dFset                       
                    dV = int(self.dV.get())

                    if (err>0) & (abs(err)>hys):
                        self.increment(dV)                    
                    if (err<0) & (abs(err)>hys):
                        self.increment(-dV)                    
            else:
                self.pdT.set_visible(False)
                self.pFSR.set_visible(False)    
            self.canvas.draw()   
            
    def on_closing(self):
        self.disconnect()
        self.destroy()

                

"""
VALIDATION OF INPUT FOR ENTRIES
import tk as tk

class window2:
    def __init__(self, master1):
        self.panel2 = tk.Frame(master1)
        self.panel2.grid()
        self.button2 = tk.Button(self.panel2, text = "Quit", command = self.panel2.quit)
        self.button2.grid()
        vcmd = (master1.register(self.validate),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        self.text1 = tk.Entry(self.panel2, validate = 'key', validatecommand = vcmd)
        self.text1.grid()
        self.text1.focus()

    def validate(self, action, index, value_if_allowed,
                       prior_value, text, validation_type, trigger_type, widget_name):
        if value_if_allowed:
            try:
                float(value_if_allowed)
                return True
            except ValueError:
                return False
        else:
            return False

root1 = tk.Tk()
window2(root1)
root1.mainloop()
"""

#%% Main Loop

if __name__ == "__main__":
     app = App()
     app.protocol("WM_DELETE_WINDOW", app.on_closing)
     app.mainloop()       
