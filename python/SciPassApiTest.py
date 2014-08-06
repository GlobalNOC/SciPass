import pprint
import unittest
import logging
import xmlrunner
import os
from SciPassApi import SciPassApi

logging.basicConfig()


class TestInit(unittest.TestCase):

    def test_no_ops(self):
        api = SciPassApi( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass.xml"
                          )
        self.assertTrue(isinstance(api,SciPassApi))




def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInit)
    return suite
