import sys
sys.path.append(".")
import pprint
import unittest
from mock import Mock
import logging
import ipaddr
import os
from SciPass import SciPass
import libxml2
import xmlrunner


logging.basicConfig()


class TestInit(unittest.TestCase):

    def test_valid_config(self):
        api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass.xml"
                          )
        self.assertTrue(isinstance(api,SciPass))
        

#    def test_no_config(self):
#        self.assertRaises(libxml2.parserError,SciPass)
#        
#        api = SciPass( logger = logging.getLogger(__name__),
#                          config = str(os.getcwd()) + "/t/etc/no_config.xml" )
        

#    def test_invalid_config(self):
#        self.assertRaises(libxml2.parserError,SciPass)
#        
#        api = SciPass( logger = logging.getLogger(__name__),
#                          config = str(os.getcwd()) + "/t/etc/InvalidConfig.xml" )

    def test_switch_init(self):
        api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass.xml" )

        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None, domain = None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            obj = {'dpid': dpid, 'header': header,
                   'actions': actions, 'command': command,
                   'priority': priority, 
                   'idle_timeout': idle_timeout,
                   'hard_timeout': hard_timeout}
            flows.append(obj)
            logging.error(obj)
            

        api.registerForwardingStateChangeHandler(flowSent)
        datapath = Mock(id=1)
        api.switchJoined(datapath)

        self.assertTrue( len(flows) == 25)
        #verify all of the 'flow details are set properly'
        for flow in flows:
            self.assertEquals(flow['dpid'], "%016x" % datapath.id)
            self.assertEquals(flow['hard_timeout'], 0)
            self.assertEquals(flow['idle_timeout'], 0)
        
        flow = flows[0]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 1, 'dl_type': None})
        self.assertEquals(flow['priority'], 5)
        flow = flows[1]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':5, 'nw_dst': ipaddr.IPv4Network('10.0.17.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[2]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':1, 'nw_src': ipaddr.IPv4Network('10.0.17.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[3]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':5, 'nw_dst': ipaddr.IPv4Network('10.0.18.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[4]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':1, 'nw_src': ipaddr.IPv4Network('10.0.18.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[5]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 2, 'dl_type': None})
        self.assertEquals(flow['priority'], 5)
        flow = flows[6]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':5, 'nw_dst':ipaddr.IPv4Network('10.0.19.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[7]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':2, 'nw_src': ipaddr.IPv4Network('10.0.19.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[8]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':5, 'nw_dst': ipaddr.IPv4Network('10.0.20.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[9]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port':2, 'nw_src': ipaddr.IPv4Network('10.0.20.0/24')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[10]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 5, 'nw_dst': ipaddr.IPv6Network('2001:0DB8::/48')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[11]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 2, 'nw_src': ipaddr.IPv6Network('2001:0DB8::/48')})
        self.assertEquals(flow['priority'], 10)
        flow = flows[12]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 5, 'dl_type': None})
        self.assertEquals(flow['priority'], 3)
        flow = flows[13]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 10}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 6, 'dl_type': None})
        self.assertEquals(flow['priority'], 10)
        flow = flows[14]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 6}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'dl_type': None})
        self.assertEquals(flow['priority'], 10)
        flow = flows[15]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 27}, {'type': 'output', 'port': 26}, {'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 1, 'nw_src': ipaddr.IPv4Network('10.0.17.0/24')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[16]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 27}, {'type': 'output', 'port': 26}, {'type': 'output', 'port': 6}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.17.0/24')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[17]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 21}, {'type': 'output', 'port': 20}, {'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 1, 'nw_src': ipaddr.IPv4Network('10.0.18.0/24')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[18]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 21}, {'type': 'output', 'port': 20}, {'type': 'output', 'port': 6}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.18.0/24')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[19]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 25}, {'type': 'output', 'port': 24}, {'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 2, 'nw_src': ipaddr.IPv4Network('10.0.19.0/24')})
        self.assertEquals(flow['priority'], 700)
        flow = flows[20]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 25}, {'type': 'output', 'port': 24}, {'type': 'output', 'port': 6}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'],  {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.19.0/24')})
        self.assertEquals(flow['priority'], 700)
        flow = flows[21]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 23}, {'type': 'output', 'port': 22}, {'type': 'output', 'port': 5}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 2, 'nw_src': ipaddr.IPv4Network('10.0.20.0/24')})
        self.assertEquals(flow['priority'], 800)
        flow = flows[22]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 23}, {'type': 'output', 'port': 22}, {'type': 'output', 'port': 6}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.20.0/24')})
        self.assertEquals(flow['priority'], 800)
#        logging.error(flows[21])
#        pprint.pprint(flows[21])
#        pprint.pprint(flows[22])
#        pprint.pprint(flows[23])
#        pprint.pprint(flows[24])
#        pprint.pprint(flows[25])
#        pprint.pprint(flows[26])


        
class TestFunctionality(unittest.TestCase):
    def setUp(self):
        self.api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass.xml" )
        
    def test_update_prefix_bw(self):
        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None, domain=None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            flows.append({'dpid': dpid, 'header': header, 'actions': actions, 'command': command, 'priority': priority, 'idle_timeout': idle_timeout, 'hard_timeout': hard_timeout})

        self.api.registerForwardingStateChangeHandler(flowSent)
        datapath = Mock(id=1)
        self.api.switchJoined(datapath)

        self.assertEquals( len(flows), 25)
        self.api.updatePrefixBW("%016x" % datapath.id, ipaddr.IPv4Network("10.0.19.0/24"), 500,500)
        self.assertTrue(self.api.getBalancer("%016x" % datapath.id, "R&E").getPrefixBW(ipaddr.IPv4Network("10.0.19.0/24")), 1000)
        self.api.updatePrefixBW("%016x" % datapath.id, ipaddr.IPv4Network("10.0.17.0/24"), 500,500)
        self.assertTrue(self.api.getBalancer("%016x" % datapath.id, "R&E").getPrefixBW(ipaddr.IPv4Network("10.0.17.0/24")), 1000)
        self.api.updatePrefixBW("%016x" % datapath.id, ipaddr.IPv6Network("2001:0DB8::/48"), 500,500)
        self.assertTrue(self.api.getBalancer("%016x" % datapath.id, "R&E").getPrefixBW(ipaddr.IPv6Network("2001:0DB8::/48")), 1000)

    def test_good_flow(self):
        flows = []
        def flowSent(dpid = None, domain=None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            flows.append({'dpid': dpid, 'header': header, 'actions': actions, 'command': command, 'priority': priority, 'idle_timeout': idle_timeout, 'hard_timeout': hard_timeout})

        self.api.registerForwardingStateChangeHandler(flowSent)
        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        #self.logger.error("testing good flow")
        self.assertEquals(len(flows),25)
        flows = []
        self.api.good_flow({"nw_src": "10.0.20.2/32", "nw_dst":"156.56.6.1/32", "tp_src":1, "tp_dst":2})
        self.assertEquals(len(flows),2)
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[{'type': 'output', 'port': '10'}])
        self.assertEqual(flow['header'],{'phys_port': 2, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('156.56.6.1/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[{'type': 'output', 'port': '2'}])
        self.assertEqual(flow['header'],{'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 1, 'tp_src': 2, 'nw_src': ipaddr.IPv4Network('156.56.6.1/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        
        

    def test_bad_flow(self):
        flows = []
        def flowSent(dpid = None, domain=None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            flows.append({'dpid': dpid, 'header': header, 'actions': actions, 'command': command, 'priority': priority, 'idle_timeout': idle_timeout, 'hard_timeout': hard_timeout})

        self.api.registerForwardingStateChangeHandler(flowSent)
        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        #self.logger.error("testing good flow")
        self.assertEquals(len(flows),25)
        flows = []
        self.api.bad_flow({"nw_src": "10.0.20.2/32", "nw_dst":"156.56.6.1/32", "tp_src":1, "tp_dst":2})
        self.assertEquals(len(flows),2)
        print flows[0]
        print flows[1]
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 2, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('156.56.6.1/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 1, 'tp_src': 2, 'nw_src': ipaddr.IPv4Network('156.56.6.1/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)

    def test_block_unknown_prefix(self):
        pass
    
    def test_bypass_unknown_prefix(self):
        pass       

class TestFlowStatProcessing(unittest.TestCase):
    def test_empty_flowstat_process(self):
        pass

    def test_good_flowstat(self):
        pass

    def test_bad_flowstat(self):
        pass

    def test_unknown_flowstat(self):
        pass


def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInit)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFunctionality))
    return suite
