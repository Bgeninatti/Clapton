import binascii
import struct
import sys
import time

from . import decode, encode
from .cfg import (APP_LINE_SIZE, COMMAND_SEPARATOR, DEFAULT_BUFFER,
                  DEFAULT_EEPROM, DEFAULT_RAM_READ, DEFAULT_RAM_WRITE,
                  MEMO_READ_NAMES, MEMO_WRITE_NAMES, READ_FUNCTIONS,
                  WRITE_FUNCTIONS)
from .exceptions import (ChecksumException, InvalidPackage,
                         NodeNotExists, WriteException)
from .utils import get_logger

logger = get_logger('containers')

class Package(object):
    """
    This class represent a TKLan package.
    Is useful for send packages and parse the received information from
    another node.
    """

    def __init__(self,
                 bytes_chain=None,
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
        if bytes_chain is not None:
            if decode.validate_checksum(bytes_chain):
                self.checksum = bytes_chain[len(bytes_chain)-1:len(bytes_chain)]
            else:
                raise ChecksumException
            self.bytes_chain = bytes_chain
            self.sender, self.destination = decode.sender_destination(bytes_chain[0:1])
            self.function, self.length = decode.function_length(bytes_chain[1:2])
            self.data = bytes_chain[2:-1]
        elif sender is not None and \
                destination is not None and \
                function is not None:
            self.sender = sender
            self.destination = destination
            self.function = function
            self.data = data
            self.length = len(self.data)
            self.checksum = None
            self.bytes_chain = self._make_byte_chain()
            if validate:
                self.validate()
        else:
            raise AttributeError("Not enough parametters to build a package.")
        self.hexlified = binascii.hexlify(self.bytes_chain).decode()

    def _make_byte_chain(self):
        first_byte = encode.sender_destination(self.sender, self.destination)
        second_byte = encode.function_length(self.function, self.length)
        self.checksum = encode.make_checksum(first_byte + second_byte + self.data)
        return first_byte + second_byte + self.data + self.checksum

    def validate(self):
        if self.function == 7 and len(self.data):
            raise InvalidPackage('No se reconoce la funcion')
        elif self.function == 0 and len(self.data):
            raise InvalidPackage(
                'La funcion 0 siempre tiene que tener longitud de datos 0.')
        elif self.function in READ_FUNCTIONS and len(self.data) != 2:
            raise InvalidPackage(
                'Las funciones de lectura de memoria siempre tienen que tener'
                ' longitud de datos 2.')
        elif self.function in WRITE_FUNCTIONS and len(self.data) <= 1:
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

    def get_rta_size(self):
        """
        Calcula tamanio de la respuesta segun la funcion del paquete
        Llegada a esta instancia la funcion ya fue validad y se asegura que
        esta no es mayor a 8, sin embargo excepcion de InvalidPackage se
        establece igual
        """
        rta_size = None
        if self.function == 0:
            rta_size = 13
        elif self.function in READ_FUNCTIONS:
            _, length = struct.unpack('2B', self.data)
            rta_size = 3 + length
        elif self.function in WRITE_FUNCTIONS:
            rta_size = 3 + self.length
        elif self.function == 5:
            start, length = struct.unpack('Hb', self.data)
            rta_size = length*2 + 3
        elif self.function == 6:
            if self.data == b'\x00\x00\xa5\x05':
                rta_size = 4
            # el dos es por la direccion y el 3 por el resto del paquete.
            rta_size = APP_LINE_SIZE + 2 + 3
        else:
            rta_size = 3
        return rta_size


class MemoryContainer(object):
    """
    This class contains an amount of bytes in some memory instance of a node
    (`RAM` or `EEPROM`) at a moment in time.
    The bytes in an instance of this class guarantee consistency, wich means
    that all that values coexist at the same time in the memory.
    """
        # TODO: Reference the sentence "TKLan protocol" to a link with the TKLan docs

    def __init__(self, node, instance, start, timestamp=None, data=b''):
        """
        :param node: The node how belongs the memory.
        :type node: math:0 `\leqslant int \geqslant 15`
        :param instance: the instance of the memory defined by
        ``MEMO_READ_NAMES`` config parametters. Default: ('RAM', 'EEPROM')
        :param start: The index in the memory of the first byte in ``data``
        :type start: int
        :param timestamp: Reference timestamp of when the memory was read.
        :type timestamp: float
        :param data: Bytes reader from the memory ``instance`` of the ``node``
            at ``timestamp`` time.
        :type data: bytes

        raises:
            * AttributeError when ``node`` don't acomplish the requirements
            of the TKLan protocol or when `instance not in cfg.MEMO_READ_NAMES`.
        """
        # contenedor dummy de atributos. Los datos no son requeridos para
        # podera armar la memoria de a dos paquetes cuando no soy master.
        if node > 15 or node < 0:
            raise AttributeError
        if instance not in MEMO_READ_NAMES.keys():
            raise AttributeError
        if not isinstance(data, bytes):
            raise AttributeError

        self.timestamp = timestamp
        self.node = node
        self.instance = instance
        self.start = start
        self.data = data
        self.length = len(self.data)

    def as_msg(self):
        """
        Format the message data as will be sended through ZMQ.
        """
        return '{1}_{2}_{3}{0}{4}{0}{5}'.format(
            COMMAND_SEPARATOR,
            self.node,
            self.instance,
            self.start,
            self.timestamp,
            binascii.hexlify(self.data).decode())

    def get(self, index, default_value=None):
        """
        returns the bytes corresonding to the given ``index`` or ``default_value``
        if the index doesn't corresponde with this memory instnace`
        """
        if index < self.start or index > self.start + self.length:
            return default_value
        return self.data[index-self.start:index-self.start+1]


class Node(object):
    """
    Representation of a Node in the TKLan network.
    """


    def __init__(self,
                 lan_dir,
                 ser,
                 is_master=False):
        """
            :param lan_dir: Direction of the node in the TKLan network. This
                will be used a ``sender`` or ``destination`` in the packages.
            :type lan_dir: mat:`\leqslant int \geqslant`
            :param ser: instance of a ``SerialInterface`` object
            :type ser: SerialInterface instance
            :param is_master: Flag that indicate where this node is master or not.
            :type is_master: bool

        raises:
            * AttributeError when ``node`` don't acomplish the requirements
                of the TKLan protocol or when `instance not in cfg.MEMO_READ_NAMES`.
        """

        if not isinstance(lan_dir, int) or lan_dir > 15 or lan_dir < 0:
            raise AttributeError("The node lan_dir should  be between 0 and 15")

        # Guardo la instancia del puerto serie.
        self._ser = ser
        # Guardo direccion. Tiene que ser un int. Si no lo tiro.
        self.lan_dir = int(lan_dir)
        logger.info("Iniciando nodo {}.".format(self.lan_dir))
        # Si nunca lo vi el timestamp no existe.
        self.last_seen = None
        """
        """
        self._status = 0
        self.is_master = is_master  # Rol del esclavo.

        # Inicio con sizes estandar para poder usar hasta que el nodo sea
        # identificado.
        self.buffer_size = DEFAULT_BUFFER
        self.eeprom_size = DEFAULT_EEPROM
        self.ram_read_size = DEFAULT_RAM_READ
        self.ram_write_size = DEFAULT_RAM_WRITE

    @property
    def status(self):
        # TODO: A status should be a instance of the class Status.
        """
        The status of the node, could be:
            * 0: Never seen.
            * 1: OK.
            * 2: Quarantine. Don't see it in a while. Used only when
            `node 0` is slave. Because he can't ask the node if exist,
            so he has to wait until the master ask something to the
            node in qquarantine and he response.
            * 3: Don't exist.
        """
        return self._status

    @status.setter
    def status(self, value):
        """
        :param value: int
        :raises:
          * TypeError: if ``value`` is not int si el estado no es int
        """
        if not isinstance(value, int):
            raise TypeError
        # Actualizo el estado y renuevo timestamp si el estado es 1.
        logger.debug(
            "Estado del nodo {}.".format(self.lan_dir))
        self._status = value
        if value == 1:
            self.last_seen = time.time()

    def _get_package_zero(self):
        ask_package_zero = Package(destination=self.lan_dir, function=0)
        package_zero = self._ser.send_package(ask_package_zero)
        return package_zero

    def _get_buffer_size(self, package_zero=b''):
        required_byte = package_zero.data[5:6]
        if required_byte:
            buffer = struct.unpack('b', required_byte)[0] * 64
        else:
            buffer = DEFAULT_BUFFER
        return buffer

    def _get_ram_read_size(self, package_zero=b''):
        required_byte = package_zero.data[7:8]
        if required_byte:
            ram_read = struct.unpack('b', required_byte)[0] * 64
        else:
            ram_read = DEFAULT_RAM_READ
        return ram_read

    def _get_ram_write_size(self, package_zero):
        required_byte = package_zero.data[6:7]
        if required_byte:
            ram_write = struct.unpack('b', required_byte)[0] * 64
        else:
            ram_write = DEFAULT_RAM_WRITE
        return ram_write

    def _get_eeprom_size(self, package_zero):
        required_byte = package_zero.data[2:3]
        if required_byte:
            eeprom_size = struct.unpack('b', required_byte)[0] * 64
        else:
            eeprom_size = DEFAULT_EEPROM
        return eeprom_size

    def identify(self, package_zero=None):
        """
        :param package_zero: Answer of the node to the identification packages,
        following the TKLan protocol. If the value is None the function will
        send the package zero to the node to get the answer
        :type package: Package instance

        raises:
          * AttributeError: If ``package_zero`` is not an instance of Package,
            or is an instance of Package but doesn't correspod with the packages
            zero.
          * NodeNotExists: If theres no answer to package zero, wich means
            that the node don't exist and the status is 3.
        """

        logger.info("Identificando nodo {}.".format(self.lan_dir))
        try:
            if not package_zero:
                package_zero = self._get_package_zero()
            elif package_zero.function != 0 or len(package_zero.data) < 8:
                logger.error("package_zero is not a valid instance of a package zero")
                raise AttributeError("package_zero is not a valid instance of a package zero")
            self.eeprom_size = self._get_eeprom_size(package_zero)
            self.buffer_size = self._get_buffer_size(package_zero)
            self.ram_write_size = self._get_ram_write_size(package_zero)
            self.ram_read_size = self._get_ram_read_size(package_zero)
            self.status = 1
        except WriteException as e:
            logger.error("El nodo {} no existe.".format(self.lan_dir))
            self.status = 3
            raise NodeNotExists

    def read_ram(self, start, length):
        """
        Read the ram of the node.

        :param start: Index of the first byte to read
        :type start: int
        :param length: Longitude of the bytes to read
        :type length: int

        Raises AttributeError if:
            * The start parametter is lower than 0 or bigger than the maximum
                index of the RAM to read (see `self._get_ram_read_size`)
            * The length parametter is lower than 0 or bigger than the buffer size
                (see `self._get_buffer_size`)
        """
        if start < 0 or start > self.ram_read_size:
            raise AttributeError("The start index is out of range (max %s)", self.read_ram)
        if length < 0 or length > self.buffer_size:
            raise AttributeError("The length to read is out of range (max buffer %s)", self.buffer_size)
        return self._read_memo(start, length, instance='RAM')

    def write_ram(self, start, data):
        """
        Write the ram of the node.

        :param start: Index of the first byte to write
        :type start: int
        :param data: Data to write in the memory from ``start``
        :type length: bytes

        Raises AttributeError if:
            * The ``start`` parametter is lower than 0 or bigger than the maximum
                index of the RAM to write (see `self._get_ram_write_size`)
            * The ``data`` parametter is lower than 0 or bigger than the buffer
                size minus 1 because of the start byte (see `self._get_buffer_size`)
        """
        if start < 0 or start > self.ram_write_size:
            raise AttributeError("The start index is out of range (max %s)", self.write_ram)
        if len(data) > self.buffer_size - 1:
            raise AttributeError("The length of the data to write is out of range (max buffer %s)", self.buffer_size)
        return self._write_memo(start, data, instance='RAM')

    def read_eeprom(self, start, length):
        """
        Read the eeprom of the node.

        :param start: Index of the first byte to read
        :type start: int
        :param length: Longitude of the bytes to read
        :type length: int

        Raises AttributeError if:
            * The start parametter is lower than 0 or bigger than the maximum
                index of the EEPROM (see `self._get_eeprom_size`)
            * The length parametter is lower than 0 or bigger than the buffer size
                (see `self._get_eeprom_size`)
        """
        if start < 0 or start > self.eeprom_size:
            raise AttributeError("The start index is out of range (max %s)", self.eeprom_size)
        if length < 0 or length > self.buffer_size:
            raise AttributeError("The length to read is out of range (max buffer %s)", self.buffer_size)
        return self._read_memo(start, length, instance='EEPROM')

    def write_eeprom(self, start, data):
        """
        Write the eeprom of the node.

        :param start: Index of the first byte to write
        :type start: int
        :param data: Data to write in the memory from ``start``
        :type length: bytes

        Raises AttributeError if:
            * The ``start`` parametter is lower than 0 or bigger than the maximum
                index of the RAM to write (see `self._get_eeprom_size`)
            * The ``data`` parametter is lower than 0 or bigger than the buffer
                size minus 1 because of the start byte (see `self._get_buffer_size`)
        """
        if start < 0 or start > self.eeprom_size:
            raise AttributeError("The start index is out of range (max %s)", self.eeprom_size)
        if len(data) > self.buffer_size - 1:
            raise AttributeError("The length of the data to write is out of range (max buffer %s)", self.buffer_size)
        return self._write_memo(start, data, instance='EEPROM')

    def _make_streaming_packages(self, indexes, instance):
        """Really don't know what is this for"""
        # TODO: What is this function for?
        end = -1
        packages = list()
        for i in sorted(indexes):
            if i > end:
                end = min(indexes, key=lambda x:i+self.buffer_size-x if x < i+self.buffer else sys.maxsize)
                packages.append(Package(destination=self.lan_dir,
                                        function=MEMO_READ_NAMES[instance],
                                        data=struct.pack('2b', i, end-i+1)))
        return packages

    def _read_memo(self, start, length, instance):
        """
        Read some memory instance from the node.

        :param start: Index of the first byte to read
        :type start: int
        :param length: Longitude of the bytes to read
        :type length: int
        :param instance: Instance of the memory to read
        :atype instance: str

        :return: MemoryContainer instance

        :raises:
          * KeyError: When `instance not in cfg.MEMO_READ_NAMES`
          * AttributeError: If is not possible build a package with the
            ``start`` and ``length`` following the TKLan protocol
        """

        logger.debug("Leyendo memoria del nodo {}.".format(self.lan_dir))
        try:
            read_package = Package(destination=self.lan_dir,
                                   function=MEMO_READ_NAMES[instance],
                                   data=struct.pack('2B', start, length))
        except struct.error as e:
            raise AttributeError

        rta = self._ser.send_package(read_package)
        return MemoryContainer(node=rta.sender,
                            instance=instance,
                            start=start,
                            timestamp=time.time(),
                            data=rta.data)

    def _write_memo(self, start, data, instance):
        """
        Read some memory instance from the node.

        :param start: Index of the first byte to write
        :type start: int
        :param data: Data to write in the memory from ``start``
        :type data: bytes
        :param instance: Instance of the memory to write
        :atype instance: str

        :raises:
          * KeyError: When `instance not in cfg.MEMO_READ_NAMES`
          * AttributeError: If is not possible build a package with the
            ``start`` and ``data`` following the TKLan protocol
        """

        logger.info("Escribiendo datos {0} en nodo {1}.".format(binascii.hexlify(data),
                                                                self.lan_dir))
        try:
            writed_package = Package(destination=self.lan_dir,
                                     function=MEMO_WRITE_NAMES[instance],
                                     data=struct.pack('B', start) + data)
        except struct.error:
            raise AttributeError
        answer_package = self._ser.send_package(writed_package)
        return writed_package, answer_package

    def __dict__(self):
        return {
            'lan_dir': self.lan_dir,
            'status': self.status,
            'buffer': self.buffer_size,
            'ram_read': self.ram_read_size,
            'ram_write': self.ram_write_size,
            'eeprom_size': self.eeprom_size,
            'is_master': self.is_master,
            'time': time.time(),
        }
