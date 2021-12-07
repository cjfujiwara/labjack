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


import ljm_stream_util

# matplotlib packages
from matplotlib.gridspec import GridSpec
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)

# Math
import numpy as np

# Convert RGB triplet to tk color that is interprable
def _from_rgb(rgb):
    """translates an rgb tuple of int to a tk friendly color code
    """
    return "#%02x%02x%02x" % rgb  

class App(tk.Tk):
    def __init__(self):        
        # Create the GUI object
        super().__init__()
        self.title('Labjack Cavity')
        self.geometry("1280x720")
        
        self.connectOptions = [
        "IP address (ETH)",
        "serial number (USB)",
        "serial number (ETH)"
        ]    
        
        # Internal Labjack Settings
        self.isConnected = False
        self.TriggerChannel = "DIO0"
        self.InputChannels = ["AIN0", "AIN1"]
        self.OutputChannel = "DAC0"

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
        
        self.t = np.arange(0.01, 10.0, 0.01)
        self.data1 = np.exp(self.t)
        self.data2 = np.sin(2 * np.pi * self.t)
        self.data3 = self.t
        
        self.defaultSettings()        
        self.create_frames()        
        self.create_widgets() 
        self.create_plots()
    
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

        self.connectMode.set(self.connectOptions[1])
        # Output voltage default values
        self.output.set('??')
        self.outputMax.set('2500')
        self.outputMin.set('0')    
        
        self.scanrate.set('20000')
        self.numscans.set('5500')
        self.scansperread.set('5500')
        self.delay.set('500')

        self.tstart.set('100')
        self.tend.set('240')
        self.minpeak.set('500')
        self.FSR.set('1500')
        
        self.FSRtime.set('??')
        self.dT.set('??')
        self.dF.set('??')    
        
        self.dFset.set('-200')
        self.hys.set('200')
        self.dV.set('1')  

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
        tk.Button(self.Fconnect,text="connect",bg=_from_rgb((80, 200, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.connect).grid(row=3,column=2,sticky='EW')   
        # Disconnect
        tk.Button(self.Fconnect,text="disconnect",bg=_from_rgb((255, 102, 120)),
                  font=(font_name,"10"),width=11,bd=3,command=self.disconnect).grid(row = 3, column=3,sticky='NSEW')
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
        tk.Button(f,text="-100",bg=_from_rgb((255,0,24)),font=(font_name,"10"),
                  width=4,bd=3,command=lambda: self.increment(-100)).grid(row=1,column=1,sticky='w')  
        
        # Down 20 mV
        tk.Button(f,text="-20",bg=_from_rgb((255,165,44)),font=(font_name,"10"),
                  width=4,bd=3,command=lambda: self.increment(-20)).grid(row=1,column=2,sticky='w')
           
        # Down 5 mV
        tk.Button(f,text="-5",bg=_from_rgb((255, 255, 65)),
                  font=(font_name,"10"),width=2,bd=3,command=lambda: self.increment(-5)).grid(
                                    row=1,column=3,sticky='w')   
        
        # Up 5 mV
        tk.Button(f,text="+5",bg=_from_rgb((0, 128, 24)),font=(font_name,"10"),
                  width=2,bd=3,fg='white',command=lambda: self.increment(5)).grid(row=1,column=4,sticky='w')  
        
        # Up 20 mV
        tk.Button(f,text="+ 20",bg=_from_rgb((0, 0, 249)),font=(font_name,"10"),
                  width=4,bd=3,fg='white',command=lambda: self.increment(20)).grid(row = 1, column=5,sticky='nwse')          
        # Up 100 mV
        tk.Button(f,text="+ 100",bg=_from_rgb((134, 0, 125)),font=(font_name,"10"),
                  width=4,bd=3,fg='white',command=lambda: self.increment(100)).grid(row = 1, column=6,sticky='nwse')          
                
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
                 width=10).grid(row = 2, column=2,columnspan=1,sticky='NSEW')   
        # Min Voltage
        tk.Label(tbl,text='output MIN (mV)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl,bg='white',font=(font_name,"10"),justify='center',textvariable=self.outputMin,
                 width=10).grid(row = 3, column=2,columnspan=1,sticky='NSEW')    
        
        # Acquisition Settings
        tk.Label(self.Facquire,text='Acquisition',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')
                     
        # Frame for acquisition buttons
        f2 = tk.Frame(self.Facquire,bd=1,bg="white",highlightbackground="grey",
                      highlightthickness=1)
        f2.grid(row=2,column=1,sticky='w')

        # force acquisition
        tk.Button(f2,text="force acq.",bg='white',font=(font_name,"10"),
                  width=9,bd=3,command=self.forceacq).grid(row = 1, column=1,sticky='w')  

        # Start acquisition
        tk.Button(f2,text="start acq.",bg=_from_rgb((85, 205, 252)),
                  font=(font_name,"10"),width=9,bd=3).grid(row=1,column=2,sticky='w')   

        # Stop acquisition
        tk.Button(f2,text="stop acq.",bg=_from_rgb((247, 168, 184)),
                  font=(font_name,"10"),width=9,bd=3).grid(row = 1, column=3,sticky='w')  

        tbl2 = tk.Frame(self.Facquire,bd=1,bg="white",highlightbackground="grey",
                        highlightthickness=1)
        tbl2.grid(row=3,column=1,columnspan=3,sticky='nswe')        

        # Scan Rate
        tk.Label(tbl2,text='scan rate (Hz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')
                    
        tk.Entry(tbl2,bg='white',justify='center',textvariable=self.scanrate,
                 font=(font_name,"10"),width=14).grid(
                     row=1,column=2,columnspan=1,sticky='NSEW')   

        # Num Scans
        tk.Label(tbl2,text='num scans',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  

        tk.Entry(tbl2,bg='white',justify='center',textvariable=self.numscans,
                 font=(font_name,"10"),width=14).grid(
                     row=2,column=2,columnspan=1,sticky='NSEW')  

        # Scans Per read
        tk.Label(tbl2,text='scans per read',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  

        tk.Entry(tbl2,bg='white',justify='center',textvariable=self.scansperread,
                 font=(font_name,"10"),width=14).grid(
                     row=3,column=2,columnspan=1,sticky='w')  

        # Delay
        tk.Label(tbl2,text='delay (ms)',font=(font_name,"10"),bg='white',
                 justify='left',height=1,bd=0,width=18).grid(
                     row=4,column=1,columnspan=1,stick='w')  

        tk.Entry(tbl2,bg='white',justify='center',textvariable=self.delay,
                 font=(font_name,"10"),width=14).grid(
                     row=4,column=2,columnspan=1,sticky='w')  

        # Peaks Analysis Settings
        tk.Label(self.Fpeak,text='Peak Analysis Settings',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                     row=1,column=1,columnspan=1,sticky='w')  
        
        
        # Frame for peak analysis settingss
        tbl3 = tk.Frame(self.Fpeak,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        tbl3.grid(row=2,column=1,columnspan=3,sticky='nswe')
        
        # Time Start
        tk.Label(tbl3,text='time start (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.tstart).grid(
                     row=1,column=2,columnspan=1,sticky='NSEW')   
        
        # Time End
        tk.Label(tbl3,text='time end (ms)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.tend).grid(
                     row=2,column=2,columnspan=1,sticky='NSEW')  
        
        # Peak Height
        tk.Label(tbl3,text='min peak (mV)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.minpeak).grid(
                     row=3,column=2,columnspan=1,sticky='NSEW')  
        
        # FSR
        tk.Label(tbl3,text='FSR (MHz)',font=(font_name,"10"),bg='white',
                 justify='left',bd=0,width=18).grid(row=4,column=1,columnspan=1,stick='w') 
        tk.Entry(tbl3,bg='white',font=(font_name,"10"),justify='center',
                 width=14,textvariable=self.FSR).grid(row=4,column=2,columnspan=1,sticky='NSEW')  

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
        tk.Label(tbl4,text='\u0394f meas. (GHz)',font=(font_name,"10"),
                 bg='white',justify='left',bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')  
        tk.Label(tbl4,textvariable=self.dF,font=(font_name,"10"),bg='white',justify='left',
                 bd=0,width=14,borderwidth=1,relief='groove').grid(
                     row=3,column=2,columnspan=1,stick='ew')        
        
        # Lock Settings Label
        tk.Label(self.Flock,text='Lock Settings',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).grid(
                                     row=1,column=1,columnspan=1,sticky='w')  
        # Lock Button Frame
        f4 = tk.Frame(self.Flock,bd=1,bg="white",
                             highlightbackground="grey",highlightthickness=1)
        f4.grid(row=2,column=1,sticky='w')
        
        # Start Lock
        tk.Button(f4,text="engage lock",bg=_from_rgb((137, 207, 240)),font=(font_name,"10"),
                  width=15,bd=3).grid(row = 1, column=1,sticky='w')  
        
        # Stop Lock
        tk.Button(f4,text="stop lock",bg=_from_rgb((255, 165, 0)),font=(font_name,"10"),
                  width=14,bd=3).grid(row = 1, column=2,sticky='w')  
        
        # Table For Lock Settings
        tbl4 = tk.Frame(self.Flock,bd=1,bg="white",highlightbackground="grey",highlightthickness=1)
        tbl4.grid(row=3,column=1,columnspan=3,sticky='nswe')
        
        # df set
        tk.Label(tbl4,text='\u0394f set (GHz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=1,column=1,columnspan=1,stick='w')
        tk.Entry(tbl4,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.dFset).grid(
            row=1,column=2,columnspan=1,sticky='NSEW')   
        
        # hysteresis
        tk.Label(tbl4,text='hysteresis (MHz)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=2,column=1,columnspan=1,stick='w')
        tk.Entry(tbl4,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.hys).grid(
            row=2,column=2,columnspan=1,sticky='NSEW')  
        
        # step size
        tk.Label(tbl4,text='\u0394V output step (mV)',font=(font_name,"10"),
                 bg='white',justify='left',height=1,bd=0,width=18).grid(
                     row=3,column=1,columnspan=1,stick='w')
        tk.Entry(tbl4,bg='white',font=(font_name,"10"),justify='center',width=14,textvariable=self.dV).grid(
            row = 3, column=2,columnspan=1,sticky='NSEW')  
        
    def create_plots(self):
        # Acquisition Label
        tk.Label(self.Fplot,text='Plots',font=(font_name_lbl,"12"),
                 bg='white',justify='left',height=1,bd=0).pack(side='top',anchor='nw')                    

        self.fig = Figure()
        
        gs = GridSpec(3, 1, figure=self.fig)        
        self.ax1 = self.fig.add_subplot(gs[:-1, :])
        self.ax1.set_ylabel("cavity voltage (V)",color='black')
        self.ax1.set_xlabel("time (ms)")
        self.p1, = self.ax1.plot(self.t,self.data1,color='black')
        self.ax1.tick_params(axis='y', labelcolor='black')
        
        color = 'tab:blue'
        self.ax2 = self.ax1.twinx()  # instantiate a second axes that shares the same x-axis
        color = 'tab:red'
        self.ax2.set_ylabel('cavity ramp (V)', color=color)  # we already handled the x-label with ax1
        self.p2,=self.ax2.plot(self.t, self.data2, color=color)
        self.ax2.tick_params(axis='y', labelcolor=color)
        
        self.ax3 = self.fig.add_subplot(gs[-1, :])
        self.p3,=self.ax3.plot(self.t, self.t, color='black')
        self.ax3.set_ylabel(r"$\Delta f~\mathrm{measure}~(\mathrm{GHz})$")
        self.ax3.set_xlabel("time")
        
        color = 'tab:blue'
        self.ax4 = self.ax3.twinx()  # instantiate a second axes that shares the same x-axis
        self.ax4.set_ylabel('output (V)', color=color)  # we already handled the x-label with ax1
        self.p4,=self.ax4.plot(self.t,self.data2, color=color)
        self.ax4.tick_params(axis='y', labelcolor=color)
        
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
            info = ljm.getHandleInfo(self.handle)
            print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
                  "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
                  (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
            val = ljm.eReadName(self.handle, self.OutputChannel) 
            self.output.set(str(np.round(1000*val,1)))
            self.ConnectStatus.config(text='connected',fg='green')
            
            self.configureLJMForTriggeredStream()
            self.configureDeviceForTriggeredStream()
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)    # Internal clock stream
            #ljm.eStreamStop(self.handle)   

    def disconnect(self):
        if self.isConnected:
            print('disconnecting from labjack')
            ljm.close(self.handle)
            self.isConnected = False
            self.ConnectStatus.config(text='disconnected',fg='red')
            
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
            
    def configureLJMForTriggeredStream(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)

    def configureDeviceForTriggeredStream(self):
        address = ljm.nameToAddress(self.TriggerChannel)[0]
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", address);
    
        # Clear any previous settings on triggerName's Extended Feature registers
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 0);
    
        # 5 enables a rising or falling edge to trigger stream
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % self.TriggerChannel, 4);
        ljm.eWriteName(self.handle, "%s_EF_CONFIG_A" % self.TriggerChannel, 1);

        # Enable
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % self.TriggerChannel, 1);
        
    def forceacq(self):
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)
        result = self.burstStream()
        if result:
            print('yay')
            self.updatePlots()
            
    def updatePlots(self):
        self.p1.set_data(self.t,self.data[:,0])
        
        """
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
        
        plotsData.append(ax1.plot([],[],color=myc[j % len(myc)],linestyle='dashed',linewidth=2)[0])
        plotsData[j].set_dashes(myd[j // len(myc)])
        """
        
        
    def burstStream(self):
        
        # Scan list addresses for streamBurst    
        nAddr = len(self.InputChannels)
        aScanList = ljm.namesToAddresses(nAddr, self.InputChannels)[0]   
        
        # Get the scan rate (Hz) and number of total samples    
        scanrate=float(self.scanrate.get())
        numscans=int(self.numscans.get())
        scansperread=int(self.scansperread.get()) 
        Tacquire = numscans/scanrate
        samplerate = scanrate*nAddr
        
        # Display acquisition settings
        #print("\n " + "Scan rate".ljust(20) + ": %s Hz" % scanrate)
        #print(" " + "Number of Scans".ljust(20) + ": %s" % numscans)
        #print(" " + "Total Duration".ljust(20) + ": %s sec" % Tacquire) 
        #print(" " + "Scans per read".ljust(20) + ": %s" % scansperread) 
        #print(" " + "Number of Channels".ljust(20) + ": %s" % nAddr)
        #print(" " + "Total Sample rate".ljust(20) + ": %s Hz" % samplerate)    
        
        # Initilize Counters
        totScans = 0            # Total scans read
        totSkip = 0             # Total skipped samples
        i = 1                   # Number of reads
        ljmScanBacklog = 0      # Backlog on the LJM
        dataAll=[]              # All data
        isGood=True
        
        
     #   long long time0 = LJM_GetHostTick();
   # err = LJM_eReadName(handle, "SERIAL_NUMBER", &value);
    #long long time1 = LJM_GetHostTick();


        # Configure and start stream
        scanrate = ljm.eStreamStart(self.handle, scansperread, nAddr, aScanList, scanrate)    


        while (totScans < numscans) & isGood:

            ljm_stream_util.variableStreamSleep(scansperread, scanrate, ljmScanBacklog)
            try:

                ret = ljm.eStreamRead(self.handle) # read data in buffer

                # Recrod the data
                aData = ret[0]
                ljmScanBacklog = ret[2]
                scans = len(aData) / nAddr
                totScans += scans 
                dataAll+=aData                
             
                # -9999 values are skipped ones
                curSkip = aData.count(-9999.0)
                totSkip += curSkip    
                
                #print("eStreamRead %i : %i scans, %0.0f scans skipped, %i device backlog, %i in LJM backlog" % (i,totScans, curSkip/nAddr, ret[1], ljmScanBacklog))

                # Increment read counter    
                i += 1
                # do stuff

            except ljm.LJMError as err:
                if err.errorCode == ljm.errorcodes.NO_SCANS_RETURNED:     
                    sys.stdout.flush()
                    continue
                else: 
                    ljme = sys.exc_info()[1]
                    print(ljme)
                    isGood=False  

          
        tAcq = time.strftime('%Y-%m-%d_%H-%M-%S') 

        try:
            ljm.eStreamStop(self.handle)   
        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
        except Exception:
            e = sys.exc_info()[1]
            print(e)    
            
        if isGood:       
            tVec = (np.array([range(numscans)]).T)/scanrate
            data = np.zeros((numscans,nAddr))
            data=np.array(dataAll).reshape(numscans,nAddr)            
            self.t = tVec
            self.data = data
            self.lastacquisition = tAcq
            if totSkip>0:
                print(totSkip)
                
        return isGood   
      
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
