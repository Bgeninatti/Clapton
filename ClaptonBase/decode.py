from bitarray import bitarray
from .exceptions import DecodeError


def sender_destination(byte):
    if not isinstance(byte, bytes):
        raise TypeError
    if len(byte) != 1:
        raise DecodeError
    bits = bitarray()
    bits.frombytes(byte)
    sender, destination = bits[:4].tobytes()[0] >> 4, bits[4:].tobytes()[0] >> 4
    return sender, destination

def function_length(byte):
    if not isinstance(byte, bytes):
        raise TypeError
    if len(byte) != 1:
        raise DecodeError
    bits = bitarray()
    bits.frombytes(byte)
    function, length = bits[:5].tobytes()[0] >> 5, bits[5:].tobytes()[0] >> 3
    return function, length

def validate_checksum(bytes_chain):
    if not isinstance(bytes_chain, bytes):
        raise TypeError
    return sum(bytes_chain) & 0b11111111 == 0
