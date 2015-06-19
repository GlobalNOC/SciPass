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


class BalancerInitTest(unittest.TestCase):
    def setUp(self):
        self.api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/SciPass_balancer_only.xml" )
        
    def testInit(self):

        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
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
        self.assertEquals(len(flows), 120)
        self.assertTrue( len(flows) == 120)

        flow = flows[0]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': 167772160, 'nw_src_mask': 8})
        self.assertEquals(flow['priority'], 500)
        flow = flows[1]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 8, 'phys_port': 10, 'nw_dst': 167772160})
        self.assertEquals(flow['priority'], 500)
        flow = flows[2]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': 167772160, 'nw_src_mask': 8})
        self.assertEquals(flow['priority'], 500)
        flow = flows[3]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 8, 'phys_port': 9, 'nw_dst': 167772160})
        self.assertEquals(flow['priority'], 500)

        
def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(BalancerInitTest)
    return suite
