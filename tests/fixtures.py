import os
import mock
import serial
import pytest
from ClaptonBase.cfg import READ_FUNCTIONS, WRITE_FUNCTIONS
from ClaptonBase.containers import Node, Package, MemoryContainer
from ClaptonBase.exceptions import ReadException, WriteException
from ClaptonBase.serial_interface import SerialInterface

@pytest.fixture
def mock_read():

    class MockRead(object):

        def __init__(self, bytes_chain):
            self.bytes_chain = bytes_chain

        def __call__(self, n=1):
            print(n)
            result = self.bytes_chain[:n]
            self.bytes_chain = self.bytes_chain[n:]
            print(result)
            return result

    return MockRead



@pytest.fixture
def mocked_serial():

    class PortMock(mock.Mock):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.ReadByte = mock.Mock()

    ser = SerialInterface()
    ser._ser = mock.Mock(spec_set=serial.Serial)
    return ser

@pytest.fixture
def ser_raises_write_exception():
    class SerialWriteException(object):

        def __init__(self, *args, im_master=True, **kwargs):
            self.im_master = im_master

        def send_package(self, package):
            raise WriteException

    return SerialWriteException()

@pytest.fixture
def ser_raises_read_exception():
    class SerialReadException(object):

        def __init__(self, *args, im_master=True, **kwargs):
            self.im_master = im_master

        def send_package(self, package):
            raise ReadException

    return SerialReadException()

@pytest.fixture
def ser_answer_all():
    class SerialAnswerAll(object):

        def send_package(self, package):
            if package.function == 0:
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function,
                               data=os.urandom(8),
                               validate=False)
            elif package.function in READ_FUNCTIONS:
                length = package.data[1]
                data = os.urandom(length)
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function,
                               data=data,
                               validate=False)
            elif package.function in WRITE_FUNCTIONS:
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function,
                               validate=False)
            elif package.function == 7:
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function,
                               validate=False)
    return SerialAnswerAll()


@pytest.fixture
def memo_instance():
    return MemoryContainer(
        node=0,
        instance='RAM',
        start=123,
        timestamp=12345436234.0,
        data=b'\x01\x02\x03\x04\x05\x06'
    )


@pytest.fixture
def node():
    return Node(1, ser=SerialInterface())


@pytest.fixture
def virtual_node():
    return Node(1, ser=ser_answer_all())
