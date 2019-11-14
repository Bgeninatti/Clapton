import zmq
from . import cfg


class TKLanClient:

    def __init__(self, ip, port=cfg.COMMANDS_PORT):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.ip = ip
        self.port = port
        self.socket.connect('tcp://{}:{}'.format(ip, port))

    def send_package(self, package):
        self.socket.send_json(package.to_dict())

    def recv_response(self):
        return self.socket.recv_json(zmq.NOBLOCK)

class Subscriber:

    def __init__(self, ip, port=cfg.PUBLISHER_PORT):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.ip = ip
        self.port = port
        self.socket.connect('tcp://{}:{}'.format(ip, port))
        # For now just suscribe to all
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')

    def listen(self):
        return self.socket.recv_json(zmq.NOBLOCK)
