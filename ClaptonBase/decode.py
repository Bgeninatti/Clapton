__author__ = 'bruno'
import struct
from .exceptions import DecodeError


def fuen_des(byte):
    try:
        add = struct.unpack('B', byte)
        return add[0] >> 4, add[0] & 0b00001111, byte
    except (struct.error, TypeError) as e:
        raise DecodeError


def fun_lon(byte):
    try:
        add = struct.unpack('B', byte)
        return add[0] >> 5, add[0] & 0b00011111, byte
    except (struct.error, TypeError) as e:
        raise DecodeError


def validate_cs(paq):
    try:
        return sum([struct.unpack('b', i)[0] for i in paq]) & 0b11111111 == 0
    except (struct.error, TypeError) as e:
        raise DecodeError

"""
TODO: implementar bien la decodificacion BCD
def bcd(x):
    return int(str((x & 0b11110000) / 16) + str(x & 0b00001111))
"""
