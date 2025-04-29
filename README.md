# labjack

Author : C Fujiwara

To get things started on Windows

Install python manager (for this example, Ananconda)

Install LJM Installers
https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit
For windows. This will install :
- Basic drivers
- LogJM useful for debugging
- https://support.labjack.com/docs/ljlogm-basics-guide
- Kipling - useful for debugging, and configuring stuff
- https://support.labjack.com/docs/kipling

This repository is a collection of code to run the labjack T7 pro in an laboratory setting.  The main applications so far as :

(1) As a transfer cavity lock with 1 Hz feedback
(2) A general purpose oscilloscope.

While all of these codes could be separated, I have elected to keep all these code packages as single unit because the code based around them are all relatively similar. Furthermore, the functionality of these applications fall into a general broad category of laboratory tools. 


https://github.com/labjack/labjack-ljm-python

pip install labjack-ljm
conda install -c anaconda scipy
conda install -c conda-forge matplotlib
