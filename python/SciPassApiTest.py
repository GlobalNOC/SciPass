import pprint
import unittest
import logging
import xmlrunner
from SciPassApi import SciPassApi

logging.basicConfig()


class TestInit(unittest.TestCase):

    def test_no_ops(self):
        api = SciPassApi( logger = logging.getLogger(__name__))
        self.assertTrue(isinstance(api,SciPassApi))




def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInit)
    return suite
