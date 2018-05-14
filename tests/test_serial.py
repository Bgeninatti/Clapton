import os
import time

import pytest
from ClaptonBase import decode
from ClaptonBase.containers import Package
from ClaptonBase.exceptions import (ChecksumException, NoMasterException,
                                    ReadException, WriteException)


class TestSerial(object):

    def test_start_stop(self, mocked_serial):
        assert not mocked_serial._connection_thread.is_alive()
        mocked_serial._ser.isOpen.return_value = True
        mocked_serial.start()
        assert mocked_serial._connection_thread.is_alive()
        assert mocked_serial.isOpen()
        mocked_serial.stop()
        assert mocked_serial._stop
        time.sleep(1)
        assert not mocked_serial._connection_thread.is_alive()

    @pytest.mark.parametrize("return_value", [True, False])
    def test_is_open(self, mocked_serial, return_value):
        mocked_serial._ser.isOpen.return_value = return_value
        assert mocked_serial.isOpen() == return_value

    def test_do_connect(self):
        pass

    @pytest.mark.parametrize("length,bytes_chain", [
        (3, b'\x01\x0f'),
        (3, b'\xff\x01\xce'),
        (3, b'\x05\x00\xfb'),
        (5, b',0\x05\x14\x8b'),
        (6, b'\x9eX\x00\xff\xff\x0c'),
    ])
    def test_get_package_from_length(self, mocked_serial, length, bytes_chain):
        mocked_serial._ser.read.side_effect = lambda n: bytes_chain[0:n if n else 1]
        if length < len(bytes_chain):
            with pytest.raises(ReadException):
                mocked_serial.get_package_from_length(length)
        elif not decode.validate_checksum(bytes_chain):
            with pytest.raises(ReadException):
                mocked_serial.get_package_from_length(length)
        else:
            rta = mocked_serial.get_package_from_length(length)
            assert isinstance(rta, Package)

    @pytest.mark.parametrize("bytes_chain", [
        b'\n\x18\x00\x00\x00\x00\x00\x00\xde',
        b'\x05\x00\xfb',
        b',0\x05\x14\x8b',
        b'\x9eX\x00\xff\xff\x0c',
        b'\xa2p\t\x10\xd5',
        b'L\x98\xf0\xe3\xc1\x88',
        b';\xe0\xe5',
    ])
    def test_get_package_on_the_fly_ok(self, mock_read, mocked_serial, bytes_chain):
        mocked_serial._ser.read.side_effect = mock_read(bytes_chain)
        rta = mocked_serial.get_package_on_the_fly()
        assert isinstance(rta, Package)

    @pytest.mark.parametrize("bytes_chain", [
        b'-P\x076',
        b'&P\x04?\x87w\xec\rq\xad',
        b'\x18X\x02\x87\xdd',
        b'\x1a\x07\x8f',
        b'\x11\x00\xb2lO\x13\xf5H\x15\xcd',
    ])
    def test_get_package_on_the_fly_checksum_error(self, mock_read, mocked_serial, bytes_chain):
        mocked_serial._ser.read.side_effect = mock_read(bytes_chain)
        with pytest.raises(ChecksumException):
            mocked_serial.get_package_on_the_fly()

    @pytest.mark.parametrize("bytes_chain", [
        b'\x01',
        b'\xff',
        b'',
    ])
    def test_get_package_on_the_fly_read_exception(self, mock_read, mocked_serial, bytes_chain):
        mocked_serial._ser.read.side_effect = mock_read(bytes_chain)
        with pytest.raises(ReadException):
            mocked_serial.get_package_on_the_fly()

    @pytest.mark.parametrize("question,answer", [
        (Package(bytes_chain=b'%T)\xfe\x01I\x10\xf5g\x9d\x0fy\x85'),
         Package(bytes_chain=b'R^\xe7~\xfe\x19\xfb\xcafn\xb2v\x92\xa7]\xb5Qw')),
        (Package(bytes_chain=b'\x01\x00\xff'),
         Package(bytes_chain=b'\x10\x14\xbd\xb3\x97\xb6-\xa6X\xdd<\xfe\xdd')),
        (Package(bytes_chain=b'\xac\x92\x9a\x9b\xec\x96\xc7\xf4\xaf\xa1x\x88'),
         Package(bytes_chain=b'\xca\x92\xa7\x99\x881X\x15\xc7\xef\x9c\xec')),
    ])
    def test_send_package_ok(self, mock_read, mocked_serial, question, answer):
        mocked_serial._ser.read.side_effect = mock_read(question.bytes_chain + answer.bytes_chain)
        mocked_serial.im_master = True
        rta = mocked_serial.send_package(question)
        assert rta.bytes_chain == answer.bytes_chain

    def test_send_package_raises_no_master_exception(self, mocked_serial):
        dummy_package = Package(destination=1, function=0)
        mocked_serial.im_master = False
        with pytest.raises(NoMasterException):
            mocked_serial.send_package(dummy_package)

    @pytest.mark.parametrize("package", [
         Package(bytes_chain=b'%T)\xfe\x01I\x10\xf5g\x9d\x0fy\x85'),
         Package(bytes_chain=b'R^\xe7~\xfe\x19\xfb\xcafn\xb2v\x92\xa7]\xb5Qw'),
         Package(bytes_chain=b'\x01\x00\xff'),
         Package(bytes_chain=b'\x10\x14\xbd\xb3\x97\xb6-\xa6X\xdd<\xfe\xdd'),
         Package(bytes_chain=b'\xac\x92\x9a\x9b\xec\x96\xc7\xf4\xaf\xa1x\x88'),
         Package(bytes_chain=b'\xca\x92\xa7\x99\x881X\x15\xc7\xef\x9c\xec'),
    ])
    def test_send_package_raises_read_exception(self,
                                                mock_read,
                                                mocked_serial,
                                                package):
        mocked_serial._ser.read.side_effect = mock_read(package.bytes_chain[1:])
        mocked_serial.im_master = True
        with pytest.raises(ReadException):
            mocked_serial.send_package(package)

    @pytest.mark.parametrize("package,answer", [
        (Package(bytes_chain=b'%T)\xfe\x01I\x10\xf5g\x9d\x0fy\x85'),
         os.urandom(1)),
        (Package(bytes_chain=b'R^\xe7~\xfe\x19\xfb\xcafn\xb2v\x92\xa7]\xb5Qw'),
         os.urandom(1)),
        (Package(bytes_chain=b'\x01\x00\xff'), os.urandom(1)),
        (Package(bytes_chain=b'\x10\x14\xbd\xb3\x97\xb6-\xa6X\xdd<\xfe\xdd'),
         os.urandom(1)),
        (Package(bytes_chain=b'\xac\x92\x9a\x9b\xec\x96\xc7\xf4\xaf\xa1x\x88'),
         os.urandom(1)),
        (Package(bytes_chain=b'\xca\x92\xa7\x99\x881X\x15\xc7\xef\x9c\xec'),
         os.urandom(1)),
    ])
    def test_send_package_raises_write_exception(self,
                                                 mock_read,
                                                 mocked_serial,
                                                 package,
                                                 answer):
        mocked_serial._ser.read.side_effect = mock_read(package.bytes_chain + answer)
        mocked_serial.im_master = True
        with pytest.raises(WriteException):
            mocked_serial.send_package(package)

    def test_listen_packages(self):
        pass
