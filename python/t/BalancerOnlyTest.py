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
import time
import xmlrunner


logging.basicConfig()


class BalancerInitTest(unittest.TestCase):
    def setUp(self):
        self.api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass_balancer_only.xml" )

    def test_bad_flow(self):
        #first setup the handler to get all the flows that were sent                                                                                                       
        flows = []
        def flowSent(dpid = None, domain =  None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            obj = {'dpid': dpid, 'header': header,
                   'actions': actions, 'command': command,
                   'priority': priority,
                   'idle_timeout': idle_timeout,
                   'hard_timeout': hard_timeout}
            flows.append(obj)
            logging.error(obj)


        self.api.registerForwardingStateChangeHandler(flowSent)

        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        self.assertTrue( len(flows) == 1132)
        flows = []
        
        self.api.bad_flow({"nw_src": "10.0.20.2/32", "nw_dst":"8.8.8.8/32", "tp_src":1, "tp_dst":2})
        self.assertEquals(len(flows),2)
        print flows[0]
        print flows[1]
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 9,  'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)


        flows = []
        self.api.bad_flow({"nw_dst": "10.0.20.2/32", "nw_src":"8.8.8.8/32", "tp_src":2, "tp_dst":1})
        self.assertEquals(len(flows),2)
        print flows[0]
        print flows[1]
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst':ipaddr.IPv4Network('8.8.8.8/32') })
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst':ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)



    def test_good_flow(self):
        #first setup the handler to get all the flows that were sent         
        flows = []
        def flowSent(dpid = None, domain = None,header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            obj = {'dpid': dpid, 'header': header,
                   'actions': actions, 'command': command,
                   'priority': priority,
                   'idle_timeout': idle_timeout,
                   'hard_timeout': hard_timeout}
            flows.append(obj)
            logging.error(obj)


        self.api.registerForwardingStateChangeHandler(flowSent)

        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        self.assertTrue( len(flows) == 1132)
        flows = []

        self.api.good_flow({"nw_src": "10.0.20.2/32", "nw_dst":"8.8.8.8/32", "tp_src":1, "tp_dst":2})
        self.assertEquals(len(flows),2)
        print flows[0]
        print flows[1]
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 10,  'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)

        flows = []
        self.api.good_flow({"nw_dst": "10.0.20.2/32", "nw_src":"8.8.8.8/32", "tp_src":2, "tp_dst":1})
        self.assertEquals(len(flows),2)
        print flows[0]
        print flows[1]
        flow = flows[0]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)
        flow = flows[1]
        self.assertEqual(int(flow['hard_timeout']),0)
        self.assertEqual(int(flow['idle_timeout']),90)
        self.assertEqual(flow['actions'],[])
        self.assertEqual(flow['header'],{'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.0.20.2/32'), 'tp_dst': 2, 'tp_src': 1, 'nw_dst': ipaddr.IPv4Network('8.8.8.8/32')})
        self.assertEqual(int(flow['priority']),65535)
        self.assertEqual(flow['command'],"ADD")
        self.assertEqual(flow['dpid'],"%016x" % datapath.id)

        
        
    def testInit(self):

        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None, domain = None,header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
            obj = {'dpid': dpid, 'header': header,
                   'actions': actions, 'command': command,
                   'priority': priority,
                   'idle_timeout': idle_timeout,
                   'hard_timeout': hard_timeout}
            flows.append(obj)
            logging.error(obj)


        self.api.registerForwardingStateChangeHandler(flowSent)

        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        self.assertTrue( len(flows) == 1132)

        flow = flows[0]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.0.0.0/16') })
        self.assertEquals(flow['priority'], 500)
        flow = flows[1]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst' :ipaddr.IPv4Network('10.0.0.0/16')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[2]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.0.0.0/16')}) 
        self.assertEquals(flow['priority'], 500)
        flow = flows[3]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.0.0.0/16')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[4]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[5]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst':ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[6]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[7]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[8]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.2.0.0/16') })
        self.assertEquals(flow['priority'], 700)
        flow = flows[9]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.2.0.0/16')})
        self.assertEquals(flow['priority'], 700)
        flow = flows[10]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.2.0.0/16')})
        self.assertEquals(flow['priority'], 700)
        flow = flows[11]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.2.0.0/16')})
        self.assertEquals(flow['priority'], 700)
        flow = flows[12]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.3.0.0/16')})
        self.assertEquals(flow['priority'], 800)
        flow = flows[13]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.3.0.0/16')})
        self.assertEquals(flow['priority'], 800)
        flow = flows[14]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.3.0.0/16')})
        self.assertEquals(flow['priority'], 800)
        flow = flows[15]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.3.0.0/16')})
        self.assertEquals(flow['priority'], 800)


    def testBalance(self):

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


        self.api.registerForwardingStateChangeHandler(flowSent)

        datapath = Mock(id=1)
        self.api.switchJoined(datapath)
        self.assertTrue( len(flows) == 1132)        

        #reset the flows array to nothing
        flows = []
        self.api.run_balancers()
        #without network traffic there is nothing to balance!
        self.assertTrue( len(flows) == 0)

        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("129.79.0.0/16"), 2000000000, 0)
        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("134.68.0.0/16"), 8000000000, 0)
        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("140.182.0.0/16"), 500000000, 0)
        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("149.159.0.0/16"), 80000000, 0)
        self.api.run_balancers()
        
        self.assertEquals(len(flows), 560)

        flow = flows[0]
        self.assertEquals(flow['actions'],[])
        self.assertEquals(flow['command'],"DELETE_STRICT")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[1]
        self.assertEquals(flow['actions'],[])
        self.assertEquals(flow['command'],"DELETE_STRICT")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[2]
        self.assertEquals(flow['actions'],[])
        self.assertEquals(flow['command'],"DELETE_STRICT")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[3]
        self.assertEquals(flow['actions'],[])
        self.assertEquals(flow['command'],"DELETE_STRICT")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[4]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[5]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_dst': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[6]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src':ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)
        flow = flows[7]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_dst': ipaddr.IPv4Network('10.1.0.0/16')})
        self.assertEquals(flow['priority'], 600)

        #we should be balanced after this!

        total_runs = 0
        #make our while condition true to enter :)
        flows.append({})
        while len(flows) != 0:
            flows = []
            self.api.run_balancers()
            total_runs += 1

        self.assertEquals(len(flows), 0)

def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(BalancerInitTest)
    return suite
