import unittest2
from .test_decode import DecodeTestCase
from .test_encode import EncodeTestCase
from .test_containers import PaqueteTestCase, NodeTestCase
from .test_serial_instance import SerialInstanceTestCase

def suite():
    test_suite = unittest2.TestSuite()
    test_suite.addTest(unittest2.makeSuite(DecodeTestCase))
    test_suite.addTest(unittest2.makeSuite(EncodeTestCase))
    test_suite.addTest(unittest2.makeSuite(PaqueteTestCase))
    test_suite.addTest(unittest2.makeSuite(NodeTestCase))
    test_suite.addTest(unittest2.makeSuite(SerialInstanceTestCase))
    return test_suite
