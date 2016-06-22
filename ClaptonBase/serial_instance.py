import time, zmq, serial
import binascii
from threading import Thread, Lock, Event
from random import random
from . import decode
from .exceptions import WriteException, ReadException, ChecksumException, \
    NoMasterException, SerialConfigError, NoSlaveException
from .containers import Paquete
from .cfg import *
from .utils import get_logger, MasterEvent, GiveMasterEvent
from .mock_serial import MockSerial

class SerialInterface(object):
    def __init__(self,
                 serial_port='/dev/ttyAMA0',
                 conn_port=DEFAULT_CONN_PORT,
                 baudrate=DEFAULT_BAUDRATE,
                 timeout=DEFAULT_SERIAL_TIMEOUT,
                 log_level=DEFAULT_LOG_LVL,
                 log_file=DEFAULT_LOG_FILE,
                 mocking=False):

        self._logger = get_logger(__name__, log_level, log_file)
        self._logger.info("Iniciando SerialInstance.")
        self.context = zmq.Context()
        self.connection_socket = self.context.socket(zmq.PUB)
        self.connection_socket.bind("tcp://*:%s" % conn_port)

        self.using_ser = Lock()
        self._serial_port = serial_port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser = None
        self._mocking = mocking

        self.ser_seted = Event()
        self._stop = False
        self._tries_reconect = 0

        self.connection_thread = Thread(target=self._connection)

        self.im_master = False
        self.want_master = MasterEvent()
        self.give_master = GiveMasterEvent()

    def start(self):
        self.connection_thread.start()
        self.check_master()
        return self

    def stop(self):
        self._logger.info("Parando SerialInstance.")
        self._stop = True
        try:
            self.connection_thread.join()
            self.connection_thread = None
        except (AttributeError, RuntimeError) as e:
            pass
        if self._ser is not None:
            self._ser.close()
        self.connection_socket.close()
        self.context.term()

    def _do_reconect(self):
        if not self.ser_seted.isSet():
            self._logger.error('Perdimos la conexion con el puerto serie. Se intenta reconectar.')
        while not self.ser_seted.isSet() and not self._stop:
            try:
                self._ser.open()
                self.ser_seted.set()
                self._tries_reconect = 0
            except serial.SerialException as e:
                self._logger.error('Error intentando abrir el puerto serie: %s' % str(e))

                self.ser_seted.clear()
                self._tries_reconect += 1
                if self._tries_reconect < INSTANT_RECONECT_TRIES:
                    time.sleep(random())
                else:
                    self.notify_con_master(0)
                    time.sleep(LONG_RECONECT_PERIOD+random())

    def _do_connect(self):
        try:
            if not self._mocking:
                self._ser = serial.Serial(port=self._serial_port, baudrate=self._baudrate, timeout=self._timeout)
            else:
                self._ser = MockSerial(port=self._serial_port, baudrate=self._baudrate, timeout=self._timeout)
            self.ser_seted.set()
        except (serial.SerialException, OSError) as e:
            self._logger.error('Error intentando abrir el puerto serie: %s' % str(e))
            raise SerialConfigError

    def _connection(self):
        self._logger.info("Iniciando ConnectionThread.")
        t = time.time() + CON_STATUS_PERIOD
        self._do_connect()

        while not self._stop:
            if CON_STATUS_PERIOD and time.time() > t:
                self.notify_con_master()
                t = time.time() + CON_STATUS_PERIOD
            self._do_reconect()

    def notify_con_master(self, status=1):
        """
        :param status: Indica el estado de la conexion de puerto serie
        :return: Nada, pero manda dos mensajes. Uno indicando la conexion del puerto serie y el otro indicando la conexion
        del master.
        El formato de mensaje de la conexion del master es:  PREFIJO im_master want_master give_master node
        """
        self._logger.debug("Notificando estado de conexion y master.")
        self.connection_socket.send_string("%s %d" % (MSG_CON_PREFIX, status))
        msg = '%s %d %d %d' % (MSG_MASTER_PREFIX, self.im_master, self.want_master.isSet(), self.give_master.isSet()) \
            if not self.give_master.isSet() else \
            "%s %d %d %d %d" % \
            (MSG_MASTER_PREFIX, self.im_master, self.want_master.isSet(), self.give_master.isSet(), self.give_master.node)
        self.connection_socket.send_string(msg)

    def send_paq(self, paq):
        """
        param paq: Paquete instance
        return:
            rta: Paquete con respuesta del nodo
            echo: Paquete con el echo del nodo
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
        if self.ser_seted.isSet():
            self.using_ser.acquire()
            try:
                self._ser.flushInput()
                self._logger.debug('Escribiendo: %s', paq.representation)
                self._ser.write(paq.to_write)
                rta1 = self._ser.read(len(paq.to_write))
                self._logger.debug('ECHO: %s', binascii.hexlify(rta1))
                if not len(rta1):
                    self._logger.error('No hay respuesta del echo en paquete para el nodo %d', paq.destino)
                    raise ReadException
                try:
                    paq1 = Paquete(paq=rta1)
                except ChecksumException:
                    self._logger.error('No se resuelve checksum en echo para el nodo %d', paq.destino)
                    raise ReadException

                rta2 = self._ser.read(paq.rta_size)
                self._logger.debug('Respuesta: %s', binascii.hexlify(rta2))
                try:
                    paq2 = Paquete(paq=rta2)
                except (ChecksumException, IndexError) as e:
                    raise WriteException
                return paq2, paq1
            except AttributeError as e:
                self._ser.close()
                self.ser_seted.clear()
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
        if self.ser_seted.isSet():
            self.using_ser.acquire()
            try:
                ser_buffer = self._ser.read()
                while not self._stop:
                    ser_buffer += self._ser.read(3)
                    if len(ser_buffer) == 1:
                        ser_buffer += self._ser.read()
                    try:
                        funcion, longitud, _ = decode.fun_lon(ser_buffer[1:2])
                        if len(ser_buffer) < longitud + 2:
                            ser_buffer += self._ser.read(longitud+2-len(ser_buffer))
                        if len(ser_buffer) < longitud + 3:
                            ser_buffer += self._ser.read()
                        str_paq = ser_buffer[:(longitud+3)]
                        paq = Paquete(paq=str_paq)
                        ser_buffer = ser_buffer[(longitud+3):]
                    except (ChecksumException, DecodeError) as e:
                        self._logger.warning("Paquete perdido.")
                        ser_buffer = ser_buffer[1:]
                        continue
                    if self.want_master.isSet() and paq.funcion == 7 and not len(ser_buffer):
                        self._logger.info('Aceptando oferta de token.')
                        token_rta = Paquete(origen=0, destino=paq.origen, funcion=7)
                        self._ser.write(token_rta.to_write)
                        rta1 = self._ser.read(len(token_rta.to_write))
                        rta2 = self._ser.read(token_rta.rta_size)
                        self._logger.info('Respuesta del master %s.', binascii.hexlify(rta2))
                        self.check_master(ser_locked=True)
                        if self.im_master:
                            self.want_master.clear()
                    yield paq
            except AttributeError:
                self._logger.error("Error en puerto serie.")
                self._ser.close()
                self.ser_seted.clear()
                raise ReadException
            except IndexError:
                self._logger.warning('Funcion read_ser no recibe nada. Longitud ser_buffer %d', len(ser_buffer))
                self.check_master(ser_locked=True)
                if self.im_master and not self.want_master.isSet():
                    raise NoSlaveException
            finally:
                self.want_master.clear()
                self.using_ser.release()

    def check_master(self, ser_locked=False):
        """
        raise:
            ReadException
        """
        self._logger.info('Chequeando estado del master.')
        if not ser_locked:
            self._logger.info('Bloqueando puerto serie.')
            self.using_ser.acquire()
        timeout = time.time() + WAIT_MASTER_PERIOD
        if self.ser_seted.isSet():
            try:
                read = ''
                self._ser.flushInput()
                while not len(read):
                    if time.time() > timeout:
                        break
                    read = self._ser.read()
                self.im_master = len(read) == 0
                self.notify_con_master()
            except AttributeError:
                self._ser.close()
                self.ser_seted.clear()
                raise ReadException

            finally:
                if not ser_locked:
                    self.using_ser.release()
        self._logger.info('Master: %s' % str(self.im_master))
