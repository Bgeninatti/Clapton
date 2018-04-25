import os

import pytest
from ClaptonBase.cfg import READ_FUNCTIONS, WRITE_FUNCTIONS
from ClaptonBase.containers import Node, Package
from ClaptonBase.exceptions import ReadException, WriteException
from ClaptonBase.serial_interface import SerialInterface


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
                               data=os.urandom(8))
            elif package.function in READ_FUNCTIONS:
                length = package.data[1]
                data = os.urandom(length)
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function,
                               data=data)
            elif package.function in WRITE_FUNCTIONS:
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function)
            elif package.function == 7:
                return Package(sender=package.destination,
                               destination=package.sender,
                               function=package.function)
    return SerialAnswerAll()


@pytest.fixture
def node():
    return Node(1, ser=SerialInterface())


@pytest.fixture
def virtual_node():
    return Node(1, ser=ser_answer_all())
