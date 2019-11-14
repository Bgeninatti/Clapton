
import binascii
import traceback
from threading import Thread

import zmq

from . import cfg
from .containers import Package
from .utils import get_logger
from .exceptions import NoMasterException, ReadException

logger = get_logger('server')


class TKLanServer(Thread):
    """
    This class provides declarations of the main functions in \
    the Clapton Server architecture,
    """
    def __init__(self,
                 serial_instance,
                 publisher_port=cfg.PUBLISHER_PORT,
                 commands_port=cfg.COMMANDS_PORT,
                 streaming_packages=[],
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        # serial connection
        self.ser = serial_instance

        # Inicio context para ZMQ
        self.context = zmq.Context()
        self.publisher_port = publisher_port
        self.publisher_socket = None
        self.commands_port = commands_port
        self.commands_socket = None

        self.streaming_packages = streaming_packages
        self._next_streaming_package = 0

        # Bandera de parada para los Threads
        self.stop = False
        self.setup()
        logger.info("TKLan Server initialized")

    def setup(self):
        try:
            logger.info("Starting publisher socket")
            self.publisher_socket = self.context.socket(zmq.PUB)
            self.publisher_socket.bind(
                "tcp://*:{0}".format(self.publisher_port))
            logger.info("Starting commands sockets")
            self.commands_socket = self.context.socket(zmq.REP)
            self.commands_socket.bind(
                "tcp://*:{0}".format(self.commands_port))
        except zmq.ZMQError as error:
            self.context.term()
            raise error

    def join(self, *args, **kwargs):
        """
        Stop the server. You shouldn't extend this function.
        """
        self.stop = True
        logger.info("Stopping publisher socket")
        self.publisher_socket.close()
        logger.info("Stopping commands socket")
        self.commands_socket.close()
        logger.info("Closing ZMQ context")
        self.context.term()
        super().join(*args, **kwargs)
        logger.info("TKLan server stoped")

    def get_request(self):
        is_command = False
        request = None
        try:
            msg = self.commands_socket.recv_json(zmq.NOBLOCK)
            logger.info("Message received: message=%s", msg)
            request = Package(
                sender=msg['sender'],
                destination=msg['destination'],
                function=msg['function'],
                data=binascii.unhexlify(msg['data']),
                validate=msg.get('validate', True)
            )
            is_command = True
        except zmq.ZMQError:
            if self.streaming_packages:
                request = self.streaming_packages[self._next_streaming_package]
                self._next_streaming_package += 1
                if self._next_streaming_package == len(self.streaming_packages):
                    self._next_streaming_package = 0
        return request, is_command


    def run(self):
        while not self.stop:
            try:
                request, is_command = self.get_request()
                if not request:
                    continue
                self.publisher_socket.send_json(request.to_dict())
                response = self.ser.send_package(request)
                logger.info("Sending response: sender=%s, destination=%s, length=%s, function=%s",
                            response.sender,
                            response.destination,
                            response.length,
                            response.function)
                if is_command:
                    self.commands_socket.send_json(response.to_dict())
                self.publisher_socket.send_json(response.to_dict())
            except (NoMasterException, ReadException) as ex:
                error_msg = str(ex)
                logger.error(error_msg)
                msg = request.to_dict()
                msg['error'] = error_msg
                if is_command:
                    self.commands_socket.send_json(msg)
                self.publisher_socket.send_json(msg)

            except Exception as ex:
                error = traceback.format_exc()
                logger.error(error)
                self.publisher_socket.send_json({'exception': error})

