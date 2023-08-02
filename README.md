# labjack

Author : C Fujiwara

This repository is a collection of code to run the labjack T7 pro in an laboratory setting.  The main applications so far as :

(1) As a transfer cavity lock with 1 Hz feedback
(2) A general purpose oscilloscope.

While all of these codes could be separated, I have elected to keep all these code packages as single unit because the code based around them are all relatively similar. Furthermore, the functionality of these applications fall into a general broad category of laboratory tools. 


https://github.com/labjack/labjack-ljm-python

pip install labjack-ljm
conda install -c anaconda scipy
conda install -c conda-forge matplotlib
