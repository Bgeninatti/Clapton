import unittest2
__all__ = ['suite']
from . import suite

mySuit=suite.suite()
runner=unittest2.TextTestRunner()
runner.run(mySuit)
