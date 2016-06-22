import unittest2
from ClaptonBase.serial_instance import SerialInterface
from ClaptonBase.containers import Paquete, Node, MemoInstance
from ClaptonBase.exceptions import ChecksumException, PaqException, \
    InactiveAppException, EncodeError


class PaqueteTestCase(unittest2.TestCase):

    def test_ok(self):
        self.assertIsInstance(Paquete(destino=1, funcion=2, datos=b'\x00\xff'), Paquete)

    def test_init(self):
        with self.assertRaises(AttributeError):
            Paquete()

    def test_encode_fuen_des(self):
        with self.assertRaises(EncodeError):
            Paquete(destino=16, funcion=0)
        with self.assertRaises(EncodeError):
            Paquete(destino=b'a', funcion=0)

    def test_encode_fun_lon(self):
        with self.assertRaises(EncodeError):
            Paquete(destino=2, funcion=10)
        with self.assertRaises(EncodeError):
            Paquete(destino=2, funcion=b'a')

    def test_decode_validate_cs(self):
        with self.assertRaises(ChecksumException):
            Paquete(paq=b'\x01\x42\x00\xff')

    def test_validate_fun(self):
        with self.assertRaises(PaqException):
            p = Paquete(destino=1, funcion=7)

    def test_validate_fun_identify(self):
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=0, datos=b'\xff')

    def test_validate_fun_read(self):
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=1)
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=3)

    def test_validate_fun_write(self):
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=2)
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=4)

    def test_validate_fun_read_app(self):
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=5)

    def test_validate_fun_write_app(self):
        with self.assertRaises(PaqException):
            Paquete(destino=1, funcion=6)


class NodeTestCase(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ser = SerialInterface(mocking=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.ser.stop()

    def test_ok(self):
        n = Node(1, self.ser)
        self.assertIsInstance(n, Node)

    def test_status_ok(self):
        n = Node(1, self.ser)
        n.status = 1
        self.assertIsInstance(n.status, int)

    def test_status_type_error(self):
        with self.assertRaises(TypeError):
            n = Node(1, self.ser)
            n.status = 'b'

    def test_enabled_read_node_true(self):
        n = Node(1, self.ser)
        n.enabled_read_node = True
        self.assertTrue(n.enabled_read_node)

    def test_enabled_read_node_false(self):
        n = Node(1, self.ser)
        n.enabled_read_node = False
        self.assertFalse(n.enabled_read_node)

    def test_enabled_read_node_type_error(self):
        with self.assertRaises(TypeError):
            n = Node(1, self.ser)
            n.enabled_read_node = 'b'

    def test_enabled_read_ram_true(self):
        n = Node(1, self.ser)
        n.enabled_read_ram = True
        self.assertTrue(n.enabled_read_ram)

    def test_enabled_read_ram_false(self):
        n = Node(1, self.ser)
        n.enabled_read_ram = False
        self.assertFalse(n.enabled_read_ram)

    def test_enabled_read_ram_type_error(self):
        with self.assertRaises(TypeError):
            n = Node(1, self.ser)
            n.enabled_read_ram = 'b'

    def test_enabled_read_eeprom_true(self):
        n = Node(1, self.ser)
        n.enabled_read_eeprom = True
        self.assertTrue(n.enabled_read_eeprom)

    def test_enabled_read_eeprom_false(self):
        n = Node(1, self.ser)
        n.enabled_read_eeprom = False
        self.assertFalse(n.enabled_read_eeprom)

    def test_enabled_read_eeprom_type_error(self):
        with self.assertRaises(TypeError):
            n = Node(1, self.ser)
            n.enabled_read_eeprom = 'b'

    def test_enable_eeprom_sector_ok(self):
        pass

    def test_enable_eeprom_sector_type_error(self):
        pass

    def test_disable_eeprom_sector_ok(self):
        pass

    def test_disable_eeprom_sector_type_error(self):
        pass

    def test_enable_ram_sector_ok(self):
        pass

    def test_enable_ram_sector_type_error(self):
        pass

    def test_disable_ram_sector_ok(self):
        pass

    def test_disable_ram_sector_type_error(self):
        pass

    def test_identify_ok(self):
        pass

    def test_identify_type_error(self):
        pass

    def test_identify_inactive_app(self):
        pass

    def test_identify_node_not_exists(self):
        pass

    def test_return_token_ok(self):
        pass

    def test_return_token_inactive_app(self):
        pass

    def test_return_token_token_exception(self):
        pass

    def test_return_token_write_exception(self):
        pass

    def test_return_token_read_exception(self):
        pass

    def test_read_memo_ok(self):
        self.ser._ser.buffer = ['01','22','00','05','d8','10','22','01','02','03','04','05','bf']
        self.ser._ser.buffer.reverse()
        n = Node(1, self.ser)
        memos = n._read_memo(0, 5, 'RAM')
        self.assertEqual(len(memos), 5)
        self.assertTrue(all([isinstance(m, MemoInstance) for m in memos]))
        self.assertEqual(memos[0].valor, b'\x01')
        self.assertEqual(memos[1].valor, b'\x02')
        self.assertEqual(memos[2].valor, b'\x03')
        self.assertEqual(memos[3].valor, b'\x04')
        self.assertEqual(memos[4].valor, b'\x05')

    def test_read_memo_inactive_app(self):
        with self.assertRaises(InactiveAppException):
            n = Node(1, self.ser)
            n.aplicacion_activa = False
            memos = n._read_memo(0, 5, 'RAM')

    def test_read_memo_write_exception(self):
        pass

    def test_read_memo_read_exception(self):
        pass

    def test_write_memo_ok(self):
        pass

    def test_write_memo_encode_exception(self):
        pass

    def test_write_memo_inactive_app(self):
        pass

    def test_write_memo_write_exception(self):
        pass

    def test_write_memo_read_exception(self):
        pass
