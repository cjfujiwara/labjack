# labjack

Author : C Fujiwara

This repository is a collection of code used to run various labjack (and labjack adjacent projects) in the Thywissen Lab at the University for Toronto.

To get things started on Windows

## Installing Drivers and Software

Install python manager (for this example, Ananconda)

Install LJM Installers
https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit
For windows. This will install :
- Basic drivers
- LogJM useful for debugging
- https://support.labjack.com/docs/ljlogm-basics-guide
- Kipling - useful for debugging, and configuring stuff
- https://support.labjack.com/docs/kipling

- One you install that stuff. Now you can interact with the labjack normally. BUT we want to run code on python for specific tasks. How do you do that? Well, with anaconda + spyder or whatever thing you want.


This will tell you how to instal lthe python drivers
https://support.labjack.com/docs/python-for-ljm-windows-mac-linux

https://github.com/labjack/labjack-ljm-python

Then I recommend installing scipy and matplotlib

conda install -c anaconda scipy

conda install -c conda-forge matplotlib

## Projects

[HVAC Monitoring](temperature-humidity/README.md) - used everyday (circa 2025)

[Electromagnet Temperature and Flow Rates](BigShim/README.md) - used everyday (circa 2025)

[General Purpose Oscilloscope](temperature-humidity/README.md) - used everyday (circa 2025)

[Stabilization of Ambient Magnetic Field](BigShim/README.md) - used everyday (circa 2025)


[Cavity Lock](temperature-humidity/README.md) - last used for PA experiment

[Vortex Wavemeter Lock](temperature-humidity/README.md) - last used for PA experiment

[Wavemeter](temperature-humidity/README.md) - last used for PA experiment

[Wavemeter WA-1000](temperature-humidity/README.md) - last used for PA experiment


### HVAC Monitoring 
We use a labjack in conjunction with EL-1050
: temperature and humidity
Flow rate Monitoring
magnet temperature monitoring
general purpose oscilloscope
CATs
QPD
cavity stabilization lock 
locking the Vortex laser using an absolute frequency reference (Vutha wavemeter)
stabilization of external magnetic fields


