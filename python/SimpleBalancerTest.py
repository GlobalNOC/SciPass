import pprint
import ipaddr
import unittest
import xmlrunner
from SimpleBalancer import SimpleBalancer,MaxPrefixlenError

class TestInit(unittest.TestCase):

    def test_no_ops(self):
        balancer = SimpleBalancer()
        self.assertTrue(isinstance(balancer,SimpleBalancer))

    def test_all_ops(self):
        balancer = SimpleBalancer( ignoreSensorLoad       = 1,
                                   ignorePrefixBW         = 1,
                                   maxPrefixes            = 28,
                                   mostSpecificPrefixLen  = 30,
                                   leastSpecificPrefixLen = 26,
                                   sensorLoadMinThresh    = .2,
                                   sensorLoadDeltaThresh  = .1)
        self.assertTrue(isinstance(balancer,SimpleBalancer))


class TestSensorMods(unittest.TestCase):
    def setUp(self):
        self.balancer = SimpleBalancer()

    def test_add_sensor(self):
        #add the first sensor
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        #add a second sensor
        res = self.balancer.addSensor(2)
        self.assertTrue(res == 1)
        res = self.balancer.addSensor(1)
        self.assertFalse(res == 1)
        res = self.balancer.addSensor(None)
        self.assertFalse(res == 1)
        load = self.balancer.getSensorLoad()
        self.assertTrue(load[1] == 0)
        self.assertTrue(load[2] == 0)

    def test_set_sensor_load(self):
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        res = self.balancer.setSensorLoad(1,.1)
        self.assertTrue(res == 1)
        load = self.balancer.getSensorLoad()
        self.assertTrue(load[1] == 0.1)
        res = self.balancer.setSensorLoad(2,.1)
        self.assertTrue(res == 0)
        res = self.balancer.setSensorLoad(1,2)
        self.assertTrue(res == 0)

    def test_set_sensor_status(self):
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        res = self.balancer.setSensorStatus(1,0)
        self.assertTrue(res == 1)
        status = self.balancer.getSensorStatus(1)
        self.assertTrue(status == 0)
        res = self.balancer.setSensorStatus(1,1)
        status = self.balancer.getSensorStatus(1)
        self.assertTrue(status == 1)
        status = self.balancer.getSensorStatus(2)
        self.assertTrue(status == -1)


class TestPrefix(unittest.TestCase):

    def addHandler(self, sensor, prefix):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix

    def delHandler(self, sensor, prefix):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix

    def moveHandler(self, old_sensor,sensor, prefix):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix
        self.old_sensor = old_sensor

    def setUp(self):
        self.balancer = SimpleBalancer()
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        res = self.balancer.addSensor(2)
        self.assertTrue(res == 1)
        self.handler_fired = 0
        self.sensor = None
        self.prefix = None
        self.old_sensor = None
        self.addPrefixHandler = self.addHandler
        self.delPrefixHandler = self.delHandler
        self.movePrefixHandler= self.moveHandler
        self.balancer.registerAddPrefixHandler(self.addPrefixHandler)
        self.balancer.registerDelPrefixHandler(self.delPrefixHandler)
        self.balancer.registerMovePrefixHandler(self.movePrefixHandler)

    def tearDown(self):
        self.handler_fired = 0
        self.sensor = None
        self.prefix = None
        self.old_sensor = None


    def test_split_prefix_for_sensors(self):
        net = ipaddr.IPv4Network("10.0.0.0/8")
        prefixList = self.balancer.splitPrefixForSensors(net,4)
        self.assertTrue(len(prefixList) == 4)
        self.assertTrue(prefixList[0] == ipaddr.IPv4Network("10.0.0.0/10"))
        self.assertTrue(prefixList[1] == ipaddr.IPv4Network("10.64.0.0/10"))
        self.assertTrue(prefixList[2] == ipaddr.IPv4Network("10.128.0.0/10"))
        self.assertTrue(prefixList[3] == ipaddr.IPv4Network("10.192.0.0/10"))    
        
    def test_split_prefix_for_sensors_large(self):
        net = ipaddr.IPv4Network("10.0.0.0/8")
        prefixList = self.balancer.splitPrefixForSensors(net,100)
        self.assertTrue(len(prefixList) == 128)

    def test_add_sensor_prefix(self):
        self.balancer.registerAddPrefixHandler(self.addPrefixHandler)
        net = ipaddr.IPv4Network("10.0.0.0/10")
        self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        
    def test_del_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        #clear them out
        self.handler = 0
        self.sensor = None
        self.prefix = None
        #do the del
        res = self.balancer.delSensorPrefix(1,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)

    def test_move_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        #clear them out, make sure we see the del
        self.handler = 0
        self.sensor = None
        self.prefix = None
        #do the move
        res = self.balancer.moveSensorPrefix(1,2,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 2)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.old_sensor == 1)

    def test_set_prefix_bw(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,500,500)
        self.assertTrue(res == 1)
        prefixBW = self.balancer.getPrefixes()
        self.assertTrue(prefixBW[net] == 1000)
        net2 = ipaddr.IPv4Network("172.16.0.0/16")
        res = self.balancer.setPrefixBW(net2, 1000, 1000)
        self.assertTrue(res == 0)
        prefixBW = self.balancer.getPrefixes()
        self.assertTrue(prefixBW.has_key(net2) == False)
        self.assertTrue(prefixBW[net] == 1000)

    def test_split_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,500,500)
        self.assertTrue(res == 1)
        res = self.balancer.splitSensorPrefix(1,net)
        self.assertTrue(res == 1)
        prefixBW = self.balancer.getPrefixes()
        self.assertTrue(len(prefixBW) == 2)
        newnet = ipaddr.IPv4Network("10.0.0.0/11")
        newnet2 = ipaddr.IPv4Network("10.32.0.0/11")
        self.assertTrue(prefixBW[newnet] == 500.0)
        self.assertTrue(prefixBW[newnet2] == 500.0)

    def test_split_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/11")
        res = self.balancer.splitPrefix(net)
        self.assertTrue(len(res) == 2)
        self.assertTrue(res[0] == ipaddr.IPv4Network("10.0.0.0/12"))
        self.assertTrue(res[1] == ipaddr.IPv4Network("10.16.0.0/12"))

        net = ipaddr.IPv4Network("10.0.0.0/29")
        self.assertRaises(MaxPrefixlenError, lambda: list(self.balancer.splitPrefix(net)))

    def test_get_prefix_sensor(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        sensor = self.balancer.getPrefixSensor(net)
        self.assertTrue(sensor == 1)
        net2 = ipaddr.IPv4Network("10.230.0.0/10")
        sensor = self.balancer.getPrefixSensor(net2)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(sensor)
        self.assertTrue(sensor == None)

    def test_get_largest_prefix(self):
        net = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net2,0)
        self.assertTrue(res == 1)
        largest = self.balancer.getLargestPrefix(1)
        self.assertTrue(largest == net2)
        largest = self.balancer.getLargestPrefix(2)
        self.assertTrue(largest == None)
        largest = self.balancer.getLargestPrefix(5)
        self.assertTrue(largest == None)

class TestBalance(unittest.TestCase):

    def test_get_est_load(self):
        self.balancer = SimpleBalancer()
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        res = self.balancer.addSensor(2)
        self.assertTrue(res == 1)
        net = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,500,500)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,500,500)
        self.assertTrue(res == 1)
        net3 = ipaddr.IPv4Network("10.0.0.0/8")
        percentTotal = self.balancer.getEstLoad(1,net3)
        self.assertTrue(percentTotal == 3.2)

    def test_balance_by_ip(self):
        self.balancer = SimpleBalancer()
        res = self.balancer.addSensor(1)
        self.assertTrue(res == 1)
        res = self.balancer.addSensor(2)
        self.assertTrue(res == 1)
        et = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addSensorPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addSensorPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,500,500)
        self.assertTrue(res == 1)
        self.balancer.balanceByIp( )
        

SimpleBalancerSuite = unittest.TestSuite()
SimpleBalancerSuite.addTest(TestInit('test_no_ops'))
SimpleBalancerSuite.addTest(TestInit('test_all_ops'))
SimpleBalancerSuite.addTest(TestSensorMods('test_add_sensor'))
SimpleBalancerSuite.addTest(TestSensorMods('test_set_sensor_load'))
SimpleBalancerSuite.addTest(TestSensorMods('test_set_sensor_status'))
SimpleBalancerSuite.addTest(TestPrefix('test_split_prefix_for_sensors'))
SimpleBalancerSuite.addTest(TestPrefix('test_split_prefix_for_sensors_large'))
SimpleBalancerSuite.addTest(TestPrefix('test_add_sensor_prefix'))
SimpleBalancerSuite.addTest(TestPrefix('test_del_sensor_prefix'))
SimpleBalancerSuite.addTest(TestPrefix('test_move_sensor_prefix'))
SimpleBalancerSuite.addTest(TestPrefix('test_set_prefix_bw'))
SimpleBalancerSuite.addTest(TestPrefix('test_split_sensor_prefix'))
SimpleBalancerSuite.addTest(TestPrefix('test_split_prefix'))
SimpleBalancerSuite.addTest(TestPrefix('test_get_prefix_sensor'))
SimpleBalancerSuite.addTest(TestPrefix('test_get_largest_prefix'))
SimpleBalancerSuite.addTest(TestBalance('test_get_est_load'))
#unittest.TextTestRunner(verbosity=2).run(SimpleBalancerSuite)
unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
