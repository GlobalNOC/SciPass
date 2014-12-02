import sys
sys.path.append(".")
import pprint
import unittest
import logging
import xmlrunner

import SciPassTest
import SimpleBalancerTest

logging.basicConfig()

if __name__ == '__main__':
    scipasstests = SciPassTest.suite()
    simplebalancertests = SimpleBalancerTest.suite()
    suite = unittest.TestSuite([scipasstests, simplebalancertests])
    xmlrunner.XMLTestRunner(output='test-reports').run(suite)

