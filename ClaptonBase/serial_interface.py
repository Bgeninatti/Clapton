"""
.. module:: serial
    :platform: Unix
    :synopsis: This module only provide the class :class:`SerialInterface`

"""
import time
from threading import Lock, Thread

import serial

from . import decode
from . import cfg
from .containers import Package
from .exceptions import (ChecksumException, DecodeError, NoMasterException,
                         NoSlaveException, ReadException, SerialConfigError,
                         WriteException, TokenException)
from .utils import GiveMasterEvent, MasterEvent, get_logger


logger = get_logger('serial')


class SerialInterface(object):
    """
    This class handle the comunication with the serial port.

    The connection with the port is managed by this class in a independient
    thread. In case that the connection was interrupted for some reason (for
    example, you unplug the TKLan cable) the process in this thread will try
    to reconnect and the pending operation with the port will be stoped until
    the connection be restablished.

    This class also provides functions to make the master interaction between nodes:

    * :func:`acept_token`: to accept a token offer from a node.
    * :func:`check_master`: to check if there's any master on the network or not. If not this means that you are master!
    """

    def __init__(self,
                 serial_port='/dev/ttyAMA0',
                 baudrate=cfg.DEFAULT_BAUDRATE,
                 timeout=cfg.DEFAULT_SERIAL_TIMEOUT):
        """
        This class initialize with the information about
        where connect (``serial_port``), at what speed (``baudrate``)
        and how much have to wait if nobody is talking or theres no response
        to your answer (``timeout``).

        :param serial_port:The path to the serial port in the sistem. The
            default value correspond to the Raspbian distribution for Raspberry Pi: ``/dev/ttyAMA0``
        :type serial_port: str
        :param baudrate: The baudrate int bits per second. The default is 2400,
            the value used for most Teknotrol equpiments.
        :type baudrate: int
        :param timeout: The timeout of the serial port when there's no response
        :type timeout: int | float
        :param log_level: The log level for the logger according with the
            :mod:`logging` python library
        :type log_level: str
        :param log_file: The file where the logs will be saved. The default
            value is None, that means that the logs will be shown in the stdout.
        :type log_file: str

        .. note::
            The default baudrate correspond with the equipments developed before
            2018. From that time the baudrate also is 9600 for some equipments
            like TKL693.

        """

        logger.info("Iniciando SerialInstance.")
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
        """
        Start te connection thread, wich means that connect and try
        to mantain that connection in case that an exception ocurr.
        """
        self._connection_thread.start()
        return self

    def stop(self):
        """
        Close the connection with the serial port and stop the connection
        thread.
        """
        logger.info("Parando SerialInstance.")
        self._stop = True
        self._connection_thread.join(timeout=5)
        if self._connection_thread.is_alive():
            self._connection_thread.terminate()
        self._ser.close()

    def isOpen(self):
        return self._ser.isOpen()

    def _do_connect(self):
        """
        Try to open the serial port and run :func:`check_master` to know wich
        of the nodes is master or if you are the master.
        """
        try:
            self._ser.open()
            self.check_master()
        except (serial.SerialException, OSError) as e:
            logger.error(
                'Error intentando abrir el puerto serie: %s', str(e))
            raise SerialConfigError()
        return self.isOpen()

    def _connection(self):
        """
        This is the function that execute the `_connection_thread`. If the
        port is not open, run _do_connect until we say it that stop (by
        running the :fun:`stop`).
        """
        logger.info("Iniciando ConnectionThread.")
        self._do_connect()
        while not self._stop:
            if not self.isOpen():
                logger.error(
                    'Perdimos la conexion con el puerto serie. Reconectando...')
                self._do_connect()

    def listen_package(self):
        """
        Try to listen an entire package from the up comming bytes in the serial port.
        If the checkum is not write raises ReadException
        """
        head_bytes = self._ser.read(2)
        if len(head_bytes) < 2:
            raise ReadException()
        function, length = decode.function_length(head_bytes[1:2])
        tail_bytes = self._ser.read(length+1)
        readed_package = Package(bytes_chain=head_bytes+tail_bytes)
        return readed_package

    def get_package_from_length(self, length):
        bytes_chain = self._ser.read(length)
        package = Package(bytes_chain=bytes_chain)
        return package

    def send_package(self, package):
        """
        In case that you where master (``im_master = True``) you are allowed to
        send packages to another nodes with this function.
        It took a :class:`Paquete`, send it throght the serial port and listen.
        If everything goes well the first thing that show up as response is the package's
        echo. Later, if the node in the package destination exists in the network, the response
        should appear in the port. If not, once the `timeout` finish an `ReadException` raises.

        :param package: The package that you want to send throght the serial port
        :type package: :func:`Paquete`
        :rtype: :func:`Paquete` with the response from the node

        raises:
            * NoMasterException: In case that you try to send a package but you
                are not master.
            * ReadException: In case that there's no echo response.
            * WriteException: In case that the node don't answer.
        """
        if not self.im_master:
            raise NoMasterException()
        logger.debug("Esperando disponibilidad de puerto serie.")
        tries = 0
        with self.using_ser:
            while 1:
                try:
                    self._ser.flushInput()
                    self._ser.write(package.bytes_chain)
                    echo_package = self.get_package_from_length(len(package.bytes_chain))
                    self._ser.write(bytes(package))
                    echo_package = self.listen_package()
                    try:
                        response_package = self.listen_package()
                        return response_package
                    except (ReadException, ChecksumException) as error:
                            raise WriteException()
                except (WriteException, ReadException, ChecksumException) as error:
                    if tries < cfg.SEND_PACKAGE_TRIES:
                        tries += 1
                        logger.error(error)
                    else:
                        raise error

    def listen_packages(self):
        """
        If you are not master this means that you anly can listen to the packages in
        the network.
        This function returns a generator that on each iteration yield a :class:`package`.
        Also check if ``want_master`` flag is set to know if should answer to the token
        offer when appear.

        return:
            Python generator

        yield: :class:`Paquete`

        raises:
            * NoSlaveException: In case that the serial port don't return nothing.
                Which means that nobody is talking, so you are master now.
        """
        logger.debug("Esperando disponibilidad de puerto serie.")
        with self.using_ser:
            bytes_chain = b''
            while not self._stop:
                try:
                    bytes_chain += self._ser.read(3)
                    function, data_length = decode.function_length(bytes_chain[1:2])
                    package_length = data_length + 3
                    if len(bytes_chain) < package_length:
                        bytes_chain += self._ser.read(package_length-len(bytes_chain))
                    package = Package(bytes_chain=bytes_chain[:package_length])
                    bytes_chain = bytes_chain[package_length:]

                    if self.want_master.isSet() and package.function == 7 and not len(bytes_chain):
                        self.accept_token(package.sender)
                        self.check_master(ser_locked=True)
                        if self.im_master:
                            self.want_master.clear()
                    yield package
                except (ChecksumException, DecodeError) as e:
                    logger.info("Paquete perdido.")
                    bytes_chain = bytes_chain[1:]
                    continue
                except IndexError:
                    logger.warning(
                        'Funcion read_ser no recibe nada.')
                    self.check_master(ser_locked=True)
                    if self.im_master and not self.want_master.isSet():
                        self.want_master.clear()
                        raise NoSlaveException()

    def accept_token(self, sender):
        """
        This function answer the token offer to a specific node.
        Usualy is executed by :func:``read_paq`` when the flag ``want_master``
        is set.

        If you want to use this in another place, take care about the timeout to
        respond the token offer if you are not master.

        :param origen: The ``lan_dir`` of the node that send the token offer.

        """
        logger.info('Aceptando oferta de token.')
        token_rta = Package(destination=sender, function=7)
        self._ser.write(token_rta.bytes_chain)
        echo_package = self.get_package_from_length(len(token_rta.bytes_chain))
        response = self.get_package_from_length(
            cfg.TOKEN_ACCEPTANCE_RTA_SIZE)
        package = Package(destination=sender, function=7)
        self._ser.write(bytes(package))
        echo_package = self.listen_package()
        response = self.listen_package()
        return response

    def offer_token(self, destination):
        """
        :return: None
        :raise:
            TokenExeption: Si no se pudo hacer el traspaso de token.
            WriteException: Si no se pudo leer el echo.
            ReadException: Si no se pudo leer la respuesta del nodo.
        """

        logger.info("Ofreciendo token al nodo {}.".format(destination))
        token_offer = Package(destination=destination, function=7)
        self._ser.write(token_offer.bytes_chain)
        echo_package = self.get_package_from_length(len(token_offer.bytes_chain))
        response = self.get_package_from_length(
            cfg.TOKEN_OFFER_RTA_SIZE)
        package = Package(destination=destination, function=7)
        self._ser.write(bytes(package))
        echo_package = self.listen_package()
        response = self.listen_package()
        self.check_master()
        if self.im_master:
            logger.error(
                "Error en traspaso de master al nodo %s.",
                destination)
            raise TokenException()

    def check_master(self, ser_locked=False):
        """
        Listen the serial port until ``WAIT_MASTER_PERIOD`` is reached
        if can't read any byte from the network this means that I'm
        master. If is full of something this means that another node
        is master.

        :param ser_locked: Flag that indicate if the serial port was locked
            before calling ``check_master`` for another function, or if it
            should be locked for made the master check.
        """
        if not ser_locked:
            self.using_ser.acquire()
        timeout = time.time() + cfg.WAIT_MASTER_PERIOD
        bytes_chain = b''
        self._ser.flushInput()
        while time.time() < timeout:
            bytes_chain += self._ser.read()
        self.im_master = len(bytes_chain) == 0
        if not ser_locked:
            self.using_ser.release()
        logger.info('Chequeo del master: %s', self.im_master)
