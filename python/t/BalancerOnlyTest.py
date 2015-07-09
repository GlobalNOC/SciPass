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
        self.assertTrue( len(flows) == 1132)

        flow = flows[0]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': 167772160, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 500)
        flow = flows[1]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 10, 'nw_dst': 167772160})
        self.assertEquals(flow['priority'], 500)
        flow = flows[2]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': 167772160, 'nw_src_mask': 16}) 
        self.assertEquals(flow['priority'], 500)
        flow = flows[3]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 9, 'nw_dst': 167772160})
        self.assertEquals(flow['priority'], 500)
        flow = flows[4]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '1'}, {'type': 'output', 'port': '2'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': 167837696, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 600)
        flow = flows[5]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 10, 'nw_dst': 167837696})
        self.assertEquals(flow['priority'], 600)
        flow = flows[6]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '1'}, {'type': 'output', 'port': '2'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': 167837696, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 600)
        flow = flows[7]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 9, 'nw_dst': 167837696})
        self.assertEquals(flow['priority'], 600)
        flow = flows[8]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': 167903232, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 700)
        flow = flows[9]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 10, 'nw_dst': 167903232})
        self.assertEquals(flow['priority'], 700)
        flow = flows[10]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '7'}, {'type': 'output', 'port': '8'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': 167903232, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 700)
        flow = flows[11]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 9, 'nw_dst': 167903232})
        self.assertEquals(flow['priority'], 700)
        flow = flows[12]
        self.assertEquals(flow['actions'], [{'type': 'output', 'port': '1'}, {'type': 'output', 'port': '2'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 10, 'nw_src': 167968768, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 800)
        flow = flows[13]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 10, 'nw_dst': 167968768})
        self.assertEquals(flow['priority'], 800)
        flow = flows[14]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': '1'}, {'type': 'output', 'port': '2'}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 9, 'nw_src': 167968768, 'nw_src_mask': 16})
        self.assertEquals(flow['priority'], 800)
        flow = flows[15]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'phys_port': 9, 'nw_dst': 167968768})
        self.assertEquals(flow['priority'], 800)



def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(BalancerInitTest)
    return suite
