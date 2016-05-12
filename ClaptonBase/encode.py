__author__ = 'bruno'
import struct


def checksum(data):
    if type(data) == (list, tuple):
        data = ''.join(data)

    return struct.pack('B', (0 - sum(struct.unpack(str(len(data))+'b', data))) & 0b11111111)[0]


def fuen_des(origen, destino):
    try:
        return struct.pack('B', int(bin(origen)[2:].zfill(4) + bin(destino)[2:].zfill(4), 2))
    except struct.error:
        return None


def fun_lon(funcion, longitud):
    try:
        return struct.pack('B', int(str(bin(funcion)[2:].zfill(3)) + str(bin(longitud)[2:].zfill(5)), 2))
    except struct.error:
        return None


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