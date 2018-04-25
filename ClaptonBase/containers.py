import binascii
import struct
import sys
import time

from . import decode, encode
from .cfg import (APP_LINE_SIZE, COMMAND_SEPARATOR, DEFAULT_BUFFER,
                  DEFAULT_EEPROM, DEFAULT_RAM_READ, DEFAULT_RAM_WRITE,
                  MEMO_READ_NAMES, MEMO_WRITE_NAMES, READ_FUNCTIONS,
                  WRITE_FUNCTIONS)
from .exceptions import (ChecksumException, EncodeError, InvalidPackage,
                         NodeNotExists, ReadException, TokenExeption,
                         WriteException)
from .utils import get_logger


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
                 data=b''):
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
        :type: int
        :param destination: Is the direction of the reciver node. The range is [0-15]
        :type: int
        :param function: The that you want to use in the package. The range is [0-7]
        :type: int
        :param data: The data that you want to send in the package. The format of this parametter depends on the function
            that you want to send. For more information please refer to the TKLan 2.0 documentation.
        :type: bytes

        raises:
            EncodeError
            ChecksumException
            AttributeError
            InvalidPackage
        """
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
                function is not None and \
                data is not None:
            self.sender = sender
            self.destination = destination
            self.function = function
            self.data = data
            self.length = len(self.data)
            self.checksum = None
            self.bytes_chain = self._make_byte_chain()
        else:
            raise AttributeError
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


class MemoInstance(object):
    """
    This class contains an amount of bytes in some memory instance of a node (`RAM` or `EEPROM`) at a moment in time.
    The bytes in an instance of this class guarantee consistency, wich means that all that values
    coexist at the same time in the memory.

    """
    def __init__(self, node, instance, start, timestamp=None, data=b''):
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
        return '{1}_{2}_{3}{0}{4}{0}{5}'.format(
            COMMAND_SEPARATOR,
            self.node,
            self.instance,
            self.start,
            self.timestamp,
            binascii.hexlify(self.data).decode())

    def get(self, index, default_value=None):
        if index < self.start or index > self.start + self.length:
            return default_value
        return self.data[index-self.start:index-self.start+1]


class Node(object):

    def __init__(self,
                 lan_dir,
                 ser,
                 is_master=False,
                 log_level=None,
                 log_file=None):
        if not isinstance(lan_dir, int) or lan_dir > 15 or lan_dir < 0:
            raise TypeError

        # Inicio logger
        self._logger = get_logger(__name__, log_level, log_file)
        # Guardo la instancia del puerto serie.
        self._ser = ser
        # Guardo direccion. Tiene que ser un int. Si no lo tiro.
        self.lan_dir = int(lan_dir)
        self._logger.info("Iniciando nodo {}.".format(self.lan_dir))
        # Si nunca lo vi el timestamp no existe.
        self.last_seen = None
        """
            status 0: Nunca visto.
            status 1: OK.
            status 2: Dudoso.
            status 3: No existe.
        """
        self._status = 0
        self.is_master = is_master  # Rol del esclavo.

        # Inicio con sizes estandar para poder usar hasta que el nodo sea
        # identificado.
        self.buffer = DEFAULT_BUFFER
        self.eeprom_size = DEFAULT_EEPROM
        self.ram_read = DEFAULT_RAM_READ
        self.ram_write = DEFAULT_RAM_WRITE

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        """
        :param value: int
        :raise:
          TypeError: si el estado no es int
        """
        if not isinstance(value, int):
            raise TypeError
        # Actualizo el estado y renuevo timestamp si el estado es 1.
        self._logger.debug(
            "Estado del nodo {}.".format(self.lan_dir))
        self._status = value
        if value == 1:
            self.last_seen = time.time()

    def identify(self, rta_bytes_chain=None):
        """
        :param rta: Una instancia de Paquete con la respuesta de la funcion 0
        :return: None
          AttributeError: Si rta no es None y no es una instancia de paquete o
            no corresponde a una respuesta de la función 0
          NodeNotExists: Si no se recibio respuesta del nodo
          ChecksumException: Si el paquete de identificacion no es válido. Ya sea
            porque su función no es 0 o porque la longitud de losd atos es
            insuficiente para obtener la información que se requiere
        """

        self._logger.info("Identificando nodo {}.".format(self.lan_dir))
        status = self.status
        try:
            if not rta_bytes_chain:
                package = Package(destination=self.lan_dir, function=0)
                rta = self._ser.send_package(package)
            else:
                rta = Package(bytes_chain=rta_bytes_chain)
            if rta.function != 0 or len(rta.data) < 8:
                self._logger.error("El paquete no contiene toda la información para la identificación del nodo")
                raise InvalidPackage("No es un paquete de identificación válido")
            self.eeprom_size = struct.unpack('b', rta.data[2:3])[0] * 64
            self.buffer = struct.unpack('b', rta.data[5:6])[0]
            self.ram_write = struct.unpack('b', rta.data[6:7])[0]
            self.ram_read = struct.unpack('b', rta.data[7:8])[0]
            status = 1
        except WriteException as e:
            if self._ser.im_master:
                self._logger.error("El nodo {} no existe.".format(self.lan_dir))
                status = 3
                raise NodeNotExists
        finally:
            self.status = status

    def read_ram(self, start, length):
        return self._read_memo(start, length, instance='RAM')

    def write_ram(self, start, data):
        return self._write_memo(start, data, instance='RAM')

    def read_eeprom(self, start, length):
        return self._read_memo(start, length, instance='EEPROM')

    def write_eeprom(self, start, data):
        return self._write_memo(start, data, instance='EEPROM')

    def _make_streaming_packages(self, indexes, instance):
        end = -1
        packages = list()
        for i in sorted(indexes):
            if i > end:
                end = min(indexes, key=lambda x:i+self.buffer-x if x < i+self.buffer else sys.maxsize)
                packages.append(Package(destination=self.lan_dir,
                                        function=MEMO_READ_NAMES[instance],
                                        data=struct.pack('2b', i, end-i+1)))
        return packages

    def _read_memo(self, start, length, instance):
        """

        :param inicio: int que indica el indice de incio de memoria que se
        quiere leer
        :param longitud: int que indica la longitud en bytes que se quiere leer
        :param instance: str que indica la instancia de la memoria que se
        quiere leer (RAM o EEPROM)
        :return: Lista de memo_instances para cada uno de los valores leidos
        :raise:
          KeyError: Si ``instance`` no es ni `RAM` ni `EEPROM`
          InvalidPackage: Si ``start`` o ``length`` son mayores a 255
        """

        self._logger.debug("Leyendo memoria del nodo {}.".format(self.lan_dir))
        try:
            read_package = Package(destination=self.lan_dir,
                                   function=MEMO_READ_NAMES[instance],
                                   data=struct.pack('2B', start, length))
        except struct.error as e:
            raise InvalidPackage

        rta = self._ser.send_package(read_package)
        return MemoInstance(node=rta.sender,
                            instance=instance,
                            start=start,
                            timestamp=time.time(),
                            data=rta.data)

    def _write_memo(self, start, data, instance):
        """
        :param inicio: int Indice indicando a partir de que registro de la
        memoria se quiere escribir
        :param datos: str datos que se quieren escribir en hexadecimal
        :param instance: str que indica la instancia de la memoria que se
        quiere escribir (RAM o EEPROM)
        :return: None
        :raise:
          InvalidPackage: Si ``start`` es mayor de 255
          KeyError: Si ``instance`` no hace referencia a `RAM` o `EEPROM`
          TypeError: Si ``data`` no es de tipo bytes
        """

        self._logger.info(
            "Escribiendo datos {0} en nodo {1}.".format(
                binascii.hexlify(data), self.lan_dir))
        try:
            writed_package = Package(destination=self.lan_dir,
                                     function=MEMO_WRITE_NAMES[instance],
                                     data=struct.pack('B', start) + data)
        except struct.error:
            raise InvalidPackage
        answer_package = self._ser.send_package(writed_package)
        return writed_package, answer_package

    def __dir__(self):
        return {
            'lan_dir': self.lan_dir,
            'status': self.status,
            'buffer': self.buffer,
            'ram_read': self.ram_read,
            'ram_write': self.ram_write,
            'eeprom_size': self.eeprom_size,
            'is_master': self.is_master,
            'time': time.time(),
        }
