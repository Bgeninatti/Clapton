from bitarray import bitarray
from .exceptions import EncodeError


def make_checksum(bytes_chain):
    if not isinstance(bytes_chain, bytes):
        raise TypeError
    return bytes([0-sum(bytes_chain) & 0b11111111])


def sender_destination(sender, destination):
    if not isinstance(sender, int) or not isinstance(destination, int):
        raise TypeError
    if sender > 15 or destination > 15:
        raise EncodeError
    bits = bitarray(bin(sender)[2:].zfill(4))
    bits.extend(bin(destination)[2:].zfill(4))
    return bits.tobytes()


def function_length(function, length):
    if not isinstance(function, int) or not isinstance(length, int):
        raise TypeError
    if function > 7 or length > 31:
        raise EncodeError
    bits = bitarray(bin(function)[2:].zfill(3))
    bits.extend(bin(length)[2:].zfill(5))
    return bits.tobytes()


