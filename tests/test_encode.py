import unittest2
from ClaptonBase import encode
from ClaptonBase.exceptions import Encode

class EncodeTestCase(unittest2.TestCase):

    def test_fuen_des_ok(self):
        self.assertIsInstance(encode.fuen_des(15, 15), str)

    def test_fuen_des_error(self):
        with self.assertRaises(EncodeError):
            encode.fuen_des(16, 16)
        with self.assertRaises(EncodeError):
            encode.fuen_des('a', 'b')

    def test_fun_lon_ok(self):
        self.assertIsInstance(encode.fun_lon(7, 31), str)

    def test_fun_lon_error(self):
        with self.assertRaises(EncodeError):
            encode.fun_lon(8, 32)
        with self.assertRaises(EncodeError):
            encode.fun_lon('a', 'b')

    def test_checksum_ok(self):
        self.assertIsInstance(encode.checksum('\xff\xff'), str)

    def test_checksum_error(self):
        with self.assertRaises(EncodeError):
            encode.checksum(1)

if __name__ == '__main__':
    unittest2.main()
