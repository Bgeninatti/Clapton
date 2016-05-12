__author__ = 'bruno'
import struct


def fuen_dest(byte):
    try:
        add = struct.unpack('B', byte)
        return add[0] >> 4, add[0] & 0b00001111, byte
    except struct.error:
        return None, None, byte


def func_lon(byte):
    try:
        add = struct.unpack('B', byte)
        return add[0] >> 5, add[0] & 0b00011111, byte
    except struct.error:
        return None, None, byte


def validate_cs(paq):
    try:
        return sum([struct.unpack('b', i)[0] for i in paq]) & 0b11111111 == 0
    except struct.error:
        return False


def bcd(x):
    return int(str((x & 0b11110000) / 16) + str(x & 0b00001111))