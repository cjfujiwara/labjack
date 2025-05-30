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


This will tell you how to instal the python drivers
https://support.labjack.com/docs/python-for-ljm-windows-mac-linux

https://github.com/labjack/labjack-ljm-python

Then I recommend installing scipy and matplotlib

conda install -c anaconda scipy

conda install -c conda-forge matplotlib

## Projects
We use the labjack for a variety of projects in the laboratory.  Here are they.

/temperature-humidity [HVAC Monitoring](temperature-humidity/README.md) -  used everyday (as of 2025)

/thermistor-flow [Electromagnet Temperature and Flow Rates](BigShim/README.md) - used everyday (as of 2025)

/oscilloscope [General Purpose Oscilloscope](temperature-humidity/README.md) -used everyday (as of 2025)

/BigShim [Stabilization of Ambient Magnetic Field](BigShim/README.md) -  used everyday (as of 2025)

/chillers [Digital communication with chiller](chillers/README.md) -  used everday (as of 2025)

/weather [Monitoring of Local Weather](weather/README.md) -  used everyday (as of 2025)

/Wavemeter WA-1000  [Digital communication with 100 MHz WA-1000 Wavemeter](Wavemeter WA-1000/README.md) - last used for PA experiment

/Wavemeter [Digital Communication with Wavemeter](Wavemter/README.md) - last used for PA experiment

/Vortex [Locking of Vortex using Wavemeter](temperature-humidity/README.md) - last used for PA experiment (2022/2023)

/cavity_lock ["Locking" of ECDL via Cavity](temperature-humidity/README.md) - last used for p-wave experiment (2021)
