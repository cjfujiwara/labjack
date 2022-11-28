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

        self.lastacquisition    = None 
        
        self.delay              = None
        self.timeout            = None

       
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
        
     
        #print('n olonger waiting')
        # Configure and start stream
        print('starting stream')
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
                    if ((time.time()-t2)-Tacquire)>self.timeout:
                        self.AcqStatus.config(text='ACQUISITION TIMEOUT',fg='red')
                        self.AcqStatus.update()
                        self.goodStream=0
                    sys.stdout.flush()
                    continue
                else: 
                    print('hi')
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



class App(tk.Tk):
    def __init__(self):        
        # Create the GUI object
        super().__init__()
        self.title('Labjack Pulse Analysis')
        self.geometry("1280x780")
        
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
        self.timeout = tk.StringVar(self)         # Output Voltage Min 

        self.t = np.linspace(0, 300, 301)
        self.y1 = np.exp(-self.t)
     
        self.defaultSettings()        
        self.create_frames()        
        self.create_widgets() 
        self.create_plots()                   
        
    def process_stream(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.process_stream(thread))

        else:
            #self.AcqStatus.config(text=thread.Status,fg=thread.StatusColor)
                
            if thread.goodStream:
                self.t = thread.t
                self.y1 = thread.y1
                #self.y2 = thread.y2
                self.lastAcquisition = thread.lastacquisition                
                self.update()
                
            if self.doAutoAcq:    
                self.after(int(self.delay.get()),self.doTrigAcq())
            else:
                self.forcebutt['state']='normal'
                self.acqbutt['state']='normal' 
                self.set_state(self.acqtbl,'normal')
                #self.set_state(self.Fpeak,'normal')


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
        
     
        # Plots
        self.Fplot = tk.Frame(self,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
        self.Fplot.pack(side='right',fill='both',expand=1)
        
    def defaultSettings(self):
        self.connectStr.set('470026765')   
        self.connectMode.set(self.connectOptions[2])
        
        #self.connectStr.set('192.168.0.177')   
        #self.connectMode.set(self.connectOptions[0])
        
        self.connectStr.set(defaultIP)   
        self.connectMode.set(self.connectOptions[0])
        
        # Output voltage default values
        self.output.set('??')
        self.outputMax.set('2500')
        self.outputMin.set('0')    
        
        self.scanrate.set('10000')
        self.numscans.set('1000')
        self.scansperread.set('1000')
        self.delay.set('500')
        self.timeout.set('30')

    
        
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
                     
        # Timeout
        tk.Label(self.acqtbl,text='timeout (s)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=5,column=1,columnspan=1,stick='w')  

        tk.Entry(self.acqtbl,bg='white',justify='center',textvariable=self.timeout,
                 font=(font_name,"10"),width=14,validatecommand=self.vcmdNum,validate='key').grid(
                     row=5,column=2,columnspan=1,sticky='w')  

    
    
        vcmd1 = (self.register(self.onValidateStart),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')
        vcmd2 = (self.register(self.onValidateEnd),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')        
        
       
        
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
        self.ax1.set_ylabel("voltage (mV)",color='black')
        self.ax1.set_xlabel("time (ms)")
        self.p1, = self.ax1.plot(self.t,self.y1,color='black')
        self.ax1.set_xlim([0,300])
        
        self.ax1.grid(True)
        
       
        self.ax1.tick_params(axis='y', labelcolor='black')        
 

        self.fig.tight_layout()
        
        
        # creating the Tkinter canvas
        # containing the Matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.fig,master = self.Fplot)  
        self.canvas.draw()
          
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().pack(side='top',fill='both',expand=True)
        

             
    def configLJM(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
                                ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        #ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, 
         #                      ljm.constants.STREAM_SCANS_RETURN_ALL)
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
        
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.TriggerChannel, 12);   # conditional reset
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.TriggerChannel, 1);    # 1 is rising 0 is falling   
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_B" % self.TriggerChannel, 1);       # number of triggers to reset


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
        #self.set_state(self.Fpeak,'disabled')

        stream_thread = stream(self.handle)        
        stream_thread.numscans=int(self.numscans.get())
        stream_thread.scanrate=int(self.scanrate.get())
        stream_thread.scansperread=int(self.scansperread.get())
        stream_thread.InputChannels = self.InputChannels
        stream_thread.TriggerChannel = self.TriggerChannel
        stream_thread.delay=int(self.delay.get())
        stream_thread.timeout=int(self.delay.get())

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
        stream_thread = stream(self.handle)            
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
   
    def update(self): 
        self.p1.set_data(self.t,self.y1)        
        self.ax1.set_xlim(0,np.amax(self.t))
        self.ax1.set_ylim(-100,8000)        
        self.canvas.draw()   
            
    def on_closing(self):
        self.disconnect()
        self.destroy()

                


#%% Main Loop

if __name__ == "__main__":
     app = App()
     app.protocol("WM_DELETE_WINDOW", app.on_closing)
     app.mainloop()       
