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


class SimpleBalancerInitTest(unittest.TestCase):
    def setUp(self):
        self.api = SciPass( logger = logging.getLogger(__name__),
                          config = str(os.getcwd()) + "/t/etc/Simple_SciPass_balancer_only.xml" )
        
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
        self.assertEquals(len(flows), 566)

        flow = flows[0]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 167772160, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 500)
#        flow = flows[1]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'nw_dst': 167772160})
#        self.assertEquals(flow['priority'], 500)
#        flow = flows[2]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 167837696, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[3]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'nw_dst': 167837696})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[4]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 167903232, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 700)
#        flow = flows[5]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 7}, {'type': 'output', 'port': 8}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'nw_dst': 167903232})
#        self.assertEquals(flow['priority'], 700)
#        flow = flows[6]
#        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 167968768, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 800)
#        flow = flows[7]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'nw_dst': 167968768})
#        self.assertEquals(flow['priority'], 800)


    def testSimpleBalance(self):

        #first setup the handler to get all the flows that were sent
        flows = []
        def flowSent(dpid = None,  domain=None, header = None, actions = None,command = None, priority = None, idle_timeout = None, hard_timeout = None):
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
        self.assertTrue( len(flows) == 566)        

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
        
#        self.assertEquals( len(flows), 10)
#        flow = flows[0]
#        self.assertEquals(flow['actions'],[])
#        self.assertEquals(flow['command'],"DELETE_STRICT")
#        self.assertEquals(flow['header'], {'nw_src': 167837696, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[1]
#        self.assertEquals(flow['actions'],[])
#        self.assertEquals(flow['command'],"DELETE_STRICT")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 16, 'nw_dst': 167837696})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[2]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 167837696, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[3]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 4}, {'type': 'output', 'port': 3}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst': 167837696, 'nw_dst_mask': 16})
#        self.assertEquals(flow['priority'], 600)
#        flow = flows[4]
#        self.assertEquals(flow['actions'],[])
#        self.assertEquals(flow['command'],"DELETE_STRICT")
#        self.assertEquals(flow['header'], {'nw_src': 2252603392, 'nw_src_mask': 16})
#        self.assertEquals(flow['priority'], 26200)
#        flow = flows[5]
#        self.assertEquals(flow['actions'],[])
#        self.assertEquals(flow['command'],"DELETE_STRICT")
#        self.assertEquals(flow['header'],  {'nw_dst_mask': 16, 'nw_dst': 2252603392})
#        self.assertEquals(flow['priority'], 26200)
#        flow = flows[6]
#        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 2252603392, 'nw_src_mask': 17})
#        self.assertEquals(flow['priority'], 26200)
#        flow = flows[7]
#        self.assertEquals(flow['actions'], [{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 17, 'nw_dst': 2252603392})
#        self.assertEquals(flow['priority'], 26200)
#        flow = flows[8]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_src': 2252636160, 'nw_src_mask': 17})
#        self.assertEquals(flow['priority'], 26250)
#        flow = flows[9]
#        self.assertEquals(flow['actions'],[{'type': 'output', 'port': 1}, {'type': 'output', 'port': 2}])
#        self.assertEquals(flow['command'],"ADD")
#        self.assertEquals(flow['header'], {'nw_dst_mask': 17, 'nw_dst': 2252636160})
#        self.assertEquals(flow['priority'], 26250)

        #run the balancer again!
        
        total_runs = 1
        while len(flows) != 0:
            flows = []
            self.api.run_balancers()
            total_runs +=1

        self.assertEquals(total_runs, 46)

        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("134.68.80.0/20"), 8000000000, 0)

        total_runs = 0
        #make our while condition true to enter :)
        flows.append({})
        while len(flows) != 0:
            flows = []
            self.api.run_balancers()
            total_runs += 1

        self.assertEquals(total_runs, 25)
        
        self.api.updatePrefixBW("0000000000000001", ipaddr.IPv4Network("134.68.91.0/24"), 8000000000, 0)

        total_runs = 0
        #make our while condition true to enter :)
        flows.append({})
        while len(flows) != 0:
            flows = []
            self.api.run_balancers()
            total_runs += 1

        self.assertEquals(total_runs, 4)
        



def suite():
    suite = unittest.TestLoader().loadTestsFromTestCase(SimpleBalancerInitTest)
    return suite
