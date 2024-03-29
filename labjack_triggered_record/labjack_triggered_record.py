# labjack_triggered_record.py
# Author  : C Fujiwara
# Created : 2022.11.02
# Last Edit : (see GitHub)
#
#
# READ ABOUT STRING VAR
#https://www.pythontutorial.net/tkinter/tkinter-stringvar/

# Options
font_name = 'arial narrow'
font_name_lbl = 'arial narrow bold'

TriggerChannel = "DIO0"
InputChannels = ["AIN0"]
OutputChannel = "DAC0"

defaultIP = '192.168.1.145'
#%% Packages

# tkinter is the main GUI package
import tkinter as tk
import os

# Import packages
import sys
import datetime
from labjack import ljm
import time
from threading import Thread
from threading import Event

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
import scipy.io
# Convert RGB triplet to tk color that is interprable
def _from_rgb(rgb):
    """translates an rgb tuple of int to a tk friendly color code
    """
    return "#%02x%02x%02x" % rgb  

#%% Stream Thread 

class stream(Thread):
    def __init__(self,handle,evt):
        super().__init__()
        self.handle = handle
        self.goodStream         = True

        # Saving Stuff

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

        self.lastacquisition    = None 
        
        self.delay              = None
        self.timeout            = None
        
        self.continueAcq       = None
        self.Foo = evt
        self.Foo.set()

       
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
        
        # Configure and start stream
        scanrate = ljm.eStreamStart(self.handle, scansperread, nAddr, aScanList, scanrate)   
        t2 = time.time()
        time.sleep(sleepTime + 0.01)
        while (totScans < numscans) & self.goodStream:
            
            #print(self.Foo.is_set())
            if not(self.Foo.is_set()):
                self.goodStream = False
                print('Canceling Stream')

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
                    if (((time.time()-t2)-Tacquire)>self.timeout) and self.timeout>0:
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

            #self.lastacquisition = tAcq
            self.lastacq = time.time()
            if totSkip>0:
                print("lost frames : " + str(totSkip))
        else:
            time.sleep(0.1)
            
        self.AcqStatus.config(text='idle ',fg='brown')
        self.AcqStatus.update()     
        #time.sleep(.5)

#%% Main App Thread 


class App(tk.Tk):
    def __init__(self):        
        # Create the GUI object
        super().__init__()
        self.title('Labjack Oscilloscope')
        self.geometry("800x600")
        
        self.connectOptions = [
        "IP address (ETH)",
        "serial number (USB)",
        "serial number (ETH)"
        ]    
        self.vcmdNum = (self.register(self.validNum),'%P')

        # Internal Labjack Settings
        self.isConnected = False
        self.TriggerChannel = TriggerChannel
        self.InputChannels = InputChannels
        self.OutputChannel = OutputChannel

        self.dirname            = tk.StringVar(self)
        self.root               = tk.StringVar(self)

        self.connectMode        = tk.StringVar(self)    # Connect Mode
        self.connectStr         = tk.StringVar(self)    # Connect String            

        self.scanrate           = tk.StringVar(self)    # Scan Rate 
        self.numscans           = tk.StringVar(self)    # Number of scans
        self.scansperread       = tk.StringVar(self)    # Scans per read 
        self.delay              = tk.StringVar(self)    # Delay after acquisition 
        self.timeout            = tk.StringVar(self)    # Timeout of measurement
        self.doSave             = tk.IntVar(self)
        
        self.doSource           = tk.IntVar(self)
        self.controlfile        = tk.StringVar(self)

        self.t                  = np.linspace(0, 300, 301)
        self.y1                 = np.exp(-self.t)
        
        
        self.Foo = Event()
        #print(self.Foo.is_set())
        #self.Foo.set()
        #print(self.Foo.is_set())

        self.defaultSettings()        
        self.create_frames()        
        self.create_widgets() 
        self.create_plots()                   
        self.set_state(self.FacqButt,'disabled')

    # Process the resultant stream
    def process_stream(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.process_stream(thread))

        else:
                
            if thread.goodStream:
                self.t = thread.t
                self.y1 = thread.y1
                self.lastAcquisition = thread.lastacquisition                
                self.update()
                
            if self.doAutoAcq:    
                self.after(int(self.delay.get()),self.doTrigAcq())
            else:
                self.forcebutt['state']='normal'
                self.acqbutt['state']='normal' 
                self.set_state(self.acqtbl,'normal')


    #Define a Function to enable the frame
    def set_state(self,frame,mystate):
        children = frame.winfo_children()
        for child in children:
            wtype = child.winfo_class()
            if wtype not in ('Frame','Labelframe'):
                child.configure(state=mystate)            
            else:
                self.set_state(child,mystate)
    
    # Create frames for objects
    def create_frames(self):
        self.Fopt = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",
                             highlightthickness=2)
        self.Fopt.pack(side='left',anchor='nw',fill='y')
        
        # Connect Frame
        self.Fconnect = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",
                                 highlightthickness=2)
        self.Fconnect.grid(row=1,column=1,sticky='we')
        
        # Voltage output
        self.Foutput = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",
                                highlightthickness=2)
        self.Foutput.grid(row=2,column=1,sticky='we')
        
        # Acquisition
        self.Facquire = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",
                                 highlightthickness=2)
        self.Facquire.grid(row=3,column=1,sticky='we')
        
        # Saving
        self.Fanalysis = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",
                                  highlightthickness=2)
        self.Fanalysis.grid(row=4,column=1,sticky='we')      
        
        # Sequence Params Source
        self.FSeq = tk.Frame(self.Fopt,bd=1,bg="white",highlightbackground="grey",
                                  highlightthickness=2)
        self.FSeq.grid(row=5,column=1,sticky='we')    
     
        # Plots
        self.Fplot = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",
                              highlightthickness=2)
        self.Fplot.pack(side='right',fill='both',expand=1)
        
# Default settings
    def defaultSettings(self):
        self.connectStr.set('470026765')   
        self.connectMode.set(self.connectOptions[2])
        
        self.connectStr.set(defaultIP)   
        self.connectMode.set(self.connectOptions[0])
        
        # Output voltage default values 
        self.dirname.set(r'PA')
        self.root.set(r'Y:\LabjackScope')
        self.doSave.set(1)

        self.scanrate.set('100000')
        self.numscans.set('500')
        self.scansperread.set('500')
        self.delay.set('500')
        self.timeout.set('0')   
        self.controlfile.set(r'Y:\_communication\control2.mat')   
        self.doSource.set(1)


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
        # Connect Button
        self.b1=tk.Button(self.Fconnect,text="connect",bg=_from_rgb((80, 200, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.connect)
        self.b1.grid(row=3,column=2,sticky='EW')   
        
        # Disconnect Button
        self.b2=tk.Button(self.Fconnect,text="disconnect",bg=_from_rgb((255, 102, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.disconnect,state='disabled')
        self.b2.grid(row = 3, column=3,sticky='NSEW')
        
        # Connect options       
        tk.OptionMenu(self.Fconnect, self.connectMode, *self.connectOptions).grid(
            row=4,column=1,columnspan=3,sticky='NSEW')  
        
        # Connect string
        tk.Entry(self.Fconnect,bg='white',textvariable=self.connectStr,
                 font=(font_name,"10"),justify='center').grid(row=5,column=1,columnspan=3,sticky='NSEW')  
        
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
        self.acqtbl.grid(row=5,column=1,columnspan=3,sticky='nswe')        

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
                     
        # Timeout
        tk.Label(self.acqtbl,text='timeout (s)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=5,column=1,columnspan=1,stick='w')  

        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.timeout,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=5,column=2,columnspan=1,sticky='w')  
                     
        # Analysis Settings
        tk.Label(self.Fanalysis,text='Analysis',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')    
                     
        tk.Checkbutton(self.Fanalysis, text='save data to drive',variable=self.doSave, 
                       onvalue=1, offvalue=0,bg='white').grid(
                                row=2,column=1,columnspan=1,sticky='w')           
                     
              
        self.analysistbl = tk.Frame(self.Fanalysis,bd=1,bg="white",highlightbackground="grey",
                        highlightthickness=1)
        self.analysistbl.grid(row=4,column=1,columnspan=3,sticky='nswe')             
                     
        tk.Label(self.analysistbl,text='root',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')
                    
        tk.Entry(self.analysistbl,bg='white',justify='center',textvariable=self.root,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=1,column=2,columnspan=1,sticky='NSEW')               
                     
        tk.Label(self.analysistbl,text='directory name',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')
                    
        tk.Entry(self.analysistbl,bg='white',justify='center',textvariable=self.dirname,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=2,column=2,columnspan=1,sticky='NSEW')   
                    
        tk.Label(self.Fanalysis,text='Analysis',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')    
                   
        # Sequence File Source
        tk.Label(self.FSeq,text='Sequence',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')  
                     
                                          
        tk.Checkbutton(self.FSeq, text='use source file date',variable=self.doSource, 
                       onvalue=1, offvalue=0,bg='white').grid(
                                row=2,column=1,columnspan=1,sticky='w')          
                     
        
 
        tk.Entry(self.FSeq,bg='white',justify='center',textvariable=self.controlfile,
                 font=(font_name,"10"),width=30).grid(
                     row=3,column=1,columnspan=1,sticky='NSEW')               
                     
   
 
                             
          
        
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

        # Create graphical object
        self.fig = Figure()
        self.fig.autofmt_xdate()
        #gs = GridSpec(1, 1, figure=self.fig)        
        #self.ax1 = self.fig.add_subplot(gs[:-1, :])
        self.ax1 = self.fig.add_subplot()      
        self.ax1.set_ylabel("voltage (mV)",color='black')
        self.ax1.set_xlabel("time (ms)")
        self.p1, = self.ax1.plot(self.t,self.y1,color='black')
        self.ax1.set_xlim([0,300])        
        self.ax1.grid(True)       
        self.ax1.tick_params(axis='y', labelcolor='black')   
        self.fig.tight_layout()
        
        # make the figure and the canvas
        self.canvas = FigureCanvasTkAgg(self.fig,master = self.Fplot)  
        self.canvas.draw()          
        self.canvas.get_tk_widget().pack(side='top',fill='both',expand=True)
        

    # Set the timeouts
    def configLJM(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
                                ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        #ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
         #                      ljm.constants.STREAM_SCANS_RETURN_ALL)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)  
        #ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 30)  

    # Configure hardware trigger for desired application
    def configTrig(self):
        address = ljm.nameToAddress(self.TriggerChannel)[0]
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", address);
    
        # Clear any previous settings on triggerName's Extended Feature registers
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 0);
    
        # For trigger settings, see the labjack manual.  Here we chose to 
        # this using the conditional reset        
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.TriggerChannel, 12);   # conditional reset
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.TriggerChannel, 1); # 1 is rising 0 is falling   
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_B" % self.TriggerChannel, 1); # number of triggers to reset


        # Enable
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 1);
        
    # Configure trigger to be manual
    def configMan(self):
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0);
        
    # Connect to the labjack
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
            #val = ljm.eReadName(self.handle, self.OutputChannel) 
            #self.output.set(str(np.round(1000*val,1)))
            self.ConnectStatus.config(text='connected',fg='green')

            ljm.eWriteName(self.handle,'AIN_ALL_NEGATIVE_CH',ljm.constants.GND)
            ljm.eWriteName(self.handle,'AIN0_RANGE',10)
            ljm.eWriteName(self.handle,'AIN1_RANGE',10)
            ljm.eWriteName(self.handle,'STREAM_SETTLING_US',0)
            ljm.eWriteName(self.handle,'STREAM_RESOLUTION_INDEX',0)

            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)    # Internal clock stream
            self.b1['state']='disabled'
            self.b2['state']='normal'
            self.set_state(self.FacqButt,'normal')


    # Disconnect from the labjack
    def disconnect(self):
        if self.isConnected:
            print('disconnecting from labjack')
            ljm.close(self.handle)
            self.isConnected = False
            self.ConnectStatus.config(text='disconnected',fg='red')
            self.b1['state']='normal'
            self.b2['state']='disabled'
            self.set_state(self.FacqButt,'disabled')

    # Force acquisition callback        
    def forceacq(self):
        self.doAutoAcq = False
        self.configMan()
        self.configLJM()      
        
        self.forcebutt['state']='disabled'
        self.acqbutt['state']='disabled'
        self.set_state(self.acqtbl,'disabled')

        stream_thread = stream(self.handle,self.Foo)        
        stream_thread.numscans=int(self.numscans.get())
        stream_thread.scanrate=int(self.scanrate.get())
        stream_thread.scansperread=int(self.scansperread.get())
        stream_thread.InputChannels = self.InputChannels
        stream_thread.TriggerChannel = self.TriggerChannel
        stream_thread.delay=int(self.delay.get())
        stream_thread.timeout=int(self.timeout.get())

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
        self.doTrigAcq()

        
    def doTrigAcq(self):           
        stream_thread = stream(self.handle,self.Foo)            
        stream_thread.numscans=int(self.numscans.get())
        stream_thread.scanrate=int(self.scanrate.get())
        stream_thread.scansperread=int(self.scansperread.get())
        stream_thread.InputChannels = self.InputChannels
        stream_thread.TriggerChannel = self.TriggerChannel                 
        stream_thread.delay=int(self.delay.get())     
        stream_thread.timeout=int(self.timeout.get())        

        stream_thread.AcqStatus=self.AcqStatus        
        stream_thread.start()
        self.process_stream(stream_thread)  
            
    def stopacq(self):
        self.doAutoAcq = False
        self.doLock = False   
        self.Foo.clear()
   
    def update(self): 
        self.p1.set_data(self.t,self.y1)     
        #self.ax1.relim()
        self.ax1.set_xlim(0,np.amax(self.t))
        self.ax1.set_ylim(min(self.y1)-100,max(self.y1)+100)   
        self.canvas.draw()  
        
        if self.doSource:
            self.grabSequenceDate()

            
        
        if self.doSave:
            self.saveData()    

    def grabSequenceDate(self):
        fname = self.controlfile.get()
        b = scipy.io.loadmat(fname)        
        matlab_datestr = b['vals']['ExecutionDateStr'][0][0][0]
        matlab_datenum = b['vals']['ExecutionDate'][0][0][0][0]
                
        self.SequenceExecutionDate = matlab_datenum
        self.SequenceExecutionDateStr = matlab_datestr
        
        
        
    # Save data to file
    def saveData(self):
        fname,dstr = self.getLogName()          
        
        
        
        if self.doSource :                
            scipy.io.savemat(fname,{"t": self.t, "y": self.y1, 
                                    "t_unit": "ms", 
                                    "y_unit": "mV",
                                    "date": dstr,
                                    "ExecutionDate": self.SequenceExecutionDate,
                                    "ExecutionDateStr": self.SequenceExecutionDateStr})
        else:
            scipy.io.savemat(fname,{"t": self.t, "y": self.y1, 
                                    "t_unit": "ms", 
                                    "y_unit": "mV",
                                    "date": dstr})
            
        print('data saved to ' + fname)

    # Get the file name that this should save to
    def getLogName(self):
        tnow=datetime.datetime.now();
        
        if self.doSource:
            fmt = '%d-%b-%Y %H:%M:%S'
            tnow = datetime.datetime.strptime(self.SequenceExecutionDateStr,fmt) 
            
        
        y=tnow.year
        m='%02d' % tnow.month
        d='%02d' % tnow.day
        
        fname0 = tnow.strftime("%Y-%m-%d_%H-%M-%S") + '.mat'
        dstr = tnow.strftime("%Y/%m/%d %H:%M:%S")

        
        # Root directory of this type
        f0 = os.path.join(self.root.get(),self.dirname.get())
        
        # Year Directory
        dir_year = os.path.join(f0,str(y))
        
        # Month Directory
        dir_month = os.path.join(dir_year,str(y) + '.' + str(m))
        
        # Day Directory
        dir_day= os.path.join(dir_month,str(m) + '.' + str(d))
        
        # Filename
        fname = os.path.join(dir_day,fname0)

        # Make the directories if they don't exist yet        
        if not(os.path.isdir(f0)):
            os.mkdir(f0)
        
        if not(os.path.isdir(dir_year)):
            print('making')
            os.mkdir(dir_year)
            
        if not(os.path.isdir(dir_month)):
            os.mkdir(dir_month)
            
        if not(os.path.isdir(dir_day)):
            os.mkdir(dir_day)
            
        return fname, dstr
            
    # On close make sure to disconnect from the labjack
    def on_closing(self):
        self.disconnect()
        self.destroy()                


#%% Main Loop

if __name__ == "__main__":
     app = App()
     app.protocol("WM_DELETE_WINDOW", app.on_closing)
     app.mainloop()       
