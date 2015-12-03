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


class InlineInitTest(unittest.TestCase):
    def setUp(self):
        self.api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/Inline.xml" )
        
    def testInit(self):

        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None, domain=None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
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
        self.assertEquals(len(flows), 4114)

        flow = flows[0]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'dl_type': None, 'phys_port': 17})
        self.assertEquals(flow['priority'], 3)
        flow = flows[1]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 17}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'dl_type': None, 'phys_port': 25})
        self.assertEquals(flow['priority'], 3)
        flow = flows[2]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 17, 'nw_src': ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[3]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], { 'phys_port': 25, 'nw_dst': ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[4]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 18, 'nw_src':ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)
        flow = flows[5]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 25, 'nw_dst': ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)

        flow = flows[6]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'],{'phys_port': 19, 'nw_src':ipaddr.IPv4Network('0.0.0.0/8') })
        self.assertEquals(flow['priority'], 500)

        flow = flows[7]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 25, 'nw_dst': ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)

        flow = flows[8]
        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 34}, {'type': 'output', 'port': 44}, {'type': 'output', 'port': 25}])
        self.assertEquals(flow['command'],"ADD")
        self.assertEquals(flow['header'], {'phys_port': 20, 'nw_src':ipaddr.IPv4Network('0.0.0.0/8')})
        self.assertEquals(flow['priority'], 500)

        
def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(InlineInitTest)
    return suite
