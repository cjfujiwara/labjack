# currentmonitor.py
# Author  : C Fujiwara
# Created : 2023.07.31
#
# This GUI is used to run a labjack T7 as an oscilloscope for monitoring and 
# multiple channels for our experiment

#
# READ ABOUT STRING VAR
#https://www.pythontutorial.net/tkinter/tkinter-stringvar/

# Options
font_name = 'arial narrow'
font_name_lbl = 'arial narrow bold'

#%% Packages

# tkinter is the main GUI package
import tkinter as tk

from tkinter import filedialog 

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))

# Configuration File Opener
import json

# Import packages
import sys
import datetime
from labjack import ljm
import time
from time import strftime

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
import shutil
# Math
import numpy as np
import scipy
#import scipy.signal
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
        self.data               = None
        self.lastAcquisition    = None         
        self.delay              = None
       
    def run(self):
        self.AcqStatus.config(text='initiating stream ...',fg='green')
        self.AcqStatus.update()  
        
        # Scan list addresses for streamBurst    
        nAddr = len(self.InputChannels)
        aScanList = ljm.namesToAddresses(nAddr, self.InputChannels)[0]   
        
        # Get the scan rate (Hz) and number of total samples    
        scanrate = self.scanrate
        numscans=self.numscans
        scansperread=self.scansperread
        Tacquire = numscans/scanrate  
        
        # Initilize Counters
        totScans = 0            # Total scans read
        totSkip = 0             # Total skipped samples
        i = 1                   # Number of reads
        ljmScanBacklog = 0      # Backlog on the LJM
        dataAll=[]              # All data
        sleepTime = float(scansperread)/float(scanrate)       

        print(sleepTime)
        #if ljm.eReadName(self.handle, "STREAM_TRIGGER_INDEX"):                    
            #print('waiting for trigger')

            # Wait until trigger level is appropriate
            #tLevel = 0;
            #while (tLevel == 0):
                #tLevel=ljm.eReadName(self.handle,self.TriggerChannel)
                #time.sleep(0.005)                   
        ljmScanBacklog = 0      # Backlog on the LJM
 

        print('Stream Started')
        

        
        # Configure and start stream
        scanrate = ljm.eStreamStart(self.handle, scansperread, nAddr, aScanList, scanrate)   
        
        self.AcqStatus.config(text=' stream started',fg='darkorange')
        self.AcqStatus.update()  
        
        t2 = time.time()
        time.sleep(sleepTime + 0.01)
        


        while (totScans < numscans) & self.goodStream:
            ljm_stream_util.variableStreamSleep(scansperread, scanrate, ljmScanBacklog)

            try:                
                ret = ljm.eStreamRead(self.handle) # read data in buffer
                aData = ret[0]
                ljmScanBacklog = ret[2]
                scans = len(aData) / nAddr
                totScans += scans 
                dataAll+=aData  
                # -9999 values are skipped ones
                curSkip = aData.count(-9999.0)
                totSkip += curSkip                    
                print("eStreamRead %i : %i scans, %0.0f scans skipped, %i device backlog, %i in LJM backlog" % (i,totScans, curSkip/nAddr, ret[1], ljmScanBacklog))
          
                #lbl2.config(text="Data stream in progress ... (%i of %i scans)" % (totScans,numScans),bg="red")   
  
          
                self.AcqStatus.config(text="Data stream in progress ... (%i of %i scans)" % (totScans,numscans),fg="red")   
                self.AcqStatus.update()    
          
                #print("eStreamRead %i : %i scans, %0.0f scans skipped, %i device backlog, %i in LJM backlog" % (i,totScans, curSkip/numAddresses, ret[1], ljmScanBacklog))

                i += 1                
                if totScans<numscans:
                    time.sleep(sleepTime)

            except ljm.LJMError as err:
                #self.goodStream = False
                if err.errorCode == ljm.errorcodes.NO_SCANS_RETURNED:  
                    #if ((time.time()-t2)-Tacquire)>2:
                    #    self.AcqStatus.config(text='ACQUISITION TIMEOUT',fg='red')
                    #    self.AcqStatus.update()
                    #    self.goodStream=False
                    sys.stdout.flush()
                    continue
                else: 
                    ljme = sys.exc_info()[1]
                    print(ljme)
                    self.goodStream=False  

        try:
            ljm.eStreamStop(self.handle)   
        except ljm.LJMError:
            print('err2')

            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            print('err3')

            e = sys.exc_info()[1]
            print(e)                
        if self.goodStream:  
            self.AcqStatus.config(text='processing stream ... ',fg='green')
            self.AcqStatus.update()               

            self.t = np.linspace(0,numscans-1,numscans)/scanrate
            self.data = np.array(dataAll).reshape(numscans,nAddr)               
            self.lastAcquisition = strftime('%Y-%m-%d_%H-%M-%S') 
            
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
        self.title('Labjack Oscilloscope')
        self.geometry("1280x780")
        
        self.connectOptions = [
        "IP address (ETH)",
        "serial number (USB)",
        "serial number (ETH)"
        ]    
        self.vcmdNum = (self.register(self.validNum),'%P')

        # Internal Labjack Settings
        self.isConnected = False       
        
        self.SaveRoot = tk.StringVar(self)
        self.SaveLabel = tk.StringVar(self)

        self.connectMode = tk.StringVar(self)   # Connect Mode
        self.connectStr = tk.StringVar(self)    # Connect String    
        
        self.output = tk.IntVar(self)        # Output Voltage 
        self.outputMax = tk.IntVar(self)     # Output Voltage Max
        self.outputMin = tk.IntVar(self)     # Output Voltage Min

        self.scanrate = tk.IntVar(self)      # Scan Rate 
        self.numscans = tk.IntVar(self)      # Output Voltage
        self.scansperread = tk.IntVar(self)  # Output Voltage Max 
        self.delay = tk.IntVar(self)         # Output Voltage Min 
        self.lastAcquisition = tk.StringVar(self)
        
        self.doAdwin = tk.BooleanVar(self)
        self.sequencer_file = tk.StringVar(self)
        self.extra_file = tk.StringVar(self)

        self.doSave = tk.BooleanVar(self)

        self.t = np.linspace(0, 300, 301)
        self.data = np.linspace(0,300,301)
        self.stream_thread = None
        
        self.defaultSettings()        
        self.create_frames()        
        self.create_widgets() 
        self.create_plots()       
        self.init_plots()
        
    def process_stream(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.process_stream(thread))

        else:
            #self.AcqStatus.config(text=thread.Status,fg=thread.StatusColor)
                
            if thread.goodStream:
                self.t = thread.t
                self.data = thread.data
                self.lastAcquisition.set(thread.lastAcquisition)
                self.update()
                
            if self.doAutoAcq and thread.goodStream:    
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
        # Right Frame
        self.Fright = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fright.pack(side='right',fill='both',expand=1)
        # Config File
        self.Fconfig = tk.Frame(self.Fright,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fconfig.pack(side='top',fill='x',expand=0)   
        # Saving
        self.Fsave = tk.Frame(self.Fright,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fsave.pack(side='top',fill='x',expand=0)     
        # Plots
        self.Fplot = tk.Frame(self.Fright,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fplot.pack(side='bottom',fill='both',expand=1)
        #self.Fplot.grid(row=2,column=1,sticky='we',expand=1)

    def defaultSettings(self):        
        self.connectStr.set('192.168.1.125')   
        self.connectMode.set(self.connectOptions[0])        
        self.TriggerChannel = "DIO0"
        self.InputChannels = ["AIN0", "AIN1"]
        self.InputNames = ["AIN0","AIN1"]
        self.OutputChannel = "DAC0"        
        self.doSave.set(0)
        self.doAdwin.set(0)              
        self.configuration_file = 'none'                
        # Output voltage default values
        self.output.set('??')
        self.outputMax.set(2500)
        self.outputMin.set(0)            
        self.scanrate.set(20000)
        self.numscans.set(5500)
        self.scansperread.set(5500)
        self.delay.set(500)
                
    def set_output_state(self,state):
        self.bDa['state'] = state
        self.bDb['state'] = state
        self.bDc['state'] = state
        self.bDd['state'] = state
        self.bDe['state'] = state
        self.bDf['state'] = state

    def create_widgets(self):
        # Config Label
        tk.Label(self.Fconfig,text='Configuration File',font=(font_name_lbl,"12"),
                 bg='white',justify='left',bd=0).grid(row=1,column=1,columnspan=1,stick='w')         
        # Load new configuration file        
        self.LoadConfig=tk.Button(self.Fconfig,text="load",
                  font=(font_name,"10"),width=4,bd=2,command=self.loadfile,state='active')
        self.LoadConfig.grid(row = 1, column=2,sticky='w')        
        # Configuration file
        self.ConfigFile = tk.Label(self.Fconfig,font=(font_name,"10"),
                 bg='white',justify='left',bd=0,fg='black',text='none')
        self.ConfigFile.grid(row=1,column=3,columnspan=3,stick='w')
        # Saving Label
        tk.Label(self.Fsave,text='Saving',font=(font_name_lbl,"12"),
                 bg='white',justify='left',bd=0).grid(row=1,column=1,columnspan=1,stick='w')         
        tk.Checkbutton(self.Fsave, text='save?',variable=self.doSave, onvalue=True, offvalue=False, 
                       ).grid(row=1,column=2,columnspan=1,stick='w')         
        tk.Checkbutton(self.Fsave, text='associate with sequencer?',variable=self.doAdwin, onvalue=True, offvalue=False, 
                       ).grid(row=1,column=3,columnspan=1,stick='w')         
        # Load new configuration file        
        self.LoadConfig=tk.Button(self.Fsave,text="load",
                  font=(font_name,"10"),width=4,bd=2,command=self.choosesavedir,state='active')
        self.LoadConfig.grid(row = 1, column=4,sticky='w')        
        # Configuration file
        self.SaveDirectory = tk.Label(self.Fsave,font=(font_name,"10"),
                 bg='white',justify='left',bd=0,fg='black',text='none')
        self.SaveDirectory.grid(row=1,column=5,columnspan=1,stick='w') 
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
        
        self.ax1= self.fig.add_subplot(1,1,1)
        self.ax1.set_ylabel("voltage (V)")
        self.ax1.set_xlabel("time (s)")
        self.ax1.xaxis.set_label_position("bottom")
        self.ax1.xaxis.tick_bottom()
        #self.ax1.set_xlim(0,10)
        self.ax1.set_ylim(-10,10)
        self.ax1.patch.set_facecolor('#c0c0c0')
        
        
        self.fig.tight_layout()
        
        
        # creating the Tkinter canvas
        # containing the Matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.fig,master = self.Fplot)  
        self.canvas.draw()
          
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().pack(side='top',fill='both',expand=True)
        
    def init_plots(self):
        myc=['#e41a1c',
             '#377eb8',
            '#4daf4a',
            '#984ea3',
            '#ff7f00',
            '#ffff33']
        myc=['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', 
             '#42d4f4', '#bfef45', '#fabed4', '#469990', '#dcbeff', 
             '#9A6324', '#800000', '#aaffc3', '#808000',  
             '#000075', '#000000','#ffffff']
        
        myd=[[5,1],[3,1,1,1],'']
        
        
 
        
        self.t = np.linspace(0,int(self.numscans.get())-1,int(self.numscans.get()))/int(self.scanrate.get())
        self.data = np.zeros((self.t.size,len(self.InputChannels)))

        
        if type(self.ax1.get_legend()) is not type(None):
            self.ax1.get_legend().remove()

        
        self.lines = []
        for j in range(len(self.InputChannels)):
            self.lines.append(self.ax1.plot([],[],color=myc[j % len(myc)],linewidth=2)[0])
            #self.lines[j].set_dashes(myd[j // len(myc)])
            
            
 
            
        self.legend=[]
        self.legend = self.ax1.legend(self.lines,self.InputNames,loc="center left",fontsize=10,
                                      bbox_to_anchor=(1.01,0.5),facecolor="#c0c0c0")                                     
        self.fig.subplots_adjust(left=.075, bottom=None, right=0.9, top=None, wspace=None, hspace=None)

        for line in self.legend.get_lines():
            line.set_linewidth(6.0)
        
        self.update()
        
        self.canvas.draw()
        
    def makeOutputDirectory(self,y,m,d):
        print(self.SaveRoot.get())
        if not os.path.isdir(self.SaveRoot.get()):
            os.mkdir(self.SaveRoot.get())
        
        ydir = os.path.join(self.SaveRoot.get(),y)
        if not os.path.isdir(ydir):
            os.mkdir(ydir)
            
        mdir = os.path.join(ydir,y+'.'+m)
        if not os.path.isdir(mdir):
            os.mkdir(mdir)
        
        ddir = os.path.join(mdir,m+'.'+d)
        if not os.path.isdir(ddir):
            os.mkdir(ddir)
        
        return(ddir)

        
            
            
        
        
    def createOutput(self):
        output = dict()
        output['t'] = self.t
        output['data'] = self.data
        output['InputChannels'] = self.InputChannels
        output['InputNames'] = self.InputNames

        output['scanrate'] = self.scanrate.get()
        output['numscans'] = self.numscans.get()
        output['scansperread'] = self.scansperread.get()
        output['AcquisitionTime'] = self.lastAcquisition.get()
        if self.doAdwin.get() and os.path.isfile(self.sequencer_file.get()):
            try:
                fdata=scipy.io.loadmat(self.sequencer_file.get())
                tstr = fdata['vals']['ExecutionDateStr'][0][0][0]                
                tseq = datetime.datetime.strptime(tstr,'%d-%b-%Y %H:%M:%S').strftime('%Y-%m-%d_%H-%M-%S')
                output['SequencerTime'] = tseq                
            except Exception:
                print("Unable to load sequencer file.")
                

                
        y = output['AcquisitionTime'][0:4]
        m = output['AcquisitionTime'][5:7]
        d = output['AcquisitionTime'][8:10]
        
        ddir = self.makeOutputDirectory(y,m,d)
        if self.doAdwin.get():
            fname = self.SaveLabel.get() + '_' + output['SequencerTime']+'.mat'
        else:
            fname = self.SaveLabel.get() + '_' + output['AcquisitionTime']+'.mat'
            
        fullname = os.path.join(ddir,fname)

        try: 
            print('saving output to file ' + fname)
            scipy.io.savemat(fullname,output)
        except Exception:
            print("Unable to save data")       
            
            
        if self.doAdwin.get() and os.path.isfile(self.extra_file.get()):
            try:
                fbase, extension = os.path.splitext(fullname)                
                extra_name = fbase + '_extra' + '.mat'    
                
                print(self.extra_file.get())
                print(extra_name)
                shutil.copy(self.extra_file.get(), extra_name)     
            except Exception:
                print("Issue with extra file.")
             
    def configLJM(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
                                ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        #ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
        #                        ljm.constants.STREAM_SCANS_RETURN_ALL)
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
        
    def choosesavedir(self):
        print('what what')
        
    def loadfile(self):
        
        path = filedialog.askopenfilename(initialdir=dir_path+'/conf', title="Select file",
                                          filetypes=(("config file (.json)", "*.json"),("all files", "*.*")))
        print(path)
        if path:
            self.ConfigFile.config(text=path)
            print('Loading from ' + path)
            
            with open(path, "r") as f:
                config = json.load(f)
                    
                if "ip_address" in config:
                    self.connectStr.set(config['ip_address'])
                    self.connectMode.set(self.connectOptions[0])
                if "trigger" in config:
                    self.TriggerChannel =config['trigger']                
                if "analog_channels" in config:
                    self.InputChannels = config['analog_channels']                
                    self.InputNames = config['analog_names']
                    self.init_plots()
                if "scanrate" in config:
                    self.scanrate.set(config['scanrate'])                
                if "numscans" in config:
                    self.numscans.set(config['numscans'])
                if "save_root" in config:
                    self.SaveRoot.set(config["save_root"])
                if "save_label" in config:
                    self.SaveLabel.set(config["save_label"])
                if "scansperread" in config:
                    self.scansperread.set(config["scansperread"])       
                if "delay" in config:
                    self.delay.set(config["delay"])   
                if "associate_with_sequencer" in config:
                    self.doAdwin.set(config["associate_with_sequencer"])   
                if "sequencer_file" in config:
                    self.sequencer_file.set(config["sequencer_file"])   
                    self.doAdwin.set(config["associate_with_sequencer"])   
                if "extra_file" in config:
                    self.extra_file.set(config["extra_file"])   
                if "dosave" in config:
                    self.doSave.set(config["dosave"])   

        else:
            print('Canceling loading new configuration file')        
        
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


        self.stream_thread = stream(self.handle)        
        self.stream_thread.numscans=int(self.numscans.get())
        self.stream_thread.scanrate=int(self.scanrate.get())
        self.stream_thread.scansperread=int(self.scansperread.get())
        self.stream_thread.InputChannels = self.InputChannels
        self.stream_thread.TriggerChannel = self.TriggerChannel
        self.stream_thread.delay=int(self.delay.get())
        self.stream_thread.AcqStatus=self.AcqStatus        
        
        self.stream_thread.start()
        self.process_stream(self.stream_thread)         
        
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
        self.stream_thread = stream(self.handle)            
        self.stream_thread.numscans=int(self.numscans.get())
        self.stream_thread.scanrate=int(self.scanrate.get())
        self.stream_thread.scansperread=int(self.scansperread.get())
        self.stream_thread.InputChannels = self.InputChannels
        self.stream_thread.TriggerChannel = self.TriggerChannel                 
        self.stream_thread.delay=int(self.delay.get())        
        self.stream_thread.AcqStatus=self.AcqStatus        
        self.stream_thread.start()
        self.process_stream(self.stream_thread)  
            
    def stopacq(self):
        self.stream_thread.goodStream = False
        #ljm.eStreamStop(self.handle)               
        #print('stop acquisition')
        
   
    def update(self): 
        for j in range(len(self.InputChannels)):
            self.lines[j].set_data(self.t,self.data[:,j])           
        self.ax1.set_xlim(0,np.amax(self.t))
        self.ax1.set_ylim(-10,10)   
        #self.ax1.set_ylim(auto=True)
        self.canvas.draw()   

        if self.doSave.get():
            self.createOutput()
            
    def on_closing(self):
        self.disconnect()
        self.destroy()

      

#%% Main Loop

if __name__ == "__main__":
     app = App()
     app.protocol("WM_DELETE_WINDOW", app.on_closing)
     app.mainloop()       
