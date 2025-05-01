# labjack_RAM_record

Author : C Fujiwara

This code is meant to run the labjack T7 pro using the LUA script interface.

There are many tutorials on LUA scripting on the internet, but the basic idea
is that LUA scripting on the labjack allows for direct interfacing from high level
systems (computers, labjack) to low level ones (DIO, AIO, etc.) with relatively
fast speeds ~10-100 kHz.

The main downsides of the T7 pro lua scripts is that each command does NOT take the 
same amount of time.  So the timing can vary depending on the load.  This makes
it non applicable for things that require precise timing. 

The labjack T7 pro lua script may also be run independently of a host computer, which
means that it can be run as an independent system (desirable).

Thus this code contains two halves which may be run independently of each other:

(1) The labjack LUA script (low level), (acquires voltages, runs feedback, etc).
(2) the python acquistiion script (high level), (read RAM values from the labjack).

This separation means that the low-level code does not rely on an digital timing from a 
host computer (slower and non-repeatable).

The main purpose of this code as of 2024/01 is to use a digital PID for the ambient field.

This is a particularly useful regime because :

(1) The ambient field variations are slow (60 Hz, 120 Hz, minutes to hours)
(2) The ambient field is very small (10 mG- 20 mG) (benefits from low noise electronics --> digital is better)
(3) The way we measure the ambient field is complicated. (The field senses all fields from magnets
	--> digital solution allows for many different test condidtions).

INSTRUCTIONS ON HOW TO RUN:

