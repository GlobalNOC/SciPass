import sys
sys.path.append(".")
import pprint
import ipaddr
import unittest
import xmlrunner
import logging
from SimpleBalancer import SimpleBalancer,MaxPrefixlenError
from collections import defaultdict

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
                                   ipv6MostSpecificPrefixLen = 64,
                                   ipv6LeastSpecificPrefixLen = 48,
                                   sensorLoadMinThresh    = .2,
                                   sensorLoadDeltaThresh  = .1)
        self.assertTrue(isinstance(balancer,SimpleBalancer))


class TestSensorMods(unittest.TestCase):
    def setUp(self):
        self.balancer = SimpleBalancer()

    def test_add_sensor(self):
        #add the first sensor
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        #add a second sensor
        sensors2 = defaultdict(list)
        sensors2[3] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[4] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr2",
                                            "sensors": sensors2})
        self.assertTrue(res == 1)
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertFalse(res == 1)
        res = self.balancer.addSensorGroup(None)
        self.assertFalse(res == 1)
        load = self.balancer.getSensorLoad()
        self.assertTrue(load[1] == 0)
        self.assertTrue(load[2] == 0)

    def test_set_sensor_load(self):
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        res = self.balancer.setSensorLoad(1,.1)
        self.assertTrue(res == 1)
        load = self.balancer.getSensorLoad()
        self.assertTrue(load[1] == 0.1)
        res = self.balancer.setSensorLoad(3,.1)
        self.assertTrue(res == 0)
        res = self.balancer.setSensorLoad(1,2)
        self.assertTrue(res == 0)

    def test_set_sensor_status(self):
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        res = self.balancer.setSensorStatus(1,0)
        self.assertTrue(res == 1)
        status = self.balancer.getSensorStatus(1)
        self.assertTrue(status == 0)
        res = self.balancer.setSensorStatus(1,1)
        status = self.balancer.getSensorStatus(1)
        self.assertTrue(status == 1)
        status = self.balancer.getSensorStatus(3)
        self.assertTrue(status == -1)


class TestPrefix(unittest.TestCase):

    def addHandler(self, sensor, prefix, priority):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix
        self.priority = priority

    def delHandler(self, sensor, prefix, priority):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix
        self.priority = priority

    def moveHandler(self, old_sensor,sensor, prefix, priority):
        self.handler_fired = 1
        self.sensor = sensor
        self.prefix = prefix
        self.old_sensor = old_sensor
        self.priority = priority

    def setUp(self):
        self.balancer = SimpleBalancer()
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        sensors2 = defaultdict(list)
        sensors2[1] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[2] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors2}) 
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
        
        net = ipaddr.IPv6Network("2001:0DB8::/48")
        prefixList = self.balancer.splitPrefixForSensors(net,4)
        self.assertTrue(prefixList[0] == ipaddr.IPv6Network("2001:db8::/50"))
        self.assertTrue(prefixList[1] == ipaddr.IPv6Network("2001:db8:0:4000::/50"))
        self.assertTrue(prefixList[2] == ipaddr.IPv6Network("2001:db8:0:8000::/50"))
        self.assertTrue(prefixList[3] == ipaddr.IPv6Network("2001:db8:0:c000::/50"))

    def test_split_prefix_for_sensors_large(self):
        net = ipaddr.IPv4Network("10.0.0.0/8")
        prefixList = self.balancer.splitPrefixForSensors(net,100)
        self.assertTrue(len(prefixList) == 128)
        
        net = ipaddr.IPv6Network("2001:0DB8::/48")
        prefixList = self.balancer.splitPrefixForSensors(net,100)
        self.assertTrue(len(prefixList) == 128)

    def test_add_sensor_prefix(self):
        self.balancer.registerAddPrefixHandler(self.addPrefixHandler)
        net = ipaddr.IPv4Network("10.0.0.0/10")
        self.balancer.addGroupPrefix(1,net,100)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 500)

        net = ipaddr.IPv6Network("2001:0DB8::/48")
        self.balancer.addGroupPrefix(1,net,100)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        logging.error(self.priority)
        self.assertTrue(self.priority == 600)

    def test_del_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net,100)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 500)
        #clear them out
        self.handler = 0
        self.sensor = None
        self.prefix = None
        self.priority = None
        #do the del
        res = self.balancer.delGroupPrefix(1,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 500)

        net = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net,100)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 600)
        #cleam them out
        self.handler = 0
        self.sensor = None
        self.prefix = None
        self.priority = None
        #do the del
        res = self.balancer.delGroupPrefix(1,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 600)

        
    def test_move_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 500)
        #clear them out, make sure we see the del
        self.handler = 0
        self.sensor = None
        self.prefix = None
        self.priority == 0
        #do the move
        res = self.balancer.moveGroupPrefix(1,2,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 2)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.old_sensor == 1)
        self.assertTrue(self.priority == 500)


        net = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(2,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 2)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.priority == 600)
        #clear them out
        self.handler = 0
        self.sensor = None
        self.prefix = None
        self.priority == 0
        #do the move
        res = self.balancer.moveGroupPrefix(2,1,net)
        self.assertTrue(res == 1)
        self.assertTrue(self.handler_fired == 1)
        self.assertTrue(self.sensor == 1)
        self.assertTrue(self.prefix == net)
        self.assertTrue(self.old_sensor == 2)
        self.assertTrue(self.priority == 600)

    def test_set_prefix_bw(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,500,500)
        self.assertTrue(res == 1)
        prefixBW = self.balancer.getPrefixes()
        #note setPrefixBW takes in bytes so for bits
        # we multiply by 8
        self.assertTrue(prefixBW[net] == 8 * 1000)
        net2 = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.setPrefixBW(net2, 1000, 1000)
        self.assertTrue(res == 0)
        prefixBW = self.balancer.getPrefixes()
        self.assertTrue(prefixBW.has_key(net2) == False)
        self.assertTrue(prefixBW[net] == 8 * 1000)

        
    def test_split_sensor_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        net2 = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.splitSensorPrefix(1,net)
        self.assertTrue(res == 1)
        res = self.balancer.splitSensorPrefix(1,net2)
        self.assertTrue(res == 1)
        prefixBW = self.balancer.getPrefixes()
        self.assertTrue(len(prefixBW) == 4)
        newnet = ipaddr.IPv4Network("10.0.0.0/11")
        newnet2 = ipaddr.IPv4Network("10.32.0.0/11")
        newnet3 = ipaddr.IPv6Network("2001:db8::/49")
        newnet4 = ipaddr.IPv6Network("2001:db8:0:8000::/49")
        #remember that we set it via bytes and this will be returned
        #as bits persec
        self.assertTrue(prefixBW[newnet] == 8 * 5000000.0)
        self.assertTrue(prefixBW[newnet2] == 8 * 5000000.0)
        self.assertTrue(prefixBW[newnet3] == 8 * 5000000.0)
        self.assertTrue(prefixBW[newnet4] == 8 * 5000000.0)
        
    def test_split_prefix(self):
        net = ipaddr.IPv4Network("10.0.0.0/11")
        res = self.balancer.splitPrefix(net)
        self.assertTrue(len(res) == 2)
        self.assertTrue(res[0] == ipaddr.IPv4Network("10.0.0.0/12"))
        self.assertTrue(res[1] == ipaddr.IPv4Network("10.16.0.0/12"))

        net = ipaddr.IPv4Network("10.0.0.0/29")
        self.assertRaises(MaxPrefixlenError, lambda: list(self.balancer.splitPrefix(net)))

        net = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.splitPrefix(net)
        self.assertTrue(len(res) == 2)
        self.assertTrue(res[0] == ipaddr.IPv6Network("2001:db8::/49"))
        self.assertTrue(res[1] == ipaddr.IPv6Network("2001:db8:0:8000::/49"))

    def test_get_prefix_sensor(self):
        net = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        sensor = self.balancer.getPrefixGroup(net)
        self.assertTrue(sensor == 1)
        net2 = ipaddr.IPv4Network("10.230.0.0/10")
        sensor = self.balancer.getPrefixGroup(net2)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(sensor)
        self.assertTrue(sensor == None)

    def test_get_largest_prefix(self):
        net = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        largest = self.balancer.getLargestPrefix(1)
        self.assertTrue(largest == net2)
        largest = self.balancer.getLargestPrefix(2)
        self.assertTrue(largest == None)
        largest = self.balancer.getLargestPrefix(5)
        self.assertTrue(largest == None)

class TestBalance(unittest.TestCase):

    def test_get_est_load_net(self):
        self.balancer = SimpleBalancer( ignorePrefixBW = 0)
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        sensors2 = defaultdict(list)
        sensors2[1] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[2] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors2})
        self.assertTrue(res == 1)
        net = ipaddr.IPv4Network("10.10.0.0/24")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,5000000,5000000)
        self.assertTrue(res == 1)
        net3 = ipaddr.IPv4Network("10.12.0.0/24")
        percentTotal = self.balancer.getEstLoad(1,net3)
        self.assertTrue(percentTotal == 0)
        percentTotal = self.balancer.getEstLoad(1,net)
        print "Percent Total: " + str(percentTotal)
        self.assertTrue(percentTotal == 0.5)
        

    def test_balance_by_ip(self):
        self.balancer = SimpleBalancer()
        self.balancer = SimpleBalancer()
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        sensors2 = defaultdict(list)
        sensors2[1] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[2] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors2})
        self.assertTrue(res == 1)
        net = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,500,500)
        self.assertTrue(res == 1)
        self.balancer.balanceByIP( )
        #todo:
        #make sure we do shit

    def test_balance_by_net(self):
        self.balancer = SimpleBalancer()
        self.balancer = SimpleBalancer()
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        sensors2 = defaultdict(list)
        sensors2[1] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[2] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors2})
        self.assertTrue(res == 1)
        net = ipaddr.IPv4Network("10.220.0.0/12")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,500,500)
        self.assertTrue(res == 1)
        self.balancer.balanceByNetBytes([] )

    def test_balance_by_load(self):
        self.balancer = SimpleBalancer( ignoreSensorLoad = 0,
                                        ignorePrefixBW = 0)
        self.balancer = SimpleBalancer()
        sensors = defaultdict(list)
        sensors[1] = {"sensor_id": 1, "of_port_id": 1, "description": "sensor foo"}
        sensors[2] = {"sensor_id": 2, "of_port_id": 2, "description": "sensor foo2"}
        res = self.balancer.addSensorGroup({"group_id": 1,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors})
        self.assertTrue(res == 1)
        sensors2 = defaultdict(list)
        sensors2[1] = {"sensor_id": 3, "of_port_id": 3, "description": "sensor foo3"}
        sensors2[2] = {"sensor_id": 4, "of_port_id": 4, "description": "sensor foo4"}
        res = self.balancer.addSensorGroup({"group_id": 2,
                                            "bw": "10GE",
                                            "admin_status":"active",
                                            "description": "some descr",
                                            "sensors": sensors2})
        self.assertTrue(res == 1)
        net = ipaddr.IPv6Network("2001:0DB8::/48")
        res = self.balancer.addGroupPrefix(1,net,0)
        self.assertTrue(res == 1)
        net2 = ipaddr.IPv4Network("10.0.0.0/10")
        res = self.balancer.addGroupPrefix(1,net2,0)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net,5000000,5000000)
        self.assertTrue(res == 1)
        res = self.balancer.setPrefixBW(net2,500,500)
        self.assertTrue(res == 1)
        res = self.balancer.setSensorLoad(1,.9)
        self.assertTrue(res == 1)
        res = self.balancer.setSensorLoad(2,.1)
        self.assertTrue(res == 1)
        self.balancer.balance( )

    def test_to_string(self):
        self.balancer = SimpleBalancer()
        self


def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInit)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSensorMods))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPrefix))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBalance))
    return suite
