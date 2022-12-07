# Luigs & Neumann SM-10
A Python class for interfacing Luigs and Neumann SM-10 controller

Based on the [Luigs & Neumann SM-5 class](https://github.com/mgraupe/LuigsAndNeumannSM5) of [mgraupe](https://github.com/mgraupe)

Main differences are:
- CRC is deprecated and only present for backward compatibility in the serial commands (according to Luigs & Neumann)
- SM-10 doesn't seem to lose connection after 3 seconds (like SM-5)

This is a work in progress. Here are the commands implemented so far:
- 0x0101 - Inquire Position
- 0x0048, 0x0049, 0x004a, 0x004b - Approach Position (these have been bundled together in a single method)
