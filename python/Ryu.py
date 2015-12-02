# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2014 The Trustees of Indiana University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import struct
import time
import pprint
from ryu import cfg
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ether
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib import dpid as dpid_lib
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json

import socket
import ipaddr 

from collections import defaultdict
from SimpleBalancer import SimpleBalancer
from SciPass import SciPass

"""
 Forwarding rule Priorities
   BlackList  
   WhiteList
   Balancer 
   Default
"""


class SciPassRest(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SciPassRest, self).__init__(req, link, data, **config)
        self.api = data['api']
        self.logger = logging.getLogger(__name__)
    #POST /scipass/flows/good_flow
    @route('scipass', '/scipass/flows/good_flow', methods=['PUT'])
    def good_flow(self, req):
        try:
            obj = eval(req.body)
        except SyntaxError:
            self.logger.error("Syntax Error processing good_flow signal %s", req.body)
            return Response(status=400)

        result = self.api.good_flow(obj)
        if result['success'] == 0:
            return Response(body=json.dumps(result),status=500)
        return Response(content_type='application/json',body=json.dumps(result))

    #POST /scipass/flows/bad_flow
    @route('scipass', '/scipass/flows/bad_flow', methods=['PUT'])
    def bad_flow(self, req):
        try:
            obj = eval(req.body)
        except SyntaxError:
            self.logger.error("Syntax Error processing bad_flow signal %s", req.body)
            return Response(status=400)
        result = self.api.bad_flow(obj)
        if result['success'] == 0:
            return Response(body=json.dumps(result),status=500)
        return Response(content_type='application/json',body=json.dumps(result))

    #GET /scipass/flows/get_good_flows
    @route('scipass', '/scipass/flows/get_good_flows', methods=['GET'])
    def get_good_flows(self, req):
        result = self.api.get_good_flows()
        return Response(content_type='application/json',body=json.dumps(result))

    #GET /scipass/flows/get_bad_flows
    @route('scipass', '/scipass/flows/get_bad_flows', methods=['GET'])
    def get_bad_flows(self, req):
        result = self.api.get_bad_flows()
        return Response(content_type='application/json',body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/flows', methods=['GET'], requirements= {'dpid': dpid_lib.DPID_PATTERN})
    def get_switch_flows(self, req, **kwargs):
        result = self.api.getSwitchFlows(dpid=kwargs['dpid'])
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass', '/scipass/sensor/load', methods=['PUT'])
    def update_sensor_load(self, req):
        try:
            obj = eval(req.body)
        except SyntaxError:
            self.logger.error("Syntax Error processing update_sensor_status signal %s", req.body)
            return Response(status=400)
        result = self.api.setSensorStatus(obj['sensor_id'],obj['load'])
        return Response(content_type='application/json',body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/domain/{domain}/sensor/{sensor_id}', methods=['GET'], requirements= {'dpid': dpid_lib.DPID_PATTERN})
    def get_sensor_load(self, req, **kwargs):
        result = self.api.getSensorStatus(dpid=kwargs['dpid'], domain=kwargs['domain'], sensor_id=kwargs['sensor_id'])
        return Response(content_type='application/json',body=json.dumps(result))

    @route('scipass', '/scipass/switches', methods=['GET'])
    def get_switches(self, req):
        result = self.api.getSwitches()
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/domain/{domain}/sensor_groups', methods=['GET'], requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_domain_sensor_groups(self, req, **kwargs):
        result = self.api.getDomainSensorGroups(dpid = kwargs['dpid'], domain = kwargs['domain'] )
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/domain/{domain}/sensor_group/{sensor_group}', methods=['GET'], requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_domain_sensor_group_details(self, req, **kwargs):
        result = self.api.getDomainSensorGroup(dpid = kwargs['dpid'], domain = kwargs['domain'], sensor_group = kwargs['sensor_group'] )
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass','/scipass/switch/{dpid}/domain/{domain}/sensor_group/{sensor_group}/sensor/{sensor}', methods=['GET'], requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_domain_sensor_group_sensor(self, req, **kwargs):
        result = self.api.getDomainSensor(dpid = kwargs['dpid'], domain = kwargs['domain'], sensor_group = kwargs['sensor_group'], sensor = kwargs['sensor'])
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/domains', methods=['GET'], requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_switch_domains(self, req, **kwargs):
        result = self.api.getSwitchDomains(dpid=kwargs['dpid'])
        return Response(content_type='application/json', body=json.dumps(result))
    
    @route('scipass', '/scipass/switch/{dpid}/domain/{domain}', methods=['GET'], requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_domain_status(self, req, **kwargs):
        result = self.api.getDomainDetails(dpid = kwargs['dpid'], domain = kwargs['domain'])
        return Response(content_type='application/json', body=json.dumps(result))

    @route('scipass', '/scipass/switch/{dpid}/domain/{domain}/flows',methods=['GET'],requirements = {'dpid': dpid_lib.DPID_PATTERN})
    def get_domain_flows(self,req, **kwargs):
        result = self.api.getDomainFlows(dpid = kwargs['dpid'], domain = kwargs['domain'])
        return Response(content_type='application/json', body=json.dumps(result))


class Ryu(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION, ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = { 'wsgi': WSGIApplication }
    def __init__(self,*args, **kwargs):
        super(Ryu,self).__init__(*args,**kwargs)
        #--- register for configuration options
        SciPass_opts = [
            cfg.StrOpt('SciPassConfig',default='/etc/SciPass/SciPass.xml',
                       help='where to find the SciPass config file'),
            cfg.BoolOpt('readState', default=False,
                        help = 'Read previous state or not')
            ]
        self.CONF.register_opts(SciPass_opts, group='SciPass')
        self.logger.error("Starting SciPass")
        self.datapaths = {}
        self.isactive = 1
        self.statsInterval = 5
        self.balanceInterval = 15
        self.bal = None
        self.stats = {}
        self.stats_thread = hub.spawn(self._stats_loop)
        self.balance_thread = hub.spawn(self._balance_loop)
        
        self.ports = defaultdict(dict);
        self.prefix_bytes = defaultdict(lambda: defaultdict(int))
        self.lastStatsTime = {}
        self.flowmods = {}
        
        api = SciPass(logger = self.logger,
                      config = self.CONF.SciPass.SciPassConfig,
                      readState = self.CONF.SciPass.readState)
        
        api.registerForwardingStateChangeHandler(self.changeSwitchForwardingState)

        self.api = api
        
        wsgi = kwargs['wsgi']
        wsgi.register(SciPassRest, {'api' : self.api})
        
    def changeSwitchForwardingState(self, dpid=None, domain=None,header=None, actions=None, command=None, idle_timeout=None, hard_timeout=None, priority=1):
        #self.logger.error("Changing switch forwarding state")
        
        if(not self.datapaths.has_key(dpid)):
            self.logger.error("unable to find switch with dpid " + dpid)
            self.logger.error(self.datapaths)
            return
        
        datapath = self.datapaths[dpid]

        ofp      = datapath.ofproto
        parser   = datapath.ofproto_parser
        
        #support different OF versions!
        if(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
            self.logger.debug("Generating OF 1.3 FlowMod")
            flow = self.OF13_flow(datapath, domain=domain, header=header, actions=actions, command=command, 
                                  idle_timeout=idle_timeout, hard_timeout=hard_timeout, priority=priority)
        elif (ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            self.logger.debug("Generating OF 1.0 FlowMod")
            flow = self.OF10_flow(dp=datapath, domain=domain, header=header, actions=actions, command=command, 
                                  idle_timeout=idle_timeout, hard_timeout=hard_timeout, priority=priority)
        else:
            self.logger.error("Unsupported OF Version")
            return

        if(datapath.is_active == True):
            self.logger.debug("Installing Flow: " + str(flow))
            datapath.send_msg(flow)
        else:
            self.logger.error("Device is not connected")




    def OF10_flow(self, dp=None, domain=None, header=None, actions=None, command=None, idle_timeout=None, hard_timeout=None, priority=1):
        ofp      = dp.ofproto
        parser   = dp.ofproto_parser
        obj = {} 
        
        if(header.has_key('dl_type')):
            if(header['dl_type'] == None):
                obj['dl_type'] = None
                del header['dl_type']
            else:
                obj['dl_type'] = int(header['dl_type'])
        else:
            obj['dl_type'] = ether.ETH_TYPE_IP
            
        if(header.has_key('phys_port')):
            obj['in_port'] = int(header['phys_port'])
        else:
            obj['in_port'] = None
            
        if(header.has_key('nw_src')):
            if header['nw_src'].version == 6:
                obj['dl_type'] = 34525
            elif header['nw_src'].version == 4:
                obj['nw_src'] = int(header['nw_src'])
                obj['nw_src_mask'] = int(header['nw_src'].prefixlen)
        else:
            obj['nw_src'] = None
            obj['nw_src_mask'] = None
         
        if(header.has_key('nw_dst')):
            if header['nw_dst'].version == 6:
                obj['dl_type'] = 34525
            elif header['nw_dst'].version == 4:
                obj['nw_dst'] = int(header['nw_dst'])
                obj['nw_dst_mask'] = int(header['nw_dst'].prefixlen)
        else:
            obj['nw_dst'] = None
            obj['nw_dst_mask'] = None

        if(header.has_key('tp_src')):
            obj['tp_src'] = int(header['tp_src'])
        else:
            obj['tp_src'] = None

        if(header.has_key('tp_dst')):
            obj['tp_dst'] = int(header['tp_dst'])
        else:
            obj['tp_dst'] = None

        if(obj['dl_type'] == None):
            del obj['dl_type']
        
        match = parser.OFPMatch(**obj)
                        
        of_actions = []
        for action in actions:
            if(action['type'] == "output"):
                of_actions.append(parser.OFPActionOutput(int(action['port']),0))
           
        #self.logger.error("Actions: " + str(of_actions))
        flags = 0
        dpid =  "%016x" % dp.id
        idle = {}
        hard =  {}
        now = time.time()
        
        if int(idle_timeout) != 0:
            timeout = now + int(idle_timeout)
            idle   =      {'timeout': timeout,
                           'dpid': dpid,
                           'domain' : domain,
                           'idle_timeout': int(idle_timeout),
                           'pkt_count': 0,
                           'header': header,
                           'actions': of_actions,
                           'priority': priority,
                           'command': "ADD"}

        if int(hard_timeout) != 0:
            timeout = now + int(hard_timeout)
            hard =        {'timeout': timeout,
                           'dpid': dpid,
                           'domain' : domain,
                           'idle_timeout': int(hard_timeout),
                           'pkt_count': 0,
                           'header': header,
                           'actions': of_actions,
                           'priority': priority,
                           'command': "ADD"}

        if(command == "ADD"):
            command = ofp.OFPFC_ADD
            flags = ofp.OFPFF_SEND_FLOW_REM
            self.api.pushTimeouts(idle, hard)
            self.api.pushFlows(dpid, domain, header, actions, priority)
        elif(command == "DELETE_STRICT"):
            command = ofp.OFPFC_DELETE_STRICT
            self.api.remove_flow(dpid, domain, header, priority)
        else:
            command = -1
        #self.logger.error("Sending flow mod with command: " + str(command))
        #self.logger.error("Datpath: " + str(datapath))
        
        mod = parser.OFPFlowMod( datapath     = dp,
                                 priority     = int(priority),
                                 match        = match,
                                 cookie       = 0,
                                 buffer_id    = ofp.OFP_NO_BUFFER,
                                 command      = command,
                                 idle_timeout = int(idle_timeout),
                                 hard_timeout = int(hard_timeout),
                                 actions      = of_actions,
                                 flags        = flags)
        return mod

    def OF13_flow(self, dp=None, domain=None,header=None, actions=None, command=None, idle_timeout=None, hard_timeout=None, priority=1):
        ofp      = dp.ofproto
        parser   = dp.ofproto_parser
        
        obj = {}
        obj['ipv6_src'] = None
        obj['ipv6_dst'] = None
        obj['ipv4_src'] = None
        obj['ipv4_dst'] = None
        obj['eth_type']  = None
        
        if(header.has_key('phys_port')):
            obj['in_port'] = int(header['phys_port'])
            header['in_port'] = int(header['phys_port'])
            del header['phys_port']

        if(header.has_key('nw_src')):
            if(header['nw_src'].version == 4):
                obj['ipv4_src'] = (str(header['nw_src'].ip), str(header['nw_src'].netmask))
                obj['eth_type'] = 0x800
            else:
                del obj['ipv4_src']
            if(header['nw_src'].version == 6):
                if(obj.has_key('ipv4_src')):
                    self.logger.error("IPv4 and IPv6 in the same message")
                    return
                obj['ipv6_src'] = (str(header['nw_src'].ip), str(header['nw_src'].netmask))
                obj['eth_type'] = 0x86dd
            else:
                del obj['ipv6_src']
        else:
            del obj['ipv4_src']
            del obj['ipv6_src']
        
        if(header.has_key('nw_dst')):
            if(header['nw_dst'].version == 4):
                if(obj.has_key('ipv6_src')):
                    self.logger.error("IPv4 and IPv6 in the same message")
                    return
                obj['ipv4_dst'] = (str(header['nw_dst'].ip), str(header['nw_dst'].netmask))
                obj['eth_type'] = 0x800
            else:
                del obj['ipv4_dst']
            if(header['nw_dst'].version == 6):
                if(obj.has_key('ipv4_src') or obj.has_key('ipv4_dst')):
                    self.logger.error("IPv4 and IPv6 in the same message")
                    return
                obj['ipv6_dst'] = (str(header['nw_dst'].ip), str(header['nw_dst'].netmask))
                obj['eth_type'] = 0x86dd
            else:
                del obj['ipv6_dst']
        else:
            del obj['ipv4_dst']
            del obj['ipv6_dst']

        if(header.has_key('tcp_src') and header.has_key('udp_dst')):
            self.logger.error("TCP and UDP ports")
            return
            
        if(header.has_key('udp_src') and header.has_key('tcp_dst')):
            self.logger.error("TCP and UDP ports")
            return

        if(header.has_key('tcp_src') and header.has_key('udp_src')):
            self.logger.error("TCP and UDP ports")
            return

        if(header.has_key('tcp_dst') and header.has_key('udp_dst')):
            self.logger.error("TCP and UDP ports")
            return
                    
        obj['ip_proto'] = None
        obj['tcp_src'] = None
        obj['tcp_dst'] = None
        obj['udp_src'] = None
        obj['udp_dst'] = None

        if(header.has_key('tcp_src')):
            obj['tcp_src'] = header['tcp_src']
            obj['ip_proto'] = 6
        else:
            del obj['tcp_src']
            

        if(header.has_key('tcp_dst')):
            obj['tcp_dst'] = header['tcp_dst']
            obj['ip_proto'] = 6
        else:
            del obj['tcp_dst'] 
            

        if(header.has_key('udp_src')):
            obj['udp_src'] = header['udp_src']
            obj['ip_proto'] = 17
        else:
            del obj['udp_src']
            

        if(header.has_key('udp_dst')):
            obj['udp_dst'] = header['udp_dst']
            obj['ip_proto'] = 17
        else:
            del obj['udp_dst']
            
                
        if obj['eth_type'] is None:
            del obj['eth_type']

        if obj['ip_proto'] is None:
            del obj['ip_proto']
        
        match = parser.OFPMatch(**obj)
        of_actions = []
        for action in actions:
            if(action['type'] == "output"):
                of_actions.append(parser.OFPActionOutput(port     = int(action['port']),
                                                         max_len  = 0
                                                         ))

        if header.has_key('dl_type'):
            del header["dl_type"]

        if obj.has_key('eth_type'):
            header['eth_type'] = obj['eth_type']

        dpid =  "%016x" % dp.id
        idle = {}
        hard =  {}
        now = time.time()
        
        if int(idle_timeout) != 0:
            timeout = now + int(idle_timeout)
            idle   =      {'timeout': timeout,
                           'dpid': dpid,
                           'domain' : domain,
                           'idle_timeout': int(idle_timeout),
                           'pkt_count': 0,
                           'header': header,
                           'actions': of_actions,
                           'priority': priority,
                           'command': "ADD"}

        if int(hard_timeout) != 0:
            timeout = now + int(hard_timeout)
            hard =        {'timeout': timeout,
                           'dpid': dpid,
                           'domain' : domain,
                           'idle_timeout': int(hard_timeout),
                           'pkt_count': 0,
                           'header': header,
                           'actions': of_actions,
                           'priority': priority,
                           'command': "ADD"}
            
        self.logger.debug("Actions: " + str(of_actions))
        flags = 0
        if(command == "ADD"):
            command = ofp.OFPFC_ADD
            flags = ofp.OFPFF_SEND_FLOW_REM
            self.api.pushTimeouts(idle, hard)
            self.api.pushFlows(dpid, domain, header, actions, priority)
        elif(command == "DELETE_STRICT"):
            command = ofp.OFPFC_DELETE_STRICT
            self.api.remove_flow(dpid, domain, header, priority)
        else:
            command = ofp.OFPFC_DELETE
        
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                             of_actions)]
        mod = parser.OFPFlowMod( datapath = dp,
                                 cookie = 0,
                                 cookie_mask = 0,
                                 priority = int(priority),
                                 buffer_id = ofp.OFP_NO_BUFFER,
                                 match    = match,
                                 command  = command,
                                 instructions  = inst,
                                 idle_timeout = int(idle_timeout),
                                 hard_timeout = int(hard_timeout),
                                 out_port = ofp.OFPP_ANY,
                                 out_group = ofp.OFPG_ANY,
                                 flags     = flags)
        
        
        return mod
        
        
    def flushRules(self, dpid):
        if(not self.datapaths.has_key(dpid)):
            self.logger.error("unable to find switch with dpid " + dpid)
            return
        
        datapath = self.datapaths[dpid]
        ofp      = datapath.ofproto
        parser   = datapath.ofproto_parser

         # --- create flowmod to control traffic from the prefix to the interwebs
        match = parser.OFPMatch()
        if(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
            mod = parser.OFPFlowMod(datapath    = datapath,
                                    table_id    = ofp.OFPTT_ALL,
                                    match       = match,
                                    cookie      = 0,
                                    cookie_mask = 0,
                                    command     = ofp.OFPFC_DELETE,
                                    out_port    = ofp.OFPP_ANY, 
                                    out_group   = ofp.OFPG_ANY)
        elif (ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            mod = parser.OFPFlowMod(datapath,match,0,ofp.OFPFC_DELETE)
        
         #--- remove mods in the flowmod cache
        self.flowmods[dpid] = []
        
        
         #--- if dp is active then push the rules
        if(datapath.is_active == True):
            datapath.send_msg(mod)
            
    def synchRules(self, dpid):
      #--- routine to syncronize the rules to the DP
      #--- currently just pushes, somday should diff
         
      #--- yep thats a hack, need to think about what multiple switches means for scipass
         if(not self.datapaths.has_key(dpid)):
             self.logger.error("unable to find switch with dpid " + dpid)
             return

         datapath = self.datapaths[dpid]
         if(datapath.is_active == True):
             for mod in self.flowmods:
                 datapath.send_msg(mod)

    def defaultDrop(self, dpid):
        # installs a default priority 1 drop rule
        if(not self.datapaths.has_key(dpid)):
            self.logger.error("unable to find switch with dpid " + dpid)
            return
        
        datapath = self.datapaths[dpid]
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        command = ofp.OFPFC_ADD
        priority = 1
        cookie = 0
        match = parser.OFPMatch()
        mod = parser.OFPFlowMod(datapath=datapath, 
                                match=match,
                                priority=priority,
                                command=command,
                                cookie=cookie)

        if(datapath.is_active == True):
            self.logger.info("Installing a default drop rule for switch with dpid " + dpid)
            datapath.send_msg(mod)
        else:
            self.logging.error("Unable to find switch with dpid {0}"
                               " to install a default drop rule".format(dpid))

    def _stats_loop(self):
         while 1:
          #--- send stats request
             for dp in self.datapaths.values():
                 self._request_stats(dp)
                 
             #--- sleep
             hub.sleep(self.statsInterval)

    def _balance_loop(self):
         while 1:
             self.logger.debug("Balancing")
             #--- tell the system to rebalance
             self.api.run_balancers()
             #--- sleep
             hub.sleep(self.balanceInterval)

    def _request_stats(self,datapath):
        ofp    = datapath.ofproto
        parser = datapath.ofproto_parser

        cookie = cookie_mask = 0
        match  = parser.OFPMatch()
        if(ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            req    = parser.OFPFlowStatsRequest(	datapath,
                                                        0,
                                                        match,
                                                        0xff,
                                                        ofp.OFPP_NONE)
        
            
            datapath.send_msg(req)
            #Port Stats request
            req = parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_NONE)
            datapath.send_msg(req)
        elif(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
             req = parser.OFPFlowStatsRequest(datapath, 0,
                                              0,
                                              ofp.OFPP_ANY, 
                                              ofp.OFPG_ANY,
                                              cookie, cookie_mask,
                                              match)
             datapath.send_msg(req)
             req = parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_ANY)
             datapath.send_msg(req)
             
    #handle the remove flow event so we know what to sync up when we do this
    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _remove_flow_handler(self, ev):
        flow = ev.msg
        datapath = ev.msg.datapath
        ofp = datapath.ofproto 
        if(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
            self.process_flow_removed_of13(flow, datapath)
        elif(ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            self.process_flow_removed_of10(flow, datapath)
        
        
    @set_ev_cls(ofp_event.EventOFPStateChange,
                 [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if(datapath.id == None):
                return
            dpid = "%016x" % datapath.id
            if not dpid in self.datapaths:
                self.logger.error('register datapath: %016x', datapath.id)
                self.datapaths[dpid] = datapath
                if(not self.flowmods.has_key(dpid)):
                    self.flowmods[dpid] = []
            else:
                del self.datapaths[dpid]
                self.logger.error('register datapath: %016x', datapath.id)
                self.datapaths[dpid] = datapath
                if(not self.flowmods.has_key(dpid)):
                    self.flowmods[dpid] = []
            
            self.flushRules(dpid) 
            self.defaultDrop(dpid)
            #--- start the balancing act
            self.api.switchJoined(datapath)

        elif ev.state == DEAD_DISPATCHER:
            if(datapath.id == None):
                return
            dpid = "%016x" % datapath.id
            if dpid in self.datapaths:
                self.logger.error('datapath leave: %016x', datapath.id)
                self.api.switchLeave(datapath)
                del self.datapaths[dpid]
            else:
                self.logger.error("unregistered node left!@!@!@!")
        else:
            self.logger.error("Unknown state in change handler: " + str(ev.state))
            
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg        = ev.msg
        dp         = msg.datapath
        ofp        = dp.ofproto
        if(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
            self.process_port_status_of13(msg,ofp)
        elif(ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            self.process_port_status_of10(msg,ofp)
            
    def process_port_status_of10(self,msg,ofp):
        reason     = msg.reason
        port_no    = msg.desc.port_no
        link_state = msg.desc.state

        ofproto = msg.datapath.ofproto
        if reason == ofp.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofp.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofp.OFPPR_MODIFY:
            #this is not working
            #state_human = self.api.OFP_PORT_STATE[link_state] if(self.api.OFP_PORT_STATE.has_key(link_state)) else link_state
            #self.logger.info("port modified %s state %s", port_no, state_human)

            #--- need to enable or disable a sensor if the port came up or down
            if(link_state   == ofproto_v1_0.OFPPS_LINK_DOWN):
                self.api.setSensorStatus(port_no, 0)
            elif(link_state == ofproto_v1_0.OFPPS_STP_LISTEN):
                self.api.setSensorStatus(port_no, 1)
            
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)

    def process_port_status_of13(self,msg,ofp):
        reason      = msg.reason
        port_no     = msg.desc.port_no
        link_config = msg.desc.config
        
        if reason == ofp.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofp.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofp.OFPPR_MODIFY:
            if link_config == ofp.OFPPC_PORT_DOWN:
                # port is down
                self.api.setSensorStatus(port_no, 0)
            else:
                # port is up
                self.api.setSensorStatus(port_no, 1)
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        #--- update scipass utilization stats for forwarding rules

        if(not self.stats.has_key(ev.msg.datapath.id)):
            self.stats[ev.msg.datapath.id] = []

        for stat in body:
            self.stats[ev.msg.datapath.id].append(stat)
            
        if(ev.msg.flags == 0):
            self.process_flow_stats(self.stats[ev.msg.datapath.id], ev.msg.datapath)
            self.stats[ev.msg.datapath.id] = []
        
    def process_flow_removed_of13(self, flow, dp):
        self.logger.debug("flow removed processor")
        header = {}
        _, _, _, header = self.processStat(flow)

        if header.has_key('eth_type'):
            if header['eth_type'] == 0x86dd:
                #IPv6
                if header.has_key('ipv6_src'):
                    header['nw_src'] = header['ipv6_src']
                    del header['ipv6_src']
                if header.has_key('ipv6_dst'):
                    header['nw_dst'] = header['ipv6_dst']
                    del header['ipv6_dst']
            elif header['eth_type'] == 0x800:
                #IPv4
                if header.has_key('ipv4_src'):
                    header['nw_src'] =header['ipv4_src']
                    del header['ipv4_src']
                if header.has_key('ipv4_dst'):
                    header['nw_dst'] = header['ipv4_dst']
                    del header['ipv4_dst']
        if header.has_key('in_port'):
            header['phys_port'] = header['in_port']
            del header['in_port']
        
        match = {}
        fields = ["nw_src", "nw_dst" , "tcp_src" , "tcp_dst" , "udp_src", "udp_dst", "phys_port"]
        for field in fields:
            if header.has_key(field):
                match[field] = header[field]
        
        priority = flow.priority
        self.api.remove_flow(header=match, priority=priority)


    def process_flow_removed_of10(self, flow, dp):
        self.logger.debug("flow removed processor")
        ofproto = dp.ofproto
        src_mask = 32 - ((flow.match.wildcards & ofproto.OFPFW_NW_SRC_MASK) >> ofproto.OFPFW_NW_SRC_SHIFT)
        dst_mask = 32 - ((flow.match.wildcards & ofproto.OFPFW_NW_DST_MASK) >> ofproto.OFPFW_NW_DST_SHIFT)
        obj = {}
        if flow.match.nw_src > 0:
            if(src_mask > 0):
                id = ipaddr.IPv4Address(flow.match.nw_src)
                src_prefix = ipaddr.IPv4Network(str(id)+"/"+str(src_mask))
                obj['nw_src'] = str(src_prefix)
            else:
                src_prefix = ipaddr.IPv4Network(flow.match.nw_src)
                obj['nw_src'] = str(src_prefix)
        if flow.match.nw_dst > 0:
            if(dst_mask > 0):
                id = ipaddr.IPv4Address(flow.match.nw_dst)
                dst_prefix = ipaddr.IPv4Network(str(id)+"/"+str(dst_mask))
                obj['nw_dst'] = str(dst_prefix)
            else:
                dst_prefix = ipaddr.IPv4Network(flow.match.nw_dst)
                obj['nw_dst'] = str(dst_prefix)
        
        if flow.match.tp_src > 0:
            obj['tp_src'] = flow.match.tp_src
        
        if flow.match.tp_dst > 0:
            obj['tp_dst'] = flow.match.tp_dst

        if flow.match.in_port > 0:
            obj['phys_port'] = flow.match.in_port
        priority =  flow.priority
        self.api.remove_flow(header=obj, priority=priority)
        

    def process_flow_stats(self, stats, dp):
        ofp = dp.ofproto
        if(ofp.OFP_VERSION == ofproto_v1_3.OFP_VERSION):
            self.process_flow_stats_of13(stats,dp)
        elif(ofp.OFP_VERSION == ofproto_v1_0.OFP_VERSION):
            self.process_flow_stats_of10(stats,dp)

    def processStat(self, stat):
        # processes a single stat from flow_stats and flow_removed
        # and returns a header 
        # OF13
        prefix = None
        d = None
        header = {}
        match = stat.match.__dict__
        ser_header = {} # serializable header
        def getCIDR(netmask):
            bitCount = [0, 0x8000, 0xc000, 0xe000, 0xf000, 0xf800, 0xfc00, 0xfe00, 0xff00, 0xff80, 0xffc0, 0xffe0, 0xfff0, 0xfff8, 0xfffc, 0xfffe, 0xffff]
            count = 0
            try:
                for w in netmask.split(':'):
                    if not w or int(w, 16) == 0: break
                    count += bitCount.index(int(w, 16))
            except:
                self.logger.info("Bad netmask")
                return 0
            return count

        def ipv6Prefix(addr):
            """returns IPv6 object for a given address and netmask"""
            prefix = None
            if type(addr) is tuple:
                mask = getCIDR(str(addr[1]))
                if mask == 0:
                    prefix = ipaddr.IPv6Network(str(addr[0]))
                else:
                    prefix = ipaddr.IPv6Network(str(addr[0]) + "/" + str(mask))
            elif type(addr) is str:
                prefix = ipaddr.IPv6Network(str(addr))
            return prefix

        def ipv4Prefix(addr):
            """returns IPv4 object for a given address and netmask"""
            prefix = None
            if type(addr) is tuple:
                prefix = ipaddr.IPv4Network(str(addr[0]) + "/" + str(addr[1]))
            elif type(addr) is str:
                prefix = ipaddr.IPv4Network(str(addr))
            return prefix

        if(stat.match.__contains__('eth_type')):
            #IPv6
            if(stat.match['eth_type'] == 0x86dd):
                if(stat.match.__contains__('ipv6_src') and stat.match.__contains__('ipv6_dst')):
                    #for good and bad flow
                    id = stat.match['ipv6_src']
                    prefix = ipv6Prefix(id)
                    if prefix:
                        header['ipv6_src'] = prefix
                        ser_header['ipv6_src'] = str(prefix)
                    id = stat.match['ipv6_dst']
                    prefix = ipv6Prefix(id)
                    if prefix:
                        header['ipv6_dst'] = prefix
                        ser_header['ipv6_dst'] = str(prefix)
                elif(stat.match.__contains__('ipv6_src')):
                    id = stat.match['ipv6_src']
                    prefix = ipv6Prefix(id)
                    if prefix:
                        header['ipv6_src'] = prefix
                        ser_header['ipv6_src'] = str(prefix)
                        d = "tx"
                elif(stat.match.__contains__('ipv6_dst')):
                    id = stat.match['ipv6_dst']
                    prefix = ipv6Prefix(id)
                    if prefix:
                        header['ipv6_dst'] = prefix
                        ser_header['ipv6_dst'] = str(prefix)
                        d = "rx"
        
            if(stat.match['eth_type'] == 0x800):
                if(stat.match.__contains__('ipv4_src') and stat.match.__contains__('ipv4_dst')):
                    id = stat.match['ipv4_src']
                    prefix = ipv4Prefix(id)
                    if prefix:
                        header['ipv4_src'] = prefix
                        ser_header['ipv4_src'] = str(prefix)
                    id = stat.match['ipv4_dst']
                    prefix = ipv4Prefix(id)
                    if prefix:
                        header['ipv4_dst'] = prefix
                        ser_header['ipv4_dst'] = str(prefix)
                elif(stat.match.__contains__('ipv4_src')):
                    id = stat.match['ipv4_src']
                    prefix = ipv4Prefix(id)
                    if prefix:
                        header['ipv4_src'] = prefix
                        ser_header['ipv4_src'] = str(prefix)
                        d = "tx"
                elif(stat.match.__contains__('ipv4_dst')):
                    id = stat.match['ipv4_dst']
                    prefix = ipv4Prefix(id)
                    if prefix:
                        header['ipv4_dst'] = prefix
                        ser_header['ipv4_dst'] = str(prefix)
                        d = "rx"
        
        obj = match['_fields2']
        for field in obj:
            if(not header.has_key(field[0])):
                header[field[0]] = field[1]
            if(not ser_header.has_key(field[0])):
                ser_header[field[0]] = field[1]
        return header, prefix, d, ser_header


    def process_flow_stats_of13(self, stats, dp):
        self.logger.debug("flow stat processor 1.3")
        self.logger.debug("flows stats: " + str(len(stats)))
        #--- figure out the time since last stats
        prefix_bps = defaultdict(lambda: defaultdict(int))
        prefix_bytes = {}
        flows = []
        dpid = dp.id
        ofproto = dp.ofproto
        if(self.lastStatsTime.has_key(dpid)):
            old_time = self.lastStatsTime[dpid]
        else:
            self.lastStatsTime[dpid] = None
            old_time = None
        now = int(time.time())
        
        stats_et = None
        if(old_time != None):
            stats_et = now - old_time

        self.lastStatsTime[dpid] = now

        for stat in stats:
            header = {}
            priority = stat.priority
            match = stat.match.__dict__
            header, prefix, d, _  = self.processStat(stat)
            if header.has_key('eth_type'):
                if header['eth_type'] == 0x86dd:
                    if header.has_key('ipv6_src'):
                        header['nw_src'] = header['ipv6_src']
                        del header['ipv6_src']
                    if header.has_key('ipv6_dst'):
                        header['nw_dst'] = header['ipv6_dst']
                        del header['ipv6_dst']
                elif header['eth_type'] == 0x800:
                    if header.has_key('ipv4_src'):
                        header['nw_src'] =header['ipv4_src']
                        del header['ipv4_src']
                    if header.has_key('ipv4_dst'):
                        header['nw_dst'] = header['ipv4_dst']
                        del header['ipv4_dst']

            flows.append({'match': header,
                          'packet_count': stat.packet_count,
                          'priority' : priority
                          })
            dur_sec = stat.duration_sec

            if not prefix:
                continue

            if(not prefix_bytes.has_key(prefix)):
                prefix_bytes[prefix] = {}
                prefix_bytes[prefix]["tx"] = 0
                prefix_bytes[prefix]["rx"] = 0
                if d:
                    prefix_bytes[prefix][d] += stat.byte_count

        for prefix in prefix_bytes:
            for d in ("rx","tx"):
                old_bytes = self.prefix_bytes[prefix][d]
                new_bytes = prefix_bytes[prefix][d]
                bytes = new_bytes - old_bytes
                #if we are less than the previous counter then we re-balanced
                #set back to 0 and start again
                if(bytes < 0):
                    self.prefix_bytes[prefix][d] = 0
                    bytes = 0

                if(stats_et == None):
                    stats_et = 0

                try:
                    rate = bytes / float(int(stats_et))
                except ZeroDivisionError:
                    self.logger.debug("Division by zero, rate = 0")
                    rate = 0

                prefix_bps[prefix][d] = rate
                self.prefix_bytes[prefix][d] = prefix_bytes[prefix][d]

        #--- update the balancer
        for prefix in prefix_bps.keys():
          rx = prefix_bps[prefix]["rx"]
          tx = prefix_bps[prefix]["tx"]
          self.api.updatePrefixBW("%016x" % dpid, prefix, tx, rx)
        
        self.api.TimeoutFlows("%016x" % dpid, flows)

    def process_flow_stats_of10(self, stats, dp):
        self.logger.debug("flow stat processor")
        self.logger.debug("flows stats: " + str(len(stats)))
        #--- figure out the time since last stats
        prefix_bps = defaultdict(lambda: defaultdict(int))
        prefix_bytes = {}
        flows = []
        dpid = dp.id
        ofproto = dp.ofproto
        old_time = None
        if (self.lastStatsTime.has_key(dpid)):
            old_time = self.lastStatsTime[dpid]
        now = int(time.time())

        stats_et = None
        if(old_time != None):
            stats_et = now - old_time

        self.lastStatsTime[dpid] = now
        
        for stat in stats:
            priority = stat.priority
            dur_sec = stat.duration_sec
            in_port = stat.match.in_port
            src_mask = 32 - ((stat.match.wildcards & ofproto_v1_0.OFPFW_NW_SRC_MASK) >> ofproto_v1_0.OFPFW_NW_SRC_SHIFT)
            dst_mask = 32 - ((stat.match.wildcards & ofproto_v1_0.OFPFW_NW_DST_MASK) >> ofproto_v1_0.OFPFW_NW_DST_SHIFT)
            if(stat.match.dl_type == 34525):
                prefix = ipaddr.IPv6Network("::/128")
                dir = "tx"
            elif(src_mask > 0):
                #--- this is traffic TX from target prefix
                id = ipaddr.IPv4Address(stat.match.nw_src)
                prefix = ipaddr.IPv4Network(str(id)+"/"+str(src_mask))  
                dir  = "tx"
            elif(dst_mask > 0):
                #--- this is traffic RX from target prefix
                id = ipaddr.IPv4Address(stat.match.nw_dst)
                prefix = ipaddr.IPv4Network(str(id)+"/"+str(dst_mask))
                dir = "rx"
            else:
                self.logger.debug("Flow:" + str(stat.match))
                #--- no mask, lets skip
                continue
        
            
            if(not prefix_bytes.has_key(prefix)):
                prefix_bytes[prefix] = {}
                prefix_bytes[prefix]["tx"] = 0
                prefix_bytes[prefix]["rx"] = 0

            prefix_bytes[prefix][dir] += stat.byte_count

            match = stat.match.__dict__
            wildcards = stat.match.wildcards
            del match['dl_dst']
            del match['dl_src']
            del match['wildcards'] 
            if match['dl_type'] == 2048:
                if match['nw_src'] != 0:
                    id = ipaddr.IPv4Address(stat.match.nw_src)
                    if src_mask > 0:
                          match['nw_src'] = ipaddr.IPv4Network(str(id)+"/"+str(src_mask))
                    else:
                        match['nw_src'] = ipaddr.IPv4Network(str(id))
                if match['nw_dst'] != 0:
                    id = ipaddr.IPv4Address(stat.match.nw_dst)
                    if dst_mask > 0:
                        match['nw_dst'] = ipaddr.IPv4Network(str(id)+"/"+str(dst_mask))
                    else:
                        match['nw_dst'] = ipaddr.IPv4Network(str(id))
                

            if(match.has_key('dl_type') and match['dl_type'] != 34525):
                del match['dl_type']

            if(match['dl_vlan_pcp'] == 0):
                del match['dl_vlan_pcp']

            if(match['dl_vlan'] == 0):
                del match['dl_vlan']

            if(match['nw_proto'] == 0):
                del match['nw_proto']

            if(match['nw_tos'] == 0):
                del match['nw_tos']
                
            if(match['nw_src'] == 0):
                del match['nw_src']
            
            if(match['nw_dst'] == 0):
                del match['nw_dst']

            if(match['tp_src'] == 0):
                del match['tp_src']

            if(match['tp_dst'] == 0):
                del match['tp_dst']

            if(match['in_port'] == 0):
                del match['in_port']
            else:
                match['phys_port'] = int(match['in_port'])
                del match['in_port']
                
            flows.append({'match': match,
                          'wildcards': wildcards,
                          'packet_count': stat.packet_count,
                          'priority' : priority
                          })
            
            
        for prefix in prefix_bytes:
            for dir in ("rx","tx"):
                old_bytes = self.prefix_bytes[prefix][dir]
                new_bytes = prefix_bytes[prefix][dir]
                bytes = new_bytes - old_bytes
                #if we are less than the previous counter then we re-balanced
                #set back to 0 and start again
                if(bytes < 0):
                    self.prefix_bytes[prefix][dir] = 0
                    bytes = 0

                if(stats_et == None):
                    stats_et = 0

                try:
                    rate = bytes / float(int(stats_et))
                except ZeroDivisionError:
                    self.logger.debug("Division by zero, rate = 0")
                    rate = 0
            
                prefix_bps[prefix][dir] = rate
                self.prefix_bytes[prefix][dir] = prefix_bytes[prefix][dir]
        

        #--- update the balancer
        for prefix in prefix_bps.keys():
	  rx = prefix_bps[prefix]["rx"]
          tx = prefix_bps[prefix]["tx"]
          self.api.updatePrefixBW("%016x" % dpid, prefix, tx, rx)

        self.api.TimeoutFlows("%016x" % dpid, flows)
          
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

	#--- update scipass utilization stats for ports

        #self.logger.info('datapath         port     '
        #                 'rx-pkts  rx-bytes rx-error '
        #                 'tx-pkts  tx-bytes tx-error')
        #self.logger.info('---------------- -------- '
        #                 '-------- -------- -------- '
        #                 '-------- -------- --------')
        #for stat in sorted(body, key=attrgetter('port_no')):
        #    self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d', 
        #                     ev.msg.datapath.id, stat.port_no,
        #                     stat.rx_packets, stat.rx_bytes, stat.rx_errors,
        #                     stat.tx_packets, stat.tx_bytes, stat.tx_errors)

