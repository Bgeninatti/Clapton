import binascii
import struct
import sys
import time

from . import cfg, decode, encode
from .exceptions import ChecksumException, InvalidPackage
from .utils import get_logger

logger = get_logger('containers')

class Package(object):
    """
    This class represent a TKLan package.
    Is useful for send packages and parse the received information from
    another node.
    """

    def __init__(self,
                 bytes_chain=b'',
                 sender=0,
                 destination=None,
                 function=None,
                 data=b'',
                 validate=True):
        """
        This class could be initialized in two ways:
            1. Make a package to be sended into the TKLan.
            2. Validate a package received for another node.

        One case or another differ in the parametters used to initalize
        the class.

        :param bytes_chain: Used in case that you want validate a package recieved.
            Is the bytes chain readed from the TKLan that we don't know if is a valid
            package yet.
        :type bytes_chain: bytes
        :param sender: Is te direction (or ``lan_dir`` in TKLan terminology) of the sender
            in the package. The default value is `0`, wich is the `lan_dir` of the Raspberry Pi node. The range is [0-15]
        :type sender: int
        :param destination: Is the direction of the reciver node. The range is [0-15]
        :type destination: int
        :param function: The that you want to use in the package. The range is [0-7]
        :type function: int
        :param data: The data that you want to send in the package. The format of this parametter depends on the function
            that you want to send. For more information please refer to the TKLan 2.0 documentation.
        :type data: bytes

        raises:
            * DecodeError: Raised if ``bytes_chain`` length is lower than 3, wich means that the package is incomplete and some of the decoders (`decode.sender_destination` or `decode.function_length`) will fail.
            * ChecksumException: Raised if ``bytes_chain`` didn't include a valid checksume in the last byte.
            * AttributeError: Raised if there's no enogh parametters to build a valid packages. If ``bytes_chain`` is not present and one of the other 3 required parametters (``sender``, ``destination`` or ``function``) is absent too theres no way to build a package.
            * EncodeError: If any of the arguments ``sender``, ``destination`` or ``function`` don't acomplish the requirements of the TKLan protocol.
        """
        # TODO: Reference the sentence "TKLan protocol" to a link with the TKLan docs
        self._bytes = bytes_chain
        self.hexlified = binascii.hexlify(self._bytes).decode()
        if self._bytes:
            if decode.validate_checksum(self._bytes):
                self.checksum = self._bytes[len(self._bytes)-1:len(self._bytes)]
            else:
                raise ChecksumException()
            self.sender, self.destination = decode.sender_destination(self._bytes[0:1])
            self.function, self.length = decode.function_length(self._bytes[1:2])
            self.data = self._bytes[2:-1]
        elif sender is not None and \
                destination is not None and \
                function is not None:
            self.sender = sender
            self.destination = destination
            self.function = function
            self.data = data
            self.length = len(self.data)
            self.checksum = None
            self._bytes = self._make_byte_chain()
            if validate:
                self.validate()
        else:
            raise AttributeError(
                "Not enough parametters to build a package.")

    def __bytes__(self):
        return self._bytes

    def _make_byte_chain(self):
        first_byte = encode.sender_destination(self.sender, self.destination)
        second_byte = encode.function_length(self.function, self.length)
        self.checksum = encode.make_checksum(first_byte + second_byte + self.data)
        return first_byte + second_byte + self.data + self.checksum

    def to_dict(self):
        return {
            'sender': self.sender,
            'destination': self.destination,
            'function': self.function,
            'length': self.length,
            'data': binascii.hexlify(self.data).decode(),
            'checksum': binascii.hexlify(self.checksum).decode()
        }

    def validate(self):
        if self.function == 7 and len(self.data):
            raise InvalidPackage('No se reconoce la funcion')
        elif self.function == 0 and len(self.data):
            raise InvalidPackage(
                'La funcion 0 siempre tiene que tener longitud de datos 0.')
        elif self.function in cfg.READ_FUNCTIONS and len(self.data) != 2:
            raise InvalidPackage(
                'Las funciones de lectura de memoria siempre tienen que tener'
                ' longitud de datos 2.')
        elif self.function in cfg.WRITE_FUNCTIONS and len(self.data) <= 1:
            raise InvalidPackage(
                'Las funciones de escritura de memoria siempre tienen que '
                'tener longitud de datos mayor a 1.')
        elif self.function == 5 and len(self.data) != 3:
            # El paquete de funcion 5 tiene que tener longitud 3 siempre. Dos
            # bytes indicando el inicio (una palabra) y un byte indicando la
            # longitud.
            raise InvalidPackage(
                'La funcion de lectura de aplicacion siempre tiene que tener '
                'longitud de datos 3.')
        elif self.function == 6 and len(self.data) < 2:
            raise InvalidPackage(
                'Las funciones de escritura de aplicacion siempre tienen que '
                'tener longitud de datos mayor a 1.')
