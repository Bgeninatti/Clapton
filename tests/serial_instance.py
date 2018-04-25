import pytest

from ClaptonBase.containers import Package
from ClaptonBase.exceptions import (NoMasterException, ReadException,
                                    SerialConfigError, WriteException)
from ClaptonBase.serial import SerialInterface


class TestSerial(object):


