# labjack

Author : C Fujiwara

This repository is a collection of code used to run various labjack (and labjack adjacent projects) in the Thywissen Lab at the University for Toronto.

To get things started on Windows

## Installing Drivers

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

