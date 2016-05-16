__author__ = 'bruno'
import time, zmq, serial
from threading import Thread, Lock, Event
from random import random
from . import decode
from .exceptions import WriteException, ReadException, BadChecksumException, NoMasterException, SerialConfigError
from .containers import Paquete

from .cfg import *
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
        context = zmq.Context()
        self.connection_socket = context.socket(zmq.PUB)
        self.connection_socket.bind("tcp://*:%s" % conn_port)

        self.using_ser = Lock()
        self._serial_port = serial_port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser = None

        self.ser_seted = Event()
        self._stop = False

        self.connection_thread = Thread(target=self._connection).start()

        self.im_master = False
        self.want_master = MasterEvent()
        self.give_master = GiveMasterEvent()
        self.check_master()

    def stop(self):
        self._logger.info("Parando SerialInstance.")
        self._stop = True
        if self.connection_thread is not None:
            self.connection_thread.join()
            self.connection_thread = None
        if self._ser is not None:
            self._ser.close()
        self.connection_socket.stop()

    def _connection(self):
        self._logger.info("Iniciando ConnectionThread.")
        t = time.time() + CON_STATUS_PERIOD
        try:
            self._ser = serial.Serial(port=self._serial_port, baudrate=self._baudrate, timeout=self._timeout)
            self.ser_seted.set()
        except serial.SerialException as e:
            self._logger.error('Error intentando abrir el puerto serie: %s' % str(e))
            self.stop()
            raise SerialConfigError

        while not self._stop:
            tries_connect = 0
            if CON_STATUS_PERIOD and time.time() > t:
                self.notify_con_master()
                t = time.time() + CON_STATUS_PERIOD
            if not self.ser_seted.isSet():
                self._logger.error('Perdimos la conexion con el puerto serie. Se intenta reconectar.')
            while not self.ser_seted.isSet() and not self._stop:
                try:
                    self._ser.open()
                    self.ser_seted.set()
                except serial.SerialException as e:
                    self._logger.error('Error intentando abrir el puerto serie: %s' % str(e))

                    self.ser_seted.clear()
                    tries_connect += 1
                    if tries_connect < INSTANT_RECONECT_TRIES:
                        time.sleep(random())
                    else:
                        self.notify_con_master(0)
                        time.sleep(LONG_RECONECT_PERIOD+random())

    def notify_con_master(self, status=1):
        """
        :param status: Indica el estado de la conexion de puerto serie
        :return: Nada, pero manda dos mensajes. Uno indicando la conexion del puerto serie y el otro indicando la conexion
        del master.
        El formato de mensaje de la conexion del master es:  PREFIJO im_master want_master give_master node
        """
        self._logger.debug("Notificando estado de conexion y master.")
        self.connection_socket.send("%s %d" % (MSG_CON_PREFIX, status))
        msg = '%s %d %d %d' % (MSG_MASTER_PREFIX, self.im_master, self.want_master.isSet(), self.give_master.isSet()) \
            if not self.give_master.isSet() else \
            "%s %d %d %d %d" % \
            (MSG_MASTER_PREFIX, self.im_master, self.want_master.isSet(), self.give_master.isSet(), self.give_master.node)
        self.connection_socket.send(msg)

    def send_paq(self, paq):
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
                self._logger.debug('ECHO: %s', rta1.encode('hex'))
                if not len(rta1):
                    self._logger.error('No hay respuesta del echo en paquete para el nodo %d', paq.destino)
                    raise ReadException()
                try:
                    paq1 = Paquete(paq=rta1)
                except BadChecksumException:
                    self._logger.error('No se resuelve checksum en echo para el nodo %d', paq.destino)
                    raise ReadException()

                rta2 = self._ser.read(paq.rta_size)
                self._logger.debug('Respuesta: %s', rta2.encode('hex'))
                try:
                    paq2 = Paquete(paq=rta2)
                except (BadChecksumException, IndexError) as e:
                    raise WriteException()
                return paq2, paq1
            except (serial.portNotOpenError, AttributeError) as e:
                self._ser.close()
                self.ser_seted.clear()
                raise WriteException()
            finally:
                self.using_ser.release()

    def read_paq(self):
        self._logger.debug("Esperando disponibilidad de puerto serie.")
        if self.ser_seted.isSet():
            self.using_ser.acquire()
            ser_buffer = self._ser.read()
            try:
                while not self._stop:
                    ser_buffer += self._ser.read(3)
                    if len(ser_buffer) == 1:
                        ser_buffer += self._ser.read()
                    funcion, longitud, _ = decode.func_lon(ser_buffer[1])
                    if len(ser_buffer) < longitud + 2:
                        ser_buffer += self._ser.read(longitud+2-len(ser_buffer))
                    if len(ser_buffer) < longitud + 3:
                        ser_buffer += self._ser.read()
                    str_paq = ser_buffer[:(longitud+3)]
                    try:
                        paq = Paquete(paq=str_paq)
                        ser_buffer = ser_buffer[(longitud+3):]
                    except BadChecksumException:
                        self._logger.warning("Paquete perdido.")
                        ser_buffer = ser_buffer[1:]
                        continue
                    if self.want_master.isSet() and paq.funcion == 7 and not len(ser_buffer):
                        self._logger.info('Aceptando oferta de token.')
                        token_rta = Paquete(origen=0, destino=paq.origen, funcion=7)
                        self._ser.write(token_rta.to_write)
                        rta1 = self._ser.read(len(token_rta.to_write))
                        rta2 = self._ser.read(token_rta.rta_size)
                        self._logger.info('Respuesta del master %s.', rta2.encode('hex'))
                        self.check_master(ser_locked=True)
                        if self.im_master:
                            self.want_master.clear()
                    yield paq
            except IndexError:
                self._logger.warning('Funcion read_ser no recibe nada. Longitud ser_buffer %d', len(ser_buffer))
                self.check_master(ser_locked=True)
            except (serial.portNotOpenError, AttributeError) as e:
                self._logger.error("Error en puerto serie.")
                self._ser.close()
                self.ser_seted.clear()
                raise ReadException()
            finally:
                self.want_master.clear()
                self.using_ser.release()

    def check_master(self, ser_locked=False):
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
            except (serial.portNotOpenError, AttributeError) as e:
                self._ser.close()
                self.ser_seted.clear()
            finally:
                if not ser_locked:
                    self.using_ser.release()
        self._logger.info('Master: %s' % str(self.im_master))
