__author__ = 'bruno'
import struct
from .exceptions import EncodeError


def checksum(data):
    try:
        return struct.pack('B', (0 - sum(struct.unpack('{}b'.format(len(data)), data)) & 0b11111111))
    except (struct.error, TypeError) as e:
        raise EncodeError

def fuen_des(origen, destino):
    try:
        if type(origen) != int:
            origen = int(origen)
        if type(destino) != int:
            destino = int(destino)
    except (ValueError, TypeError) as e:
        raise EncodeError
    if origen > 15 or destino > 15:
        raise EncodeError
    return struct.pack('B', int(bin(origen)[2:].zfill(4) + bin(destino)[2:].zfill(4), 2))


def fun_lon(funcion, longitud):
    try:
        if type(funcion) != int:
            funcion = int(funcion)
        if type(longitud) != int:
            longitud = int(longitud)
    except (ValueError, TypeError) as e:
        raise EncodeError
    if funcion > 7 or longitud > 31:
        raise EncodeError

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
