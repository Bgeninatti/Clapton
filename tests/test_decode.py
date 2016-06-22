import unittest2
from ClaptonBase import decode
from ClaptonBase.exceptions import DecodeError


class DecodeTestCase(unittest2.TestCase):

    def test_fuen_des_ok(self):
        self.assertIsInstance(decode.fuen_des(b'\xff'), tuple)

    def test_fuen_des_error(self):
        with self.assertRaises(DecodeError):
            decode.fuen_des(b'\xff\xff')
        with self.assertRaises(DecodeError):
            decode.fuen_des(1000)

    def test_fun_lon_ok(self):
        self.assertIsInstance(decode.fun_lon(b'\xff'), tuple)

    def test_fun_lon_error(self):
        with self.assertRaises(DecodeError):
            decode.fun_lon(b'\xff\xff')
        with self.assertRaises(DecodeError):
            decode.fun_lon(1000)

    def test_validate_cs_true(self):
        self.assertTrue(decode.validate_cs(b'\x01\x42\x00\xff\xbe'))

    def test_validate_cs_false(self):
        self.assertFalse(decode.validate_cs(b'\x01\x42\x00\xff'))

    def test_validate_cs_error(self):
        with self.assertRaises(DecodeError):
            decode.validate_cs(1000)
