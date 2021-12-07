# labjack_cavity_gui.py
# Author : C Fujiwara
#
# This GUI is used to run a labjack T7 as an oscilloscope for monitoring and 
# a spectrum from a Fabry-Perot Interferometer.  Using a reference laser
# as a source for peaks, it locks the separation between two peaks.

# Options
m_name = 'Labjack Cavity'
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

# matplotlib packages

#import matplotlib
#matplotlib.use('TkAgg') # <-- THIS MAKES IT FAST!

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

#%% Main GUI Window

# Create the GUI object
m = tk.Tk()
m.title(m_name)
m.geometry("1200x690")
m.configure(bg="yellow")

# Options Frame
frame_opt = tk.Frame(m,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_opt.pack(side='left',anchor='nw',fill='y')

# Connect Frame
frame_connect = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_connect.grid(row=1,column=1,sticky='we')

# Voltage output
frame_output = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_output.grid(row=2,column=1,sticky='we')

# Acquisition
frame_acquire = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_acquire.grid(row=3,column=1,sticky='we')

# Peak Analysis Settings
frame_peaks = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_peaks.grid(row=4,column=1,sticky='we')

# Peak Analysis Output
frame_peaks_out = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_peaks_out.grid(row=5,column=1,sticky='we')

# Lock Settings
fLock = tk.Frame(frame_opt,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
fLock.grid(row=6,column=1,sticky='we')

# Plots
frame_plot = tk.Frame(m,bd=1,bg="white",highlightbackground="grey",highlightthickness=2)
frame_plot.pack(side='right',fill='both',expand=1)


#%%% Connection Frame

# Connect Label
lConnect = tk.Label(frame_connect,text='Labjack Connection',font=(font_name_lbl,"12"),
                         bg='white',justify='left',bd=0)
lConnect.grid(row=1,column=1,columnspan=3,stick='w')  

# Help Button
bHelp = tk.Button(frame_connect,text='help',font=(font_name,"10"),
                       width=6,bd=3)
bHelp.grid(row=2,column=1)  

# Connect
bConnect=tk.Button(frame_connect,text="connect",
                        bg=_from_rgb((80, 200, 120)),
                        font=(font_name,"10"),width=11,bd=3)
bConnect.grid(row = 2, column=2,sticky='EW')   

# Disconnect
bDisconnect=tk.Button(frame_connect,text="disconnect",
                        bg=_from_rgb((255, 102, 120)),
                        font=(font_name,"10"),width=11,bd=3)
bDisconnect.grid(row = 2, column=3,sticky='NSEW')

# Descriptor
bConnectStr=tk.Entry(frame_connect,
                        bg='white',
                        font=(font_name,"10"))
bConnectStr.grid(row = 3, column=1,columnspan=3,sticky='NSEW')  




#%%% Output Frame  

# Acquisition Label
lOut = tk.Label(frame_output,text='Output',font=(font_name_lbl,"12"),
                         bg='white',justify='left',height=1,bd=0)
lOut.grid(row=1,column=1,sticky='w')  


#
fOut_buttons = tk.Frame(frame_output,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
fOut_buttons.grid(row=2,column=1,sticky='w')



# Down 10mV
bAcqForce=tk.Button(fOut_buttons,text="-20 mV",
                        bg=_from_rgb((255,244,48)),
                        font=(font_name,"10"),width=7,bd=3)
bAcqForce.grid(row = 1, column=1,sticky='w')   

# Down 1mV
bAcqStart=tk.Button(fOut_buttons,text="-5 mV",
                        bg=_from_rgb((255, 255, 255)),
                        font=(font_name,"10"),width=6,bd=3)
bAcqStart.grid(row = 1, column=2,sticky='w')   

# Up 1mV
bAcqStop=tk.Button(fOut_buttons,text="+5 mV",
                        bg=_from_rgb((156, 89, 209)),
                        font=(font_name,"10"),width=6,bd=3)
bAcqStop.grid(row = 1, column=3,sticky='w')  

# Up 10mV
bAcqStop=tk.Button(fOut_buttons,text="+ 20mV",
                        bg=_from_rgb((0, 0, 0)),
                        font=(font_name,"10"),width=6,bd=3,fg='white')
bAcqStop.grid(row = 1, column=4,sticky='nwse')  

    
#
frame_out_tbl = tk.Frame(frame_output,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
frame_out_tbl.grid(row=3,column=1,sticky='nswe')

# Output Voltage
tk.Label(frame_out_tbl,text='output (V)',font=(font_name,"10"),
              bg='white',justify='left',height=1,bd=0,
              width=18).grid(row=1,column=1,columnspan=1,stick='w')  
tk.Entry(frame_out_tbl,
                        bg='white',font=(font_name,"10"),
                        width=14).grid(row = 1, column=2,columnspan=1,sticky='NSEW')   

# Max Voltage
tk.Label(frame_out_tbl,text='output MAX (V)',font=(font_name,"10"),
              bg='white',justify='left',height=1,bd=0,
              width=18).grid(row=2,column=1,columnspan=1,stick='w')  
tk.Entry(frame_out_tbl,
                        bg='white',font=(font_name,"10"),
                        width=10).grid(row = 2, column=2,columnspan=1,sticky='NSEW')   
# Min Voltage
tk.Label(frame_out_tbl,text='output MIN (V)',font=(font_name,"10"),
              bg='white',justify='left',height=1,bd=0,
              width=18).grid(row=3,column=1,columnspan=1,stick='w')  
tk.Entry(frame_out_tbl,
                        bg='white',font=(font_name,"10"),
                        width=10).grid(row = 3, column=2,columnspan=1,sticky='NSEW')    

#%%% Acquisition Frame

# Acquisition Label
lAcquire = tk.Label(frame_acquire,text='Acquisition',font=(font_name_lbl,"12"),
                         bg='white',justify='left',height=1,bd=0)
lAcquire.grid(row=1,column=1,columnspan=1,sticky='w')  


#
frame_acquire_buttons = tk.Frame(frame_acquire,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
frame_acquire_buttons.grid(row=2,column=1,sticky='w')



# Start
bAcqForce=tk.Button(frame_acquire_buttons,text="force acq.",
                        bg='white',
                        font=(font_name,"10"),width=9,bd=3)
bAcqForce.grid(row = 1, column=1,sticky='w')   


# Start
bAcqStart=tk.Button(frame_acquire_buttons,text="start acq.",
                        bg=_from_rgb((85, 205, 252)),
                        font=(font_name,"10"),width=9,bd=3)
bAcqStart.grid(row = 1, column=2,sticky='w')   

# Stop
bAcqStop=tk.Button(frame_acquire_buttons,text="stop acq.",
                        bg=_from_rgb((247, 168, 184)),
                        font=(font_name,"10"),width=9,bd=3)
bAcqStop.grid(row = 1, column=3,sticky='w')  


# Table For Acquistion Settings
frame_acquire_tbl = tk.Frame(frame_acquire,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
frame_acquire_tbl.grid(row=3,column=1,columnspan=3,sticky='nswe')

# Scan Rate
lScanRate = tk.Label(frame_acquire_tbl,text='scan rate (Hz)',font=(font_name,"10"),
                         bg='white',justify='left',height=1,bd=0,width=18)
lScanRate.grid(row=1,column=1,columnspan=1,stick='w')  

eScanRate=tk.Entry(frame_acquire_tbl,
                        bg='white',
                        font=(font_name,"10"),width=14)
eScanRate.grid(row = 1, column=2,columnspan=1,sticky='NSEW')   

# Num Scans
lNumScans = tk.Label(frame_acquire_tbl,text='num scans',font=(font_name,"10"),
                         bg='white',justify='left',height=1,bd=0,width=18)
lNumScans.grid(row=2,column=1,columnspan=1,stick='w')  

eNumScans=tk.Entry(frame_acquire_tbl,
                        bg='white',
                        font=(font_name,"10"),width=14)
eNumScans.grid(row = 2, column=2,columnspan=1,sticky='NSEW')  

# Scans Per read
lScanPread = tk.Label(frame_acquire_tbl,text='scans per read',font=(font_name,"10"),
                         bg='white',justify='left',height=1,bd=0,width=18)
lScanPread.grid(row=3,column=1,columnspan=1,stick='w')  

eScanPread=tk.Entry(frame_acquire_tbl,
                        bg='white',
                        font=(font_name,"10"),width=14)
eScanPread.grid(row = 3, column=2,columnspan=1,sticky='w')  

# Delay
lDelay = tk.Label(frame_acquire_tbl,text='delay (s)',font=(font_name,"10"),
                         bg='white',justify='left',height=1,bd=0,width=18)
lDelay.grid(row=4,column=1,columnspan=1,stick='w')  

eDelay=tk.Entry(frame_acquire_tbl,
                        bg='white',
                        font=(font_name,"10"),width=14)
eDelay.grid(row = 4, column=2,columnspan=1,sticky='w')  

#%%% Peak Analysis Settings Frame

# Peaks Label
tk.Label(frame_peaks,text='Peak Analysis Settings',font=(font_name_lbl,"12"),
         bg='white',justify='left',height=1,bd=0).grid(
             row=1,column=1,columnspan=1,sticky='w')  


# Table For Acquistion Settings
frame_peak_tbl = tk.Frame(frame_peaks,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
frame_peak_tbl.grid(row=2,column=1,columnspan=3,sticky='nswe')

# Time Start
tk.Label(frame_peak_tbl,text='time start (ms)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=1,column=1,columnspan=1,stick='w')  
ePeak1=tk.Entry(frame_peak_tbl,bg='white',font=(font_name,"10"),width=14)
ePeak1.grid(row = 1, column=2,columnspan=1,sticky='NSEW')   

# Time End
tk.Label(frame_peak_tbl,text='time end (ms)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=2,column=1,columnspan=1,stick='w')  
ePeak2=tk.Entry(frame_peak_tbl,bg='white',font=(font_name,"10"),width=14)
ePeak2.grid(row = 2, column=2,columnspan=1,sticky='NSEW')  

# Peak Height
tk.Label(frame_peak_tbl,text='min peak (V)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=3,column=1,columnspan=1,stick='w')  
ePeakH=tk.Entry(frame_peak_tbl,bg='white',font=(font_name,"10"),width=14)
ePeakH.grid(row = 3, column=2,columnspan=1,sticky='NSEW')  

#%%% Peaks Analysis Output 

# Peaks Label
tk.Label(frame_peaks_out,text='Peak Analysis Output',font=(font_name_lbl,"12"),
         bg='white',justify='left',height=1,bd=0).grid(
             row=1,column=1,columnspan=1,sticky='w')  


frame_peakout_tbl = tk.Frame(frame_peaks_out,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
frame_peakout_tbl.grid(row=2,column=1,columnspan=3,sticky='nswe')

# FSR
tk.Label(frame_peakout_tbl,text='FSR (GHz)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=1,column=1,columnspan=1,stick='w') 
tk.Label(frame_peakout_tbl,text='1.5',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=14,borderwidth=1,relief='groove').grid(
             row=1,column=2,columnspan=1,stick='w')  

# FSR (ms)
tk.Label(frame_peakout_tbl,text='FSR meas. (ms)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=2,column=1,columnspan=1,stick='w')  
L_FSR = tk.Label(frame_peakout_tbl,text='n/a',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=14,borderwidth=1,relief='groove')
L_FSR.grid(row=2,column=2,columnspan=1,stick='w')  
             
# dT
tk.Label(frame_peakout_tbl,text='dT meas. (ms)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=3,column=1,columnspan=1,stick='w')  
L_dT = tk.Label(frame_peakout_tbl,text='n/a',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=14,borderwidth=1,relief='groove')
L_dT.grid(row=3,column=2,columnspan=1,stick='w')  

# dF
tk.Label(frame_peakout_tbl,text='df meas. (GHz)',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=18).grid(
             row=4,column=1,columnspan=1,stick='w')  
L_df = tk.Label(frame_peakout_tbl,text='n/a',font=(font_name,"10"),
         bg='white',justify='left',bd=0,width=14,borderwidth=1,relief='groove')
L_df.grid(row=4,column=2,columnspan=1,stick='w')        

#%%% Lock Frame

tk.Label(fLock,text='Lock Settings',font=(font_name_lbl,"12"),
         bg='white',justify='left',height=1,bd=0).grid(
                             row=1,column=1,columnspan=1,sticky='w')  

fLockButt = tk.Frame(fLock,bd=1,bg="white",
                     highlightbackground="grey",highlightthickness=1)
fLockButt.grid(row=2,column=1,sticky='w')

# Start Lock
bAcqForce=tk.Button(fLockButt,text="engage lock",bg=_from_rgb((137, 207, 240)),font=(font_name,"10"),
                    width=15,bd=3).grid(row = 1, column=1,sticky='w')  

# Stop
bAcqForce=tk.Button(fLockButt,text="stop lock",bg=_from_rgb((255, 165, 0)),font=(font_name,"10"),
                    width=14,bd=3).grid(row = 1, column=2,sticky='w')  

# Table For Lock Settings
fLock_tbl = tk.Frame(fLock,bd=1,bg="white",
                                  highlightbackground="grey",highlightthickness=1)
fLock_tbl.grid(row=3,column=1,columnspan=3,sticky='nswe')

# df set
tk.Label(fLock_tbl,text='df set (GHz)',font=(font_name,"10"),
         bg='white',justify='left',height=1,bd=0,width=18).grid(
             row=1,column=1,columnspan=1,stick='w')
tk.Entry(fLock_tbl,bg='white',font=(font_name,"10"),width=14).grid(
    row = 1, column=2,columnspan=1,sticky='NSEW')   

# hysteresis
tk.Label(fLock_tbl,text='hysteresis (GHz)',font=(font_name,"10"),
         bg='white',justify='left',height=1,bd=0,width=18).grid(
             row=2,column=1,columnspan=1,stick='w')
tk.Entry(fLock_tbl,bg='white',font=(font_name,"10"),width=14).grid(
    row = 2, column=2,columnspan=1,sticky='NSEW')  

# step size
tk.Label(fLock_tbl,text='step size (mV)',font=(font_name,"10"),
         bg='white',justify='left',height=1,bd=0,width=18).grid(
             row=3,column=1,columnspan=1,stick='w')
tk.Entry(fLock_tbl,bg='white',font=(font_name,"10"),width=14).grid(
    row = 3, column=2,columnspan=1,sticky='NSEW')  


#%%% Plot Frame

# Acquisition Label
tk.Label(frame_plot,text='Plots',font=(font_name_lbl,"12"),
         bg='white',justify='left',height=1,bd=0).pack(side='top',anchor='nw')  
  

t = np.arange(0.01, 10.0, 0.01)
data1 = np.exp(t)
data2 = np.sin(2 * np.pi * t)
data3 = t

y = [i**2 for i in range(101)]

fig = Figure()

gs = GridSpec(3, 1, figure=fig)

ax1 = fig.add_subplot(gs[:-1, :])
ax1.set_ylabel("voltage (V)",color='black')
ax1.set_xlabel("time (ms)")
ax1.plot(t,data1,color='black')
ax1.tick_params(axis='y', labelcolor='black')

color = 'tab:blue'
ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
color = 'tab:red'
ax2.set_ylabel('ramp (V)', color=color)  # we already handled the x-label with ax1
ax2.plot(t, data2, color=color)
ax2.tick_params(axis='y', labelcolor=color)

ax3 = fig.add_subplot(gs[-1, :])
ax3.plot(t, t, color='black')
ax3.set_ylabel("df measure (GHz)")
ax3.set_xlabel("time")

color = 'tab:blue'
ax4 = ax3.twinx()  # instantiate a second axes that shares the same x-axis
ax4.set_ylabel('output (V)', color=color)  # we already handled the x-label with ax1
ax4.plot(t, data2, color=color)
ax4.tick_params(axis='y', labelcolor=color)

fig.tight_layout()


# creating the Tkinter canvas
# containing the Matplotlib figure
canvas = FigureCanvasTkAgg(fig,
                           master = frame_plot)  
canvas.draw()
  
# placing the canvas on the Tkinter window
canvas.get_tk_widget().pack(side='top',fill='both',expand=True)

# creating the Matplotlib toolbar
#toolbar = NavigationToolbar2Tk(canvas,
                               #frame_plot)
#toolbar.update()
  
# placing the toolbar on the Tkinter window
#canvas.get_tk_widget().pack()


        #canvas1.get_tk_widget().pack(side="top",fill='both',expand=True)
        #canvas1.pack(side="top",fill='both',expand=True)

# %% Callback Functions

# %% Labjack Functions
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

# Start GUI
m.mainloop()
