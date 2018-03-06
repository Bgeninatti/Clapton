import time
import zmq
import serial
import binascii
from threading import Thread, Lock, Event
from random import random
from . import decode
from .exceptions import WriteException, ReadException, ChecksumException, \
    NoMasterException, SerialConfigError, NoSlaveException, DecodeError
from .containers import Paquete
from .cfg import *
from .consts import *
from .utils import get_logger, MasterEvent, GiveMasterEvent


class SerialInterface(object):
    def __init__(self,
                 serial_port='/dev/ttyAMA0',
                 conn_port=DEFAULT_CONN_PORT,
                 baudrate=DEFAULT_BAUDRATE,
                 timeout=DEFAULT_SERIAL_TIMEOUT,
                 log_level=DEFAULT_LOG_LVL,
                 log_file=DEFAULT_LOG_FILE):

        self._logger = get_logger(__name__, log_level, log_file)
        self._logger.info("Iniciando SerialInstance.")

        self.using_ser = Lock()
        self._serial_port = serial_port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser = serial.Serial()
        self._ser.baudrate = self._baudrate
        self._ser.timeout = self._timeout
        self._ser.port = self._serial_port

        self._stop = False

        self._connection_thread = Thread(target=self._connection)

        self.im_master = False
        self.want_master = MasterEvent()
        self.give_master = GiveMasterEvent()

    def start(self):
        self._connection_thread.start()
        return self

    def stop(self):
        self._logger.info("Parando SerialInstance.")
        self._stop = True
        if self._ser is not None:
            self._ser.close()
        self._connection_thread.join()

    def _do_connect(self):
        try:
            self._ser.open()
            self.check_master()
        except (serial.SerialException, OSError) as e:
            self._logger.error(
                'Error intentando abrir el puerto serie: %s' % str(e))
            raise SerialConfigError
        return self._ser.isOpen()

    def _connection(self):
        self._logger.info("Iniciando ConnectionThread.")
        self._do_connect()
        while not self._stop:
            if not self._ser.isOpen():
                self._logger.error(
                    'Perdimos la conexion con el puerto serie. Reconectando...')
                self._do_connect()

    def notify_con_master(self, status=1):
        """
        :param status: Indica el estado de la conexion de puerto serie
        :return: Nada, pero manda dos mensajes. Uno indicando la conexion
        del puerto serie y el otro indicando la conexion
        del master.
        El formato de mensaje de la conexion del master es:  PREFIJO im_master
        want_master give_master node
        """
        con_msg = "{1}{0}{2}".format(COMMAND_SEPARATOR, MSG_CON_PREFIX, status)
        master_msg = '{1}{0}{2}{0}{3}{0}{4}'.format(
                COMMAND_SEPARATOR,
                MSG_MASTER_PREFIX,
                int(self.im_master),
                int(self.want_master.isSet()),
                int(self.give_master.isSet()))
        if self.give_master.isSet():
            master_msg = '{1}{0}{2}'.format(msg, self.give_master.node)

    def send_paq(self, paq):
        """
        param paq: Paquete instance
        return:
            rta: Paquete con respuesta del nodo
        raise:
            NoMasterException
            TypeError
            ReadException
            WriteException
        """
        if not isinstance(paq, Paquete):
            raise TypeError
        if not self.im_master:
            raise NoMasterException
        self._logger.debug("Esperando disponibilidad de puerto serie.")
        if self._ser.isOpen():
            self.using_ser.acquire()
            try:
                self._ser.flushInput()
                self._logger.debug('Escribiendo: %s', paq.representation)
                self._ser.write(paq.to_write)
                echo = self._ser.read(len(paq.to_write))
                self._logger.debug('ECHO: %s', binascii.hexlify(echo))
                if not len(echo):
                    self._logger.error(
                        'No hay respuesta del echo en paquete para el nodo %d',
                        paq.destino)
                    raise ReadException
                try:
                    paq_echo = Paquete(paq=echo)
                except ChecksumException:
                    self._logger.error(
                        'No se resuelve checksum en echo para el nodo %d',
                        paq.destino)
                    raise ReadException

                rta = self._ser.read(paq.rta_size)
                self._logger.debug('Respuesta: %s', binascii.hexlify(rta))
                try:
                    paq_rta = Paquete(paq=rta)
                except (ChecksumException, IndexError) as e:
                    raise WriteException
                return paq_rta
            except SerialException as e:
                self._logger.error(
                    'Error en el puerto serie: %s'.format(str(e))
                )
                raise WriteException
            finally:
                self.using_ser.release()

    def read_paq(self):
        """
        return:
            generador de paquetes
        raise:
            ReadException
            NoSlaveException
        """
        self._logger.debug("Esperando disponibilidad de puerto serie.")
        if self._ser.isOpen():
            self.using_ser.acquire()
            ser_buffer = ''
            while not self.im_master:
                try:
                    ser_buffer += self._ser.read(3)
                    funcion, longitud = decode.fun_lon(ser_buffer[1:2])
                    if len(ser_buffer) < longitud + 3:
                        ser_buffer += self._ser.read(
                            longitud+3-len(ser_buffer))
                    str_paq = ser_buffer[:longitud+3]
                    paq = Paquete(paq=str_paq)
                    ser_buffer = ser_buffer[(longitud+3):]

                    if self.want_master.isSet() and paq.funcion == 7 and not len(ser_buffer):
                        self.acept_token(paq.origen)
                        self.check_master(ser_locked=True)
                        if self.im_master:
                            self.want_master.clear()

                    yield paq

                except (ChecksumException, DecodeError) as e:
                    self._logger.warning("Paquete perdido.")
                    ser_buffer = ser_buffer[1:]
                    continue

                except SerialException as e:
                    self._logger.error(
                        'Error en el puerto serie: %s'.format(str(e))
                    )

                except IndexError:
                    self._logger.warning(
                        'Funcion read_ser no recibe nada. Longitud ser_buffer {}'.format(len(ser_buffer)))
                    self.check_master(ser_locked=True)
                    if self.im_master and not self.want_master.isSet():
                        raise NoSlaveException
            self.want_master.clear()
            self.using_ser.release()

    def acept_token(self, origen):
        self._logger.info('Aceptando oferta de token.')
        token_rta = Paquete(
            origen=0, destino=origen, funcion=7)
        self._ser.write(token_rta.to_write)
        echo = self._ser.read(len(token_rta.to_write))
        rta = self._ser.read(token_rta.rta_size)
        self._logger.info(
            'Respuesta del master %s.', binascii.hexlify(rta))

    def check_master(self, ser_locked=False):
        """
        raise:
            ReadException
        """
        self._logger.debug('Chequeando estado del master.')
        if not ser_locked:
            self._logger.debug('Bloqueando puerto serie.')
            self.using_ser.acquire()
        timeout = time.time() + WAIT_MASTER_PERIOD
        try:
            if self._ser.isOpen():
                read = ''
                self._ser.flushInput()
                while not len(read):
                    if time.time() > timeout:
                        break
                    read = self._ser.read()
                self.im_master = len(read) == 0
        except AttributeError:
            self._ser.close()
            raise ReadException

        finally:
            if not ser_locked:
                self.using_ser.release()
        self._logger.info('Chequeo del master: {}'format(str(self.im_master)))
