import struct
import sys
from .exceptions import DecodeError


def fuen_des(byte):
    try:
        add = struct.unpack('B', byte)[0]
        return add >> 4, add & 0b00001111, byte
    except (struct.error, TypeError) as e:
        raise DecodeError


def fun_lon(byte):
    try:
        add = struct.unpack('B', byte)[0]
        return add >> 5, add & 0b00011111, byte
    except (struct.error, TypeError) as e:
        raise DecodeError


def validate_cs(paq):
    try:
        if not len(paq):
            return False
        return sum(struct.unpack(
            '{}b'.format(len(paq)), paq)) & 0b11111111 == 0
    except (struct.error, TypeError) as e:
        raise DecodeError
