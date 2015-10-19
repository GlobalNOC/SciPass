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

from ryu import cfg
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ether
from ryu.ofproto import ofproto_v1_0
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

    #POST /scipass/flows/good_flow
    @route('scipass', '/scipass/flows/good_flow', methods=['PUT'])
    def good_flow(self, req):
        try:
            obj = eval(req.body)
        except SyntaxError:
            self.logger.error("Syntax Error processing good_flow signal %s", req.body)
            return Response(status=400)

        result = self.api.good_flow(obj)
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
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = { 'wsgi': WSGIApplication }
    
    def __init__(self, *args, **kwargs):
        super(Ryu,self).__init__(*args,**kwargs)
        #--- register for configuration options
        self.CONF.register_opts([
                cfg.StrOpt('SciPassConfig',default='/etc/SciPass/SciPass.xml',
                           help='where to find the SciPass config file'),
                ])
        
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
                      config_file = self.CONF.SciPassConfig )
        
        api.registerForwardingStateChangeHandler(self.changeSwitchForwardingState)

        self.api = api
        
        wsgi = kwargs['wsgi']
        wsgi.register(SciPassRest, {'api' : self.api})
        
    def changeSwitchForwardingState(self, dpid=None, header=None, actions=None, command=None, idle_timeout=None, hard_timeout=None, priority=1):
        #self.logger.error("Changing switch forwarding state")
        
        if(not self.datapaths.has_key(dpid)):
            self.logger.error("unable to find switch with dpid " + dpid)
            self.logger.error(self.datapaths)
            return
        
        datapath = self.datapaths[dpid]

        ofp      = datapath.ofproto
        parser   = datapath.ofproto_parser

        obj = {} 
        
        if(header.has_key('dl_type')):
            if(header['dl_type'] == None):
                obj['dl_type'] = None
            else:
                obj['dl_type'] = int(header['dl_type'])
        else:
            obj['dl_type'] = ether.ETH_TYPE_IP
            
        if(header.has_key('phys_port')):
            obj['in_port'] = int(header['phys_port'])
        else:
            obj['in_port'] = None
            
        if(header.has_key('nw_src')):
            obj['nw_src'] = int(header['nw_src'])
        else:
            obj['nw_src'] = None
             
        if(header.has_key('nw_src_mask')):
            obj['nw_src_mask'] = int(header['nw_src_mask'])
        else:
            obj['nw_src_mask'] = None
         
        if(header.has_key('nw_dst')):
            obj['nw_dst'] = int(header['nw_dst'])
        else:
            obj['nw_dst'] = None

        if(header.has_key('nw_dst_mask')):
            obj['nw_dst_mask'] = int(header['nw_dst_mask'])
        else:
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
            match = parser.OFPMatch( in_port     = obj['in_port'],
                                     nw_dst      = obj['nw_dst'],
                                     nw_dst_mask = obj['nw_dst_mask'],
                                     nw_src      = obj['nw_src'],
                                     nw_src_mask = obj['nw_src_mask'],
                                     tp_src      = obj['tp_src'],
                                     tp_dst      = obj['tp_dst'])
        else:
            
            match = parser.OFPMatch( in_port     = obj['in_port'],
                                     nw_dst      = obj['nw_dst'],
                                     nw_dst_mask = obj['nw_dst_mask'],
                                     nw_src      = obj['nw_src'],
                                     nw_src_mask = obj['nw_src_mask'],
                                     dl_type     = obj['dl_type'],
                                     tp_src      = obj['tp_src'],
                                     tp_dst      = obj['tp_dst'])
            
        #self.logger.error("Match: " + str(match))
        
        of_actions = []
        for action in actions:
            if(action['type'] == "output"):
                of_actions.append(parser.OFPActionOutput(int(action['port']),0))
                
        #self.logger.error("Actions: " + str(of_actions))
        if(command == "ADD"):
            command = ofp.OFPFC_ADD
        elif(command == "DELETE_STRICT"):
            command = ofp.OFPFC_DELETE_STRICT
        else:
            command = -1

        #self.logger.error("Sending flow mod with command: " + str(command))
        #self.logger.error("Datpath: " + str(datapath))

        mod = parser.OFPFlowMod( datapath     = datapath,
                                 priority     = int(priority),
                                 match        = match,
                                 cookie       = 0,
                                 command      = command,
                                 idle_timeout = int(idle_timeout),
                                 hard_timeout = int(hard_timeout),
                                 actions      = of_actions)

        if(datapath.is_active == True):
            datapath.send_msg(mod)
        else:
            self.logger.error("Device is not connected")

    def flushRules(self, dpid):
        if(not self.datapaths.has_key(dpid)):
            self.logger.error("unable to find switch with dpid " + dpid)
            return
        
        datapath = self.datapaths[dpid]
        ofp      = datapath.ofproto
        parser   = datapath.ofproto_parser

         # --- create flowmod to control traffic from the prefix to the interwebs
        match = parser.OFPMatch()
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
        req    = parser.OFPFlowStatsRequest(	datapath,
						0,
						match,
						0xff,
        					ofp.OFPP_NONE)


        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_NONE)
        datapath.send_msg(req)

    #handle the remove flow event so we know what to sync up when we do this
    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _remove_flow_handler(self, ev):
        msg = ev.msg
        self.api.remove_flow(msg)
        for flow in self.flows:
            if(flow.match == msg.match and flow.actions == msg.actions):
                self.flows.delete(flow)
                return
        self.logger.error("A flow was removed but we didn't know it was there!")

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
        reason     = msg.reason
        port_no    = msg.desc.port_no
        link_state = msg.desc.state

        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofproto.OFPPR_MODIFY:
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
        
           
    def process_flow_stats(self, stats, dp):
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
            
            dur_sec = stat.duration_sec
            in_port = stat.match.in_port
            src_mask = 32 - ((stat.match.wildcards & ofproto.OFPFW_NW_SRC_MASK) >> ofproto.OFPFW_NW_SRC_SHIFT)
            dst_mask = 32 - ((stat.match.wildcards & ofproto.OFPFW_NW_DST_MASK) >> ofproto.OFPFW_NW_DST_SHIFT)
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
                self.logger.error("Flow:" + str(stat.match))
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
            del match['dl_type']
            del match['wildcards']

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

            mask = 32 - ((wildcards & ofproto_v1_0.OFPFW_NW_SRC_MASK)
                         >> ofproto_v1_0.OFPFW_NW_SRC_SHIFT)
            match['nw_src_mask'] = mask

            mask = 32 - ((wildcards & ofproto_v1_0.OFPFW_NW_DST_MASK)
                         >> ofproto_v1_0.OFPFW_NW_DST_SHIFT)
            match['nw_dst_mask'] = mask

            flows.append({'match': match,
                          'wildcards': wildcards,
                          'packet_count': stat.packet_count
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

