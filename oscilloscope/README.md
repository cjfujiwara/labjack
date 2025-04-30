# Oscilloscope
This code utilizing the labjack T7 as a general purpose oscilloscope.  Because the T7 has a multiplexed analog read using the STREAM command, do not rely on specific timings from this software.

The primary code to run is the labjack_oscilloscope.py code which opens up a GUI.  The configuration files are .json files which are located in the config_files directory.

A few reminders:
- This code uses the STREAM command.
- During an active STREAM, the labjack will not communicate until the STREAM is complete.
- The analog signals are time multiplexed.
- It is recommended to keep the total sample rate (Nchannels * sample rate) to be <100 kHz.
