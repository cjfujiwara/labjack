# labjack_cavity_gui.py
# Author : C Fujiwara
#
# This GUI is used to run a labjack T7 as an oscilloscope for monitoring and 
# a spectrum from a Fabry-Perot Interferometer.  Using a reference laser
# as a source for peaks, it locks the separation between two peaks.

# Options
m_name = 'Labjack Cavity'
font_name = 'arial narrow'

# Import packages
import sys
import datetime
from labjack import ljm
from matplotlib.figure import Figure
import numpy as np
import tkinter
import time

def _from_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb  


# Create the GUI object
m = tkinter.Tk()
m.title(m_name)
m.geometry("800x600")
m.configure(bg="yellow")

# Left panels for options and connections
frame_connect = tkinter.Frame(m,bd=1,bg="white",highlightbackground="black",highlightthickness=1)
frame_connect.pack(anchor="nw",expand=False,side="left")

# Connect
bConnect=tkinter.Button(frame_connect,text="connect",
                        bg=_from_rgb((80, 200, 120)),
                        font=(font_name,"10"),width=8)
bConnect.grid(row = 1, column=1,sticky='NSEW')   

# Disconnect
bDisconnect=tkinter.Button(frame_connect,text="disconnect",
                        bg=_from_rgb((255, 102, 120)),
                        font=(font_name,"10"),width=8)
bDisconnect.grid(row = 1, column=2)   

# Descriptor
bConnectStr=tkinter.Entry(frame_connect,text="disconnect",
                        bg='white',
                        font=(font_name,"10"))
bConnectStr.grid(row = 2, column=1,columnspan=2)   

# Start GUI
m.mainloop()
