__author__ = 'bruno'
import struct
from .exceptions import EncodeError


def checksum(data):
    if type(data) in (list, tuple):
        data = ''.join(data)
    try:
        return struct.pack('B', (0 - sum(struct.unpack(str(len(data))+'b', data))) & 0b11111111)[0]
    except (struct.error, TypeError) as e:
        raise EncodeError

def fuen_des(origen, destino):
    try:
        return struct.pack('B', int(bin(origen)[2:].zfill(4) + bin(destino)[2:].zfill(4), 2))
    except (struct.error, TypeError) as e:
        raise EncodeError


def fun_lon(funcion, longitud):
    try:
        return struct.pack('B', int(str(bin(funcion)[2:].zfill(3)) + str(bin(longitud)[2:].zfill(5)), 2))
    except (struct.error, TypeError) as e:
         raise EncodeError

"""
TODO: implementar bien la codificacion BCD
def bcd(x):
    bcd_result = ''
    first = True
    for i in str(x):
        if first:
            bcd_result += bin(int(i))[2:]
            first = False
        else:
            bcd_result += bin(int(i))[2:].zfill(4)
    return bcd_result
"""
