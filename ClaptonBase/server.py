from threading import Thread

import zmq
import struct
import traceback

from .utils import get_logger
from .containers import MemoryContainer, Package


logger = get_logger('server')


class TKLanServer(Thread):
    """
    This class provides declarations of the main functions in \
    the Clapton Server architecture,
    """
    def __init__(self,
                 serial_instance,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)

        # serial connection
        self.ser = serial_instance

        # Inicio context para ZMQ
        self.context = zmq.Context()

        self.publisher_port = publisher_port
        self.publisher_socket = None

        # Bandera de parada para los Threads
        self.stop = False
        self.setup()
        logger.info("TKLan Server initialized")

    def setup(self):
        try:
            self.setup_sockets()
            self.setup_threads()
        except zmq.ZMQError as error:
            self.stop_sockets()
            raise error

    def setup_sockets(self):
        """
        Initialize the zmq sockets.
        """
        logger.info("Starting publisher socket")
        self.publisher_socket = self.context.socket(zmq.PUB)
        self.publisher_socket.bind(
            "tcp://*:{0}".format(self.publisher_port))


    def setup_threads(self):
        """
        Start the threads of your server.
        If you want to run aditional threads that runs \
        you should extend this function to start them::

            class YourCustomServer(BaseServer):

                def start_threads(self):
                    super().start_threads()
                    self.your_custom_thread.start()

                def stop_threads(self):
                    super().stop_threads()
                    self.your_custom_thread.join()

        Be aware to also stop your custom threads in \
        :func:`stop_threads`
        """
        logger.info("Starting threads")
        pass

    def join(self, *args, **kwargs):
        """
        Stop the server. You shouldn't extend this function.
        """
        self.stop = True
        self.stop_threads()
        self.stop_sockets()
        logger.info("Base server stoped")
        super().join(*args, **kwargs)

    def stop_threads(self):
        """
        Stop the threads of your server.
        If you want to run aditional threads and you alredy registered to be started :func:`start_threads`
        you should extend this function to stop them::

            class YourCustomServer(BaseServer):

                ...

                def start_threads(self):
                    super().start_threads()
                    self.your_custom_thread.start()

                def stop_threads(self):
                    super().stop_threads()
                    self.your_custom_thread.join()
        """
        pass

    def stop_sockets(self):
        """
        Stop the zmq publisher and commands sockets.
        """
        logger.info("Attempt to stop publisher socket")
        self.publisher_socket.close()
        self.context.term()
        logger.info("Sockets stoped")

    def handle_exception(self, exception):
        pass

    def run(self):
        while not self.stop:
            try:
                if self.ser.im_master:
                    self.run_when_master()
                else:
                    self.run_when_slave()
                self.run_always()
            except Exception as error:
                tb = traceback.format_exc()
                logger.critical(tb)
                self.handle_exception(tb)
                tb = traceback.format_tb(error.__traceback__)
                logger.critical(''.join(tb))
                self.handle_exception(''.join(tb))

