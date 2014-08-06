import unittest
import SimpleBalancerTest
import SciPassApiTest
import xmlrunner
import logging

SimpleBalancerSuite = SimpleBalancerTest.suite()
print "SimpleBalancer Suite: " + str(SimpleBalancerSuite)
SciPassApiSuite = SciPassApiTest.suite()
print "SciPassApi Suite: " + str(SciPassApiSuite)

FullSuite = unittest.TestSuite()
FullSuite.addTests(SimpleBalancerSuite)
FullSuite.addTests(SciPassApiSuite)

if __name__ == '__main__':
    runner = xmlrunner.XMLTestRunner("test-reports")
    runner.run(FullSuite)
    
    #unittest.main(module=FullSuite)
    #unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
