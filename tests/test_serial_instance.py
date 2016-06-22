import unittest2
from ClaptonBase.serial_instance import SerialInterface
from ClaptonBase.exceptions import SerialConfigError, NoMasterException, \
    ReadException, WriteException
from ClaptonBase.containers import Paquete
from ClaptonBase.cfg import INSTANT_RECONECT_TRIES

class SerialInstanceTestCase(unittest2.TestCase):

    def test_00_stop_ok(self):
        ser = SerialInterface(mocking=True)
        ser.start()
        self.assertIsNone(ser.stop())

    def test_01_initial_conect_error(self):
        with self.assertRaises(SerialConfigError):
            ser = SerialInterface(serial_port='puerto')
            ser._do_connect()
        ser.stop()

    def test_02_do_reconect_ok(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.ser_seted.clear()
        ser._do_reconect()
        self.assertTrue(ser.ser_seted.isSet())
        ser.stop()

    def test_03_do_reconect_instant_reconect(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.ser_seted.clear()
        ser._ser.raise_serial_error = 1
        ser._do_reconect()
        self.assertTrue(ser.ser_seted.isSet())
        ser.stop()

    def test_04_do_reconect_long_reconect(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.ser_seted.clear()
        ser._ser.raise_serial_error = INSTANT_RECONECT_TRIES + 1
        ser._do_reconect()
        self.assertTrue(ser.ser_seted.isSet())
        ser.stop()

    def test_05_send_paq_ok(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.im_master = True
        paq = Paquete(origen=0, destino=1, funcion=1, datos=b'\x00\x05')
        ser._ser.buffer = ['01','22','00','05','d8','10','22','01','02','03','04','05','bf']
        ser._ser.buffer.reverse()
        rta, echo = ser.send_paq(paq)
        self.assertEqual(paq.to_write, echo.to_write)
        self.assertIsInstance(rta, Paquete)
        ser.stop()

    def test_06_send_paq_no_master(self):
        with self.assertRaises(NoMasterException):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser.im_master = False
            paq = Paquete(origen=0, destino=1, funcion=1, datos=b'\x00\x05')
            rta, echo = ser.send_paq(paq)
        ser.stop()

    def test_07_send_paq_type_error(self):
        with self.assertRaises(TypeError):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser.im_master = True
            rta, echo = ser.send_paq(1234)
        ser.stop()

    def test_08_send_paq_read_exception(self):
        with self.assertRaises(ReadException):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser.im_master = True
            paq = Paquete(origen=0, destino=1, funcion=1, datos=b'\x00\x05')
            rta, echo = ser.send_paq(paq)
        ser.stop()

    def test_09_send_paq_write_exception(self):
        with self.assertRaises(WriteException):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser.im_master = True
            paq = Paquete(origen=0, destino=1, funcion=1, datos=b'\x00\x05')
            ser._ser.buffer = ['01','22','00','05','d8']
            ser._ser.buffer.reverse()
            rta, echo = ser.send_paq(paq)
        ser.stop()

    def test_10_read_paq_ok(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.im_master = False
        ser._ser.buffer = ['01','22','00','05','d8','10','22','01','02','03','04','05','bf']
        ser._ser.buffer.reverse()
        gen = ser.read_paq()
        paq = next(gen)
        self.assertIsInstance(paq, Paquete)
        ser.stop()

    def test_11_read_paq_read_exception(self):
        with self.assertRaises(ReadException):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser.im_master = False
            ser._ser.raise_serial_error = 1
            gen = ser.read_paq()
            paq = next(gen)
        ser.stop()

    def test_12_check_master_true(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser.check_master()
        self.assertTrue(ser.im_master)
        ser.stop()

    def test_13_check_master_false(self):
        ser = SerialInterface(mocking=True)
        ser._do_connect()
        ser._ser.buffer = ['01','22','00','05','d8','10','22','01','02','03','04','05','bf']
        ser._ser.buffer.reverse()
        ser.check_master()
        self.assertFalse(ser.im_master)
        ser.stop()

    def test_14_check_master_read_exception(self):
        with self.assertRaises(ReadException):
            ser = SerialInterface(mocking=True)
            ser._do_connect()
            ser._ser.raise_serial_error = 1
            ser.check_master()
        ser.stop()
