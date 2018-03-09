import unittest
from ClaptonBase import encode
from ClaptonBase.exceptions import EncodeError

class EncodeTestCase(unittest.TestCase):

    def test_fuen_des_ok(self):
        self.assertEqual(encode.fuen_des(15, 15), b'\xff')

    def test_fuen_des_error(self):
        with self.assertRaises(EncodeError):
            encode.fuen_des(16, 16)
        with self.assertRaises(EncodeError):
            encode.fuen_des(b'a', b'b')

    def test_fun_lon_ok(self):
        self.assertEqual(encode.fun_lon(7, 31), b'\xff')

    def test_fun_lon_error(self):
        with self.assertRaises(EncodeError):
            encode.fun_lon(8, 32)
        with self.assertRaises(EncodeError):
            encode.fun_lon(b'a', b'b')

    def test_checksum_ok(self):
        self.assertEqual(encode.checksum(b'\xff\xff'), b'\x02')

    def test_checksum_error(self):
        with self.assertRaises(EncodeError):
            encode.checksum(1)
