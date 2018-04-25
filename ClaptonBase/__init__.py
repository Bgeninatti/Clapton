"""
This module provides several tools useful to interact with TKLan protocol
developed by Teknotrol. This is the main protocol used to interact betwen
Teknotrol electronics devices and microcontroller.

The Clapton project was maded to give that protocol the hability to interact
with higer level lenguages and applications, following the concept of IoT.abs

Initialy Clapton was maded to run in a Raspberry Pi, but you can use it with
any computer with serial port.


..moduleauthor:: Bruno Geninatti <bruno@teknotrol.com>

"""

__author__ = 'Bruno Geninatti'
__all__ = ["exceptions", "decode", "encode", "utils", "serial",
           "containers"]
