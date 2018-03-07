import struct
import math
import time
import json
import binascii
import sys
from threading import Event, Lock

from .cfg import *
from .consts import (LINE_REGEX, READ_FUNCTIONS, END_LINE, MEMO_NAMES,
                     APP_ACTIVATE_RESPONSE, APP_DEACTIVATE_RESPONSE,
                     WRITE_FUNCTIONS, MEMO_WRITE_NAMES, MEMO_READ_NAMES)
from . import encode, decode
from .exceptions import ChecksumException, WriteException, ReadException, \
    TokenExeption, NodeNotExists, InactiveAppException, ActiveAppException, \
    PaqException, BadLineException, DecodeError
from .utils import get_logger


class AppLine(object):

    def __init__(self, **kwargs):
        line = kwargs.get('line', None)
        paq = kwargs.get('paq', None)
        inicio = kwargs.get('inicio', None)
        if line is not None:
            line = LINE_REGEX.search(line)
            if line is not None:
                line_parsed = line.groups()
            else:
                raise BadLineException
            if decode.validate_cs(binascii.unhexlify(''.join(line_parsed))):
                try:
                    self.longitud = struct.unpack(
                        'b', binascii.unhexlify(line_parsed[0]))[0]
                    self.inicio = int(struct.unpack(
                        'H', binascii.unhexlify(
                            line_parsed[2] + line_parsed[1]))[0]/2)
                    self.comando = line_parsed[3]
                    datos = binascii.unhexlify(line_parsed[4])
                    self.datos = datos[:-1]
                    self.cs = datos[-1:]
                except (struct.error, TypeError) as e:
                    raise BadLineException
            else:
                raise BadLineException
        elif (paq is not None) and (inicio is not None):
            self.longitud = int(paq.longitud/2)
            self.inicio = inicio
            self.datos = paq.datos
            self.comando = '00'

    def get_1b_data(self):
        dir_inicio = struct.pack('H', self.inicio)
        return dir_inicio + ''.join(
            [self.datos[i] for i in range(len(self.datos)) if i % 2])

    def to_write(self):
        longitud = binascii.hexlify(struct.pack('b', self.longitud)).decode()
        pre_inicio = binascii.hexlify(struct.pack('H', self.inicio*2))
        inicio = pre_inicio[2:4].decode() + pre_inicio[0:2].decode()
        datos = binascii.hexlify(self.datos).decode()
        pre_line = '{0}{1}{2}{3}'.format(longitud, inicio, self.comando, datos)
        cs = binascii.hexlify(encode.checksum(
            binascii.unhexlify(pre_line))).decode()
        return ':{0}{1}'.format(pre_line, cs).upper()


class Paquete(object):

    def __init__(self,
                 paq=None,
                 origen=0,
                 destino=None,
                 funcion=None,
                 datos=None):
        # Se puede enviar un paquete como cadena de bytes para decodificarlo o
        # indicar los parametros para codificar el paquete como cadena de
        # bytes. Esto permite usar la misma instancia para interpretar las
        # lecturas como codificar las escrituras.
        #
        # Paquete como cadena de bytes
        """
        raise:
            EncodeError
            ChecksumException
            AttributeError
            PaqException
        """
        if paq is not None:
            # Verifico el checksum del paquete.
            if decode.validate_cs(paq):
                self.cs = paq[len(paq)-1:len(paq)]
            else:
                raise ChecksumException
            # Decodifico las variables
            self.to_write = paq
            self.origen, self.destino = decode.fuen_des(paq[0:1])
            self.funcion, self.longitud = decode.fun_lon(paq[1:2])
            self.datos = paq[2:-1]
        # Paquete como parametros
        elif origen is not None and destino is not None and funcion is not None:
            self.origen = origen
            self.destino = destino
            self.funcion = funcion
            self.datos = datos if datos is not None else b''
            self.longitud = len(self.datos)
            self.cs = None
            # Creo cadena de bytes.
            self.to_write = self._make_paq()
            self._validate()
            self.rta_size = self._get_rta_size()
        # Ninguna de las dos. Devuelvo un error.
        else:
            raise AttributeError
        self.representation = self._make_representation()

    def _make_paq(self):
        # Creo cabecera
        b1 = encode.fuen_des(self.origen, self.destino)
        # Creo funcion y longitud
        b2 = encode.fun_lon(self.funcion, self.longitud)
        # Guardo el checksum
        self.cs = encode.checksum(b1 + b2 + self.datos)
        # Lo junto y lo mando.
        return b1 + b2 + self.datos + self.cs

    def _make_representation(self):
        return binascii.hexlify(self.to_write).decode()

    def _validate(self):
        if self.funcion == 7:
            raise PaqException('No se reconoce la funcion')
        elif self.funcion == 0 and len(self.datos):
            # La funcion 0 siempre tiene que tener longitud de datos 0
            raise PaqException(
                'La funcion 0 siempre tiene que tener longitud de datos 0.')
        elif self.funcion in READ_FUNCTIONS and len(self.datos) != 2:
            # Las funciones en READ_FUNCTIONS siempre tienen que tener longitud
            # de datos 2
            raise PaqException(
                'Las funciones de lectura de memoria siempre tienen que tener'
                ' longitud de datos 2.')
        elif self.funcion in WRITE_FUNCTIONS and len(self.datos) <= 1:
            # Las funciones en WRITE_FUNCTIONS siempre tienen que tener
            # longitud de datos mayor a 1.
            raise PaqException(
                'Las funciones de escritura de memoria siempre tienen que '
                'tener longitud de datos mayor a 1.')
        elif self.funcion == 5 and len(self.datos) != 3:
            # El paquete de funcion 5 tiene que tener longitud 3 siempre. Dos
            # bytes indicando el inicio (una palabra) y un byte indicando la
            # longitud.
            raise PaqException(
                'La funcion de lectura de aplicacion siempre tiene que tener '
                'longitud de datos 3.')
        elif self.funcion == 6 and len(self.datos) < 2:
            raise PaqException(
                'Las funciones de escritura de aplicacion siempre tienen que '
                'tener longitud de datos mayor a 1.')

    def _get_rta_size(self):
        """
        Calcula tamanio de la respuesta segun la funcion del paquete
        Llegada a esta instancia la funcion ya fue validad y se asegura que
        esta no es mayor a 8, sin embargo excepcion de PaqException se
        establece igual
        """
        if self.funcion == 0:
            return 13
        elif self.funcion in READ_FUNCTIONS:
            inicio, longitud = struct.unpack('2b', self.datos)
            return 3 + longitud
        elif self.funcion == 2:
            return 3
        elif self.funcion == 4:
            return 3 + self.longitud
        elif self.funcion == 5:
            inicio, longitud = struct.unpack('Hb', self.datos)
            return longitud*2 + 3
        elif self.funcion == 6:
            if self.datos == b'\x00\x00\xa5\x05':
                return 4
            else:
                # el dos es por la direccion y el 3 por el resto del paquete.
                return APP_LINE_SIZE + 2 + 3
        elif self.funcion == 7:
            return 3
        else:
            PaqException('No se reconoce la funcion')


class MemoInstance(object):

    def __init__(self, nodo, tipo, inicio, timestamp=None, valores=b''):
        # contenedor dummy de atributos. Los datos no son requeridos para
        # podera armar la memoria de a dos paquetes cuando no soy master.
        self.timestamp = timestamp
        self.nodo = nodo
        self.tipo = tipo
        self.inicio = inicio
        self.valores = valores
        self.longitud = len(self.valores)
        self.representation = self._make_representation()

    def _make_representation(self):
        return '{1}_{2}_{3}{0}{4}{0}{5}'.format(
            COMMAND_SEPARATOR,
            self.nodo,
            self.tipo,
            self.inicio,
            self.timestamp,
            binascii.hexlify(self.valores))

    def get(self, index):
        if index < self.inicio or index > self.inicio + self.longitud:
            raise IndexError
        return self.valores[index-self.inicio:index-self.inicio+1]


class Node(object):

    def __init__(self,
                 lan_dir,
                 ser,
                 is_master=False,
                 required=DEFAULT_REQUIRED_NODE,
                 required_ram=DEFAULT_REQUIRED_RAM,
                 required_eeprom=DEFAULT_REQUIRED_EEPROM,
                 required_ram_index=list(),
                 required_eeprom_index=list(),
                 log_level=None,
                 log_file=None):
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
        self.im_master = is_master  # Rol del esclavo.
        self.aplicacion_activa = True
        self.solicitud_desactivacion = False

        self.eeprom = {}
        self.eeprom_lock = Lock()
        self.ram = {}
        self.ram_lock = Lock()

        # Bandera de uso interno para que no haya colicion en la actualizacion
        # de los datos del master.
        self._can_update = Event()
        self._can_update.set()

        # Inicio con sizes estandar para poder usar hasta que el nodo sea
        # identificado.
        self.buffer = DEFAULT_BUFFER
        self.eeprom_size = DEFAULT_EEPROM
        self.initapp = None
        self.fnapp = None
        self.ram_read = DEFAULT_RAM_READ
        self.ram_write = DEFAULT_RAM_WRITE

        # Banderas de lectura del nodo.
        self._enabled_read_node = required
        self._enabled_read_ram = required_ram
        self._enabled_read_eeprom = required_eeprom
        self.index_disabled_ram = set()
        self.index_disabled_eeprom = set()
        self.to_read_ram = list()
        self.to_read_eeprom = list()

        # Estos son los parametros requeridos de lectura para que la aplicacion
        # funcione. Se dara warning cuando se quiera desactivarlos.
        self.required = required
        self.required_ram = required_ram
        self.required_eeprom = required_eeprom
        self.required_ram_index = required_ram_index
        self.required_eeprom_index = required_eeprom_index

        self.enabled_read_ram = bool(required_ram or len(required_ram_index))
        self.enabled_read_eeprom = bool(required_eeprom or len(required_eeprom_index))
        self.enabled_read_node = bool(required or self.enabled_read_ram or self.enabled_read_eeprom)
        self.enable_eeprom_sector(*required_eeprom_index)
        self.enable_ram_sector(*required_ram_index)

        # En donde se almacenaran los servicios leidos del pic
        self._servicios = {}

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
        self._can_update.wait()
        if self._can_update.isSet():
            # Actualizo el estado y renuevo timestamp si el estado es 1.
            self._can_update.clear()
            self._logger.debug(
                "Reportando estado del nodo {}.".format(self.lan_dir))
            self._status = value
            if value == 1:
                self.last_seen = time.time()
            self._can_update.set()

    @property
    def enabled_read_node(self):
        return self._enabled_read_node

    @enabled_read_node.setter
    def enabled_read_node(self, value):
        """
        :param value: int
        :raise:
          TypeError: si el valor no es bool
        """

        if self.required and not value:
            self._logger.warning(
                "El nodo {} es requerido y se esta desactivando su lectura".format(self.lan_dir))

        self._logger.info(
            "{0}ctivando lectura del nodo {1}.".format(
                ('A' if value else 'Desa'),
                self.lan_dir))

        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            self._enabled_read_node = value
            self._can_update.set()

    @property
    def enabled_read_ram(self):
        return self._enabled_read_ram

    @enabled_read_ram.setter
    def enabled_read_ram(self, value):
        """
        :param value: int
        :raise:
          TypeError: si el valor no es bool
        """
        if self.required_ram and not value:
            self._logger.warning(
                "La memoria ram del nodo {} es requerida y se esta " +
                "desactivando su lectura".format(self.lan_dir))

        self._logger.info(
            "{0}ctivando lectura de ram del nodo {1}.".format(
                ('A' if value else 'Desa'), self.lan_dir))

        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            self._enabled_read_ram = value
            self._can_update.set()

    @property
    def enabled_read_eeprom(self):
        return self._enabled_read_eeprom

    @enabled_read_eeprom.setter
    def enabled_read_eeprom(self, value):
        """
        :param value: int
        :raise:
          TypeError: si el valor no es bool
        """

        if self.required_eeprom and not value:
            self._logger.warning(
                "La eeprom del nodo {} es requerida y se esta desactivando "
                "su lectura".format(self.lan_dir))

        self._logger.info(
            "{0}ctivando lectura de eeprom del nodo {1}.".format(
                ('A' if value else 'Desa'), self.lan_dir))

        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            self._enabled_read_eeprom = value
            self._can_update.set()

    def disable_eeprom_sector(self, *args):
        """
        :param value: ints
        :raise:
          TypeError: si el valor no es int
        """

        if any([a in self.required_eeprom_index for a in args]):
            self._logger.warning(
                "Desactivando indices de eeprom del nodo {} indicados como " +
                "requeridos".format(self.lan_dir))
        self._logger.info(
            "Desactivando sectores de eeprom {0} del nodo {1}.".format(
                str(args), self.lan_dir))
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            for value in args:
                self.index_disabled_eeprom.add(value)
            self._can_update.set()
            self._update_to_read_eeprom()

    def enable_eeprom_sector(self, *args):
        """
        :param value: ints
        :raise:
          TypeError: si el valor no es int
        """
        self._logger.info(
            "Activando sectores de eeprom {0} del nodo {1}.".format(
                str(args), self.lan_dir))
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            for value in args:
                try:
                    self.index_disabled_eeprom.remove(value)
                except KeyError as e:
                    self._logger.warning("El indice {} de la eeprom ya estaba activo.".format(
                        value))
            self._can_update.set()
            self._update_to_read_eeprom()

    def disable_ram_sector(self, *args):
        """
        :param value: ints
        :raise:
          TypeError: si el valor no es int
        """
        if any([a in self.required_ram_index for a in args]):
            self._logger.warning(
                "Desactivando indices de ram del nodo {} indicados como " +
                "requeridos".format(self.lan_dir))
        self._logger.info(
            "Desactivando sectores de ram {0} del nodo {1}.".format(
                str(args), self.lan_dir))
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            for value in args:
                self.index_disabled_ram.add(value)
            self._can_update.set()
            self._update_to_read_ram()

    def enable_ram_sector(self, *args):
        """
        :param value: ints
        :raise:
          TypeError: si el valor no es int
        """

        self._logger.info(
            "Activando sectores de ram {0} del nodo {1}.".format(
                str(args), self.lan_dir))
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            for value in args:
                try:
                    self.index_disabled_ram.remove(value)
                except KeyError as e:
                    self._logger.warning(
                        "El indice {} de la ram ya estaba activo.".format(
                            value))
            self._can_update.set()
            self._update_to_read_ram()

    def identify(self, rta=None):
        """
        :param rta: Una instancia de Paquete con la respuesta de la funcion 0
        :return: None
          TypeError: Si rta no es None y no es una instancia de paquete o no es
          un paquete con funcion 0
          InactiveAppException: Si la aplicacion esta inactiva
          NodeNotExists: Si no se recibio respuesta del nodo
        """

        self._logger.info("Identificando nodo {}.".format(self.lan_dir))
        status = self.status
        try:
            if rta is None:
                paq = Paquete(destino=self.lan_dir, funcion=0)
                rta = self._ser.send_paq(paq)
            self._can_update.wait()
            if self._can_update.isSet():
                self._can_update.clear()
                self.fnapp = struct.unpack(
                    'b', rta.datos[0:1])[0] * 256 + 255 \
                    if len(rta.datos[0:1]) else None
                self.initapp = struct.unpack('b', rta.datos[1:2])[0] * 256 \
                    if len(rta.datos[1:2]) else None
                self.eeprom_size = struct.unpack('b', rta.datos[2:3])[0] * 64 \
                    if len(rta.datos[2:3]) else DEFAULT_EEPROM
                self.buffer = struct.unpack('b', rta.datos[5:6])[0] \
                    if len(rta.datos[5:6]) else DEFAULT_BUFFER
                self.ram_write = struct.unpack('b', rta.datos[6:7])[0] \
                    if len(rta.datos[6:7]) else DEFAULT_RAM_WRITE
                self.ram_read = struct.unpack('b', rta.datos[7:8])[0] \
                    if len(rta.datos[7:8]) else DEFAULT_RAM_READ
                self.ini_config = struct.unpack('b', rta.datos[8:9])[0] \
                    if len(rta.datos[8:9]) else None
                self.ini_eeprom = struct.unpack('b', rta.datos[9:10])[0] \
                    if len(rta.datos[9:10]) else None
                if len(rta.datos[3:4]):
                    servicio0 = struct.unpack('b', rta.datos[3:4])[0]
                    self._servicios['0b7'] = {
                        'estado': (servicio0 & 0b10000000) / 128,
                        'desc': 'Puede ser maestro.'}
                    self._servicios['0b6'] = {
                        'estado': (servicio0 & 0b01000000) / 64,
                        'desc': 'Tiene entradas analogicas de alta resolucion.'}
                    self._servicios['0b5'] = {
                        'estado': (servicio0 & 0b00100000) / 32,
                        'desc': 'Tiene entradas digitales o analogicas de baja resolucion.'}
                    self._servicios['0b4'] = {
                        'estado': (servicio0 & 0b00010000) / 16,
                        'desc': 'Tiene salidas analogicas o tipo PWM.'}
                    self._servicios['0b3'] = {
                        'estado': (servicio0 & 0b00001000) / 8,
                        'desc': 'Tiene salidas a rele o digitales a transistor.'}
                    self._servicios['0b2'] = {
                        'estado': (servicio0 & 0b00000100) / 4,
                        'desc': 'Tiene entradas de cuenta de alta velocidad.'}
                    self._servicios['0b1'] = {
                        'estado': (servicio0 & 0b00000010) / 2,
                        'desc': 'Tiene display y/o pulsadores.'}
                    self._servicios['0b0'] = {
                        'estado': (servicio0 & 0b00000001),
                        'desc': 'Tiene EEPROM.'}
                if len(rta.datos[4:5]):
                    servicio1 = struct.unpack('b', rta.datos[4:5])[0]
                    self.puede_master = servicio1 & 0b10000000
                    self.tiene_eeprom = servicio1 & 0b00000001
                    self._servicios['1b7'] = {
                        'estado': (servicio1 & 0b10000000) / 128,
                        'desc': 'No implementado.'}
                    self._servicios['1b6'] = {
                        'estado': (servicio1 & 0b01000000) / 64,
                        'desc': 'No implementado.'}
                    self._servicios['1b5'] = {
                        'estado': (servicio1 & 0b00100000) / 32,
                        'desc': 'No implementado.'}
                    self._servicios['1b4'] = {
                        'estado': (servicio1 & 0b00010000) / 16,
                        'desc': 'No implementado.'}
                    self._servicios['1b3'] = {
                        'estado': (servicio1 & 0b00001000) / 8,
                        'desc': 'No implementado.'}
                    self._servicios['1b2'] = {
                        'estado': (servicio1 & 0b00000100) / 4,
                        'desc': 'No implementado.'}
                    self._servicios['1b1'] = {
                        'estado': (servicio1 & 0b00000010) / 2,
                        'desc': 'No implementado.'}
                    self._servicios['1b0'] = {
                        'estado': (servicio1 & 0b00000001),
                        'desc': 'No implementado.'}
                status = 1
        except IndexError:
            self._logger.warning(
                "Nodo {} posiblemente con una version vieja de software.".format(self.lan_dir))
            status = 1
        except (WriteException, ReadException) as e:
            if self._ser.im_master:
                self._logger.error("El nodo {} no existe.".format(self.lan_dir))
                status = 3
                raise NodeNotExists
        finally:
            self._can_update.set()
            self.status = status
        self._update_to_read_eeprom()
        self._update_to_read_ram()
        self.check_app_state()

    def read_ram(self, inicio, longitud):
        return self._read_memo(inicio, longitud, instance='RAM')

    def write_ram(self, inicio, datos):
        return self._write_memo(inicio, datos, instance='RAM')

    def read_eeprom(self, inicio, longitud):
        return self._read_memo(inicio, longitud, instance='EEPROM')

    def write_eeprom(self, inicio, datos):
        return self._write_memo(inicio, datos, instance='EEPROM')

    def return_token(self):
        """
        :return: None
        :raise:
            InactiveAppException: Si la aplicacion esta inactiva.
            TokenExeption: Si no se pudo hacer el traspaso de token.
            WriteException: Si no se pudo escribir el paquete.
            ReadException: Si no se pudo leer la respuesta del nodoself.
        """

        self._logger.info("Ofreciendo token al nodo {}.".format(self.lan_dir))
        paq = Paquete(destino=self.lan_dir, funcion=7)
        rta = self._ser.send_paq(paq)
        self._ser.check_master()
        if self._ser.im_master:
            self._logger.error("Error en traspaso de master al nodo {}.".format(self.lan_dir))
            raise TokenExeption

    def read_app_line(self, inicio, longitud):
        """
        :param inicio: int Indice indicando a partir de que registro de la
        memoria de la aplicacion se quiere leer.
        :param longitud: int que indica la longitud en bytes que se quiere leer
        :return: Line instance
        :raise:
          ActiveAppException: Si la aplicacion esta inactiva
          TypeError: Si el tipo de los parametros recibidos no es correcto
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """

        if not self.aplicacion_activa:
            raise InactiveAppException

        paq = Paquete(
            destino=self.lan_dir,
            funcion=5,
            datos=struct.pack('Hb', inicio, longitud)
        )
        self._logger.info(
            "Leyendo linea del nodo {0}, inicio {1}, longitud {2}.".format(
                self.lan_dir), inicio, longitud)
        rta = self._ser.send_paq(paq)
        line = AppLine(inicio=inicio*2, paq=rta)
        return line

    def deactivate_app(self, blocking=True):
        """
        :return: None
        :raise:
          InactiveAppException: Si la aplicacion ya esta inactiva.
          ActiveAppException: Si hubo un error desactivando la aplicacion.
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """
        if not self.aplicacion_activa:
            raise InactiveAppException

        self._logger.info(
            "Desactivando aplicacion del nodo {}.".format(self.lan_dir))
        paq = Paquete(
            destino=self.lan_dir, funcion=6, datos=b'\x00\x01\xff\xff')
        rta = self._ser.send_paq(paq)
        if rta.datos != APP_DEACTIVATE_RESPONSE:
            raise ActiveAppException
        else:
            if blocking:
                while self.aplicacion_activa:
                    solicitud, estado = self.check_app_state()
                    if not estado:
                        return
                    elif not solicitud:
                        raise ActiveAppException

    def write_app_line(self, line):
        """
        :param line: Instancia de AppLine
        :return: None
        :raise:
          TypeError: Si line no es una instancia de AppLine
          ActiveAppException: Si la aplicacion esta activa
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """
        # TODO: APP_INIT_CONFIG tiene que ir en el paquete de identificacion
        if self.aplicacion_activa:
            raise ActiveAppException

        if line.inicio < self.fnapp:
            sum_inicio = 0
            for part in [line.datos[GRABA_MAX_BYTES*(i-1):GRABA_MAX_BYTES*i] for i in range(1, int(math.ceil(float(line.longitud)/GRABA_MAX_BYTES))+1)]:
                paq = Paquete(
                    destino=self.lan_dir,
                    funcion=6,
                    datos=struct.pack('H', line.inicio + sum_inicio) + part
                )
                sum_inicio += int(GRABA_MAX_BYTES/2)
                rta = self._ser.send_paq(paq)
        elif line.inicio > APP_INIT_E2:
            paq = Paquete(
                destino=self.lan_dir,
                funcion=4,
                datos=(struct.pack('b', line.inicio - APP_INIT_CONFIG) + ''.join([line.datos[i] for i in range(len(line.datos)) if not i % 2])))
            rta = self._ser.send_paq(paq)

    def activate_app(self):
        """
        :return: None
        :raise:
          ActiveAppException: Si la aplicacion ya esta activa
          InactiveAppException: Si hubo un error intentando activar la
          aplicacion
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodo.
        """
        if self.aplicacion_activa:
            raise ActiveAppException
        self._logger.info(
            "Reactivando aplicacion del nodo {}.".format(self.lan_dir))
        paq = Paquete(
            destino=self.lan_dir, funcion=6, datos=b'\x00\x00\xa5\x05')
        rta = self._ser.send_paq(paq)
        if rta.datos != APP_ACTIVATE_RESPONSE:
            raise InactiveAppException
        else:
            self.check_app_state()
            return self.aplicacion_activa

    def check_app_state(self):
        lab_gen = self.read_ram(0, 1)[0]
        self.aplicacion_activa = bool(lab_gen.get(0) & 0b10000000)
        self.solicitud_desactivacion = bool(lab_gen.get(0) & 0b01000010)
        return (self.solicitud_desactivacion, self.aplicacion_activa)

    def _update_to_read_eeprom(self):
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            to_read = [i for i in range(int(self.eeprom_size + 1)) if i not in self.index_disabled_eeprom]
            if len(to_read):
                start = min(to_read)
                last_in_paq = None
                to_read_eeprom = list()
                for i in to_read:
                    if i >= start + self.buffer:
                        size = 1 if last_in_paq < start else \
                            last_in_paq - start + 1
                        to_read_eeprom.append((size, start))
                        start = i
                    else:
                        last_in_paq = i
                if len(to_read_eeprom) > 0 and start != to_read_eeprom[-1][1]:
                    to_read_eeprom.append((last_in_paq - start if last_in_paq > start else 1, start))
                if not len(to_read_eeprom):
                    to_read_eeprom.append(((max(to_read) - min(to_read)), min(to_read)))
            else:
                to_read_eeprom = []
            self.to_read_eeprom = to_read_eeprom
            self._can_update.set()

    def _update_to_read_ram(self):
        self._can_update.wait()
        if self._can_update.isSet():
            self._can_update.clear()
            to_read = [i for i in range(int(self.ram_read + 1)) if i not in self.index_disabled_ram]
            if len(to_read):
                start = min(to_read)
                last_in_paq = None
                to_read_ram = list()
                for i in to_read:
                    if i >= start + self.buffer:
                        size = 1 if last_in_paq < start else last_in_paq - start + 1
                        to_read_ram.append((size, start))
                        start = i
                    else:
                        last_in_paq = i
                if len(to_read_ram) > 0 and start != to_read_ram[-1][1]:
                    to_read_ram.append((last_in_paq - start if last_in_paq > start else 1, start))
                if not len(to_read_ram):
                    to_read_ram.append(((max(to_read) - min(to_read)), min(to_read)))
            else:
                to_read_ram = []
            self.to_read_ram = to_read_ram
            self._can_update.set()

    def _read_memo(self, inicio, longitud, instance):
        """

        :param inicio: int que indica el indice de incio de memoria que se
        quiere leer
        :param longitud: int que indica la longitud en bytes que se quiere leer
        :param instance: str que indica la instancia de la memoria que se
        quiere leer (RAM o EEPROM)
        :return: Lista de memo_instances para cada uno de los valores leidos
        :raise:
          InactiveAppException: Si la aplicacion esta inactiva.
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodo.
        """

        if self._ser.im_master:
            self._logger.debug(
                "Leyendo memoria del nodo {}.".format(self.lan_dir))
            paq = Paquete(
                destino=self.lan_dir,
                funcion=MEMO_READ_NAMES[instance],
                datos=struct.pack('2b', inicio, longitud)
            )
            paq = self._ser.send_paq(paq)
            timestamp = time.time()
            memo_instances = []
            if instance == 'RAM':
                self.ram_lock.acquire()
            elif instance == 'EEPROM':
                self.eeprom_lock.acquire()
            for k, v in enumerate(paq.datos):
                indice = inicio + k
                memo = MemoInstance(
                    nodo=self.lan_dir,
                    tipo=instance,
                    inicio=indice,
                    timestamp=timestamp,
                    valores=paq.datos[k:k+1]
                )
                if memo.tipo == 'RAM':
                    self.ram[indice] = memo
                elif memo.tipo == 'EEPROM':
                    self.eeprom[indice] = memo
                memo_instances.append(memo)
            if instance == 'RAM':
                self.ram_lock.release()
            elif instance == 'EEPROM':
                self.eeprom_lock.release()
        else:
            memo_instances = []
            if instance == 'RAM':
                self.ram_lock.acquire()
                for i in range(inicio, inicio + longitud + 1):
                    memo_instances.append(self.ram[i])
                self.ram_lock.release()
            elif instance == 'EEPROM':
                self.eeprom_lock.acquire()
                for i in range(inicio, inicio + longitud + 1):
                    memo_instances.append(self.eeprom[i])
                self.eeprom_lock.release()
        return memo_instances

    def _write_memo(self, inicio, datos, instance):
        """
        :param inicio: int Indice indicando a partir de que registro de la
        memoria se quiere escribir
        :param datos: str datos que se quieren escribir en hexadecimal
        :param instance: str que indica la instancia de la memoria que se
        quiere escribir (RAM o EEPROM)
        :return: None
        :raise:
          EncodeError: Si el formato de datos no es correcto
          InactiveAppException: Si la aplicacion esta inactiva
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodo.
        """

        self._logger.info(
            "Escribiendo datos {0} en nodo {1}.".format(
                binascii.hexlify(datos), self.lan_dir))
        try:
            paq = Paquete(
                destino=self.lan_dir,
                funcion=MEMO_WRITE_NAMES[instance],
                datos=struct.pack('b', inicio) + datos
            )
        except struct.error:
            raise EncodeError
        self._ser.send_paq(paq)

    def __state__(self):
        return '{1}_{3}{0}{2}'.format(
                COMMAND_SEPARATOR,
                MSG_NODE_PREFIX,
                self.report(),
                self.lan_dir)

    def report(self):
        return json.dumps({
            'lan_dir': self.lan_dir,
            'status': self.status,
            'im_master': self.im_master,
            'enabled_read_node': self.enabled_read_node,
            'enabled_read_ram':  self.enabled_read_ram,
            'enabled_read_eeprom': self.enabled_read_eeprom,
            'enabled_read_eeprom_index': [i for i in range(self.eeprom_size+1) if i not in self.index_disabled_eeprom],
            'enabled_read_ram_index': [i for i in range(self.ram_read+1) if i not in self.index_disabled_ram],
            'time': time.time(),
        })

    def __str__(self):
        return json.dumps({
            'lan_dir': self.lan_dir,
            'status': self.status,
            'buffer': self.buffer,
            'ram_read': self.ram_read,
            'ram_write': self.ram_write,
            'initapp': self.initapp,
            'fnapp': self.fnapp,
            'eeprom_size': self.eeprom_size,
            'im_master': self.im_master,
            'enabled_read_node': self.enabled_read_node,
            'enabled_read_ram':  self.enabled_read_ram,
            'enabled_read_eeprom': self.enabled_read_eeprom,
            'enabled_read_eeprom_index': [i for i in range(self.eeprom_size+1) if i not in self.index_disabled_eeprom],
            'enabled_read_ram_index': [i for i in range(self.ram_read+1) if i not in self.index_disabled_ram],
            'servicios': self._servicios,
            'time': time.time(),
        })
