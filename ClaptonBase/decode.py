from bitarray import bitarray
from .exceptions import DecodeError


def sender_destination(byte):
    if not isinstance(byte, bytes):
        raise TypeError
    if len(byte) != 1:
        raise DecodeError
    sender, destination = byte[0] >> 4, byte[0] & 0b00001111
    return sender, destination

def function_length(byte):
    if not isinstance(byte, bytes):
        raise TypeError
    if len(byte) != 1:
        raise DecodeError
    function, length = byte[0] >> 5, byte[0] & 0b00011111
    return function, length

def validate_checksum(bytes_chain):
    if not isinstance(bytes_chain, bytes):
        raise TypeError
    return sum(bytes_chain) & 0b11111111 == 0
