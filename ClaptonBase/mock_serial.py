import serial
import struct
import binascii
from .exceptions import WriteException, ReadException, ChecksumException, NoMasterException, SerialConfigError


class MockSerial(object):

    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.buffer = list()
        self.raise_serial_error = 0
        self.open()

    def open(self):
        if self.raise_serial_error:
            self.raise_serial_error -= 1
            raise serial.SerialException

    def close(self):
        pass

    def flushInput(self):
        pass

    def read(self, n=1):
        if self.raise_serial_error:
            self.raise_serial_error -= 1
            raise AttributeError
        rta = ''
        if not len(self.buffer):
            return binascii.unhexlify(rta)
        for i in range(n):
            rta += self.buffer.pop()
        return binascii.unhexlify(rta)

    def write(self, data):
        if self.raise_serial_error:
            self.raise_serial_error -= 1
            raise serial.portNotOpenError
