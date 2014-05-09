# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.

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
from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ether
from ryu.lib import hub

import socket
import ipaddr 

from collections import defaultdict
from SimpleBalancer import SimpleBalancer


"""
 Forwarding rule Priorities
   BlackList  
   WhiteList
   Balancer 
   Default



"""


class SciPass(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(SciPass,self).__init__(*args,**kwargs)
        self.datapaths = {}
        self.isactive = 1
        self.statsInterval = 5
        self.balanceInterval = 15 
	self.bal = None

        self.stats_thread = hub.spawn(self._stats_loop)
        self.balance_thread = hub.spawn(self._balance_loop)

	self.ports = defaultdict(dict);
        self.prefix_bytes = defaultdict(lambda: defaultdict(int))
        self.lastStatsTime = None
        self.flowmods = []
 
     
    def initFlows(self):
      """this is called after the switch joins, this needs refactoring as switches can come and go"""

      #--- bootstrap hack, need to figure out where to init and also how we want to support multiple ranges
      if(self.bal == None):

        bal = SimpleBalancer(
                        maxPrefixes             = 64,
                        mostSpecificPrefixLen   = 29,
                        leastSpecificPrefixLen  = 24,
                        ignoreSensorLoad        = 1,
                        ignorePrefixBW          = 0,
                        sensorLoadMinThresh     = .25,
                        sensorLoadDeltaThresh   = .05)

        bal.registerAddPrefixHandler(self.addPrefix)
        bal.registerDelPrefixHandler(self.delPrefix)
        bal.registerMovePrefixHandler(self.movePrefix)

        self.bal   = bal
        ports      = self.ports

        test       = ipaddr.IPv4Network('10.0.13.0/24')
        prefixList = bal.splitPrefixForSensors(test,2)

	#--- flush the rules
        self.flushRules()	

        #--- push rules to forward ARP
        self.pushArpRule(in_port=9,
                        out_port=10)

        self.pushArpRule(in_port=10,
                        out_port=9)



        #--- add the network , the port mapping is crap but ok for now
        for x in range(0,2):
          id = str(x)
          port =  x+9;
          ports["net"][id] = port

        #--- add the fw , the port mapping is crap but ok for now
        for x in range(0,2):
          id = str(x)
          port = x+11;
          ports["fw"][id] = port

        #--- add the sensors, the port mapping is crap but ok for now
        for x in range(1,3):
          id = str(x)
          bal.addSensor(id)
          ports["sensor"][id] = x
          bal.addSensorPrefix(id,prefixList[x-1])

      else:
        #---- we already have the flows just repush them
	self.synchRules()

    def flushRules(self):
      #--- pushes a mode to remove all flows from switch 
      #--- yep thats a hack, need to think about what multiple switches means for scipass
      datapath = self.datapaths.values()[0]
      ofp      = datapath.ofproto
      parser   = datapath.ofproto_parser

      # --- create flowmod to control traffic from the prefix to the interwebs
      match = parser.OFPMatch()
      mod = parser.OFPFlowMod(datapath,match,0,ofp.OFPFC_DELETE)

      #--- remove mods in the flowmod cache
      self.flowmods = [] 

 
      #--- if dp is active then push the rules
      if(datapath.is_active == True):
        datapath.send_msg(mod)
      

    def addPrefix(self,sensor,prefix):
      self.logger.debug("Add sensor: "+sensor+" prefix "+str(prefix))
      north_net_port = self.ports["net"]["0"]
      south_net_port = self.ports["net"]["1"]
      sensor_port    = self.ports["sensor"][sensor]

      net    = int(prefix)
      masklen = prefix.prefixlen

      assert 0 < masklen <= 32

      self.pushPrefixSensorFlowMod(priority=40000+masklen,
				in_port=north_net_port,
				out_port=south_net_port,
				sensor_port=sensor_port,
				nw_dst=net,
				nw_dst_mask=masklen,
				)

      self.pushPrefixSensorFlowMod(priority=40000+masklen,
                                in_port=south_net_port,
                                out_port=north_net_port,
                                sensor_port=sensor_port,
                                nw_src=net,  
                                nw_src_mask=masklen,
				)

    def delPrefix(self,sensor,prefix):
      self.logger.debug("Del sensor: "+sensor+" prefix "+str(prefix))
      north_net_port = self.ports["net"]["0"]
      south_net_port = self.ports["net"]["1"]
      sensor_port    = self.ports["sensor"][sensor]

      net    = int(prefix)
      masklen = prefix.prefixlen

      assert 0 < masklen <= 32

      datapath = self.datapaths.values()[0]
      ofp      = datapath.ofproto

      self.pushPrefixSensorFlowMod(priority=40000+masklen,
				command=ofp.OFPFC_DELETE_STRICT,
                                in_port=north_net_port,
                                out_port=south_net_port,
                                sensor_port=sensor_port,
                                nw_dst=net,
                                nw_dst_mask=masklen,
                                )

      self.pushPrefixSensorFlowMod(priority=40000+masklen,
				command=ofp.OFPFC_DELETE_STRICT,
                                in_port=south_net_port,
                                out_port=north_net_port,
                                sensor_port=sensor_port,
                                nw_src=net,
                                nw_src_mask=masklen,
                                )

    def movePrefix(self,oldSensor,newSensor,prefix):
      self.logger.debug("Move prefix "+str(prefix)+" from "+oldSensor+" to "+newSensor)
      #--- openflow deletes are based on match criterial, we cant add then delete because the delete would hit both
      self.delPrefix(newSensor,prefix)
      self.addPrefix(oldSensor,prefix)


    def synchRules(self):
      #--- routine to syncronize the rules to the DP
      #--- currently just pushes, somday should diff

      #--- yep thats a hack, need to think about what multiple switches means for scipass
      datapath = self.datapaths.values()[0]
      self.logger.debug('synch rules on DP: %016x', datapath.id)
      if(datapath.is_active == True):
          for mod in self.flowmods:
            datapath.send_msg(mod)


    def pushArpRule(self,in_port=None,out_port=None ):
      #--- pushes a rule to allow arp from in to out
       #--- yep thats a hack, need to think about what multiple switches means for scipass
      datapath = self.datapaths.values()[0]
      ofp      = datapath.ofproto
      parser   = datapath.ofproto_parser

      # --- create flowmod to control traffic from the prefix to the interwebs
      match = parser.OFPMatch(
                               dl_type=ether.ETH_TYPE_ARP,
                               in_port=in_port)

      actions = [parser.OFPActionOutput(out_port, 0)]

      mod = parser.OFPFlowMod(
                                datapath=datapath,
                                match=match,
                                cookie=0,
                                command=ofp.OFPFC_ADD,
                                idle_timeout=0,
                                hard_timeout=0,
                                actions=actions)

      #--- push mods to the array
      self.flowmods.append(mod)

      #--- if dp is active then push the rules
      if(datapath.is_active == True):
        datapath.send_msg(mod)


    #--- command=0, 0 == OFPFC_ADD = 0 # New flow. -- not sure how to cleanly reference as a default value
    def pushPrefixSensorFlowMod(self,command=0,in_port=None,out_port=None,priority=None,sensor_port=None,nw_src=None,nw_src_mask=None,nw_dst=None,nw_dst_mask=None):
      #--- yep thats a hack, need to think about what multiple switches means for scipass
      datapath = self.datapaths.values()[0]
      ofp      = datapath.ofproto
      parser   = datapath.ofproto_parser

      # --- create flowmod to control traffic from the prefix to the interwebs
      match = parser.OFPMatch(
                               dl_type=ether.ETH_TYPE_IP,
                               in_port=in_port,
                               nw_src=nw_src,
                               nw_src_mask=nw_src_mask,
			       nw_dst=nw_dst,
			       nw_dst_mask=nw_dst_mask)

      actions = [parser.OFPActionOutput(out_port, 0),
                 parser.OFPActionOutput(sensor_port, 0)]

      mod = parser.OFPFlowMod(
                                datapath=datapath,
                                priority=priority,
                                match=match,
                                cookie=0,
                                command=command,
                                idle_timeout=0,
                                hard_timeout=0,
                                actions=actions)

      #--- update local flowmod cache 
      if(command == ofp.OFPFC_ADD):
        self.flowmods.append(mod)

      if(command == ofp.OFPFC_DELETE_STRICT):
        try:
          self.flowmods.remove(mod)
        except:
          pass

      #--- if dp is active then push the rules
      if(datapath.is_active == True):
        datapath.send_msg(mod)



    #def delPrefix(self,sensor,prefix):
    #  self.logger.debug("Del: sensor: "+sensor+" prefix "+str(prefix))

    #def movePrefix(self,oldSensor,newSensor,prefix):
    #  self.logger.debug("move:  prefix "+str(prefix)+" from "+oldSensor+" to "+newSensor)


    def _stats_loop(self):
        while 1:
          #--- send stats request
          for dp in self.datapaths.values():
              self._request_stats(dp)
          
          #--- sleep
          hub.sleep(self.statsInterval)

    def _balance_loop(self):
      while 1:
        if( self.bal):
          #--- tell the system to rebalance
          self.bal.balance()
          self.logger.info(self.bal.showStatus())
        #--- sleep
        hub.sleep(self.balanceInterval)

    def _request_stats(self,datapath):
        #self.logger.debug('send stats request: %016x', datapath.id)
        ofp    = datapath.ofproto
        parser = datapath.ofproto_parser


        
        cookie = cookie_mask = 0
        match  = parser.OFPMatch()
        req    = parser.OFPFlowStatsRequest(	datapath, 
						0,
						match,
        					#ofp.OFPTT_ALL,
						0xff,
        					ofp.OFPP_NONE)
						#0xffffffff,
        					#cookie, 
						#cookie_mask,
        					#match)
        datapath.send_msg(req)

        req = parser.OFPPortStatsRequest(datapath, 0, ofp.OFPP_NONE)
        datapath.send_msg(req)



    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath

		#--- start the balancing act
		self.initFlows();

        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]


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
            self.logger.info("port modified %s state %s", port_no,link_state)
            #--- need to check the state to see if port is down
            
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        
        #--- figure out the time since last stats
	old_time = self.lastStatsTime
        self.lastStatsTime = int(time.time()) 
	stats_et = None
        if(old_time != None):
	  stats_et = self.lastStatsTime - old_time 
        
        body = ev.msg.body



        ofproto = ev.msg.datapath.ofproto

	prefix_bps = defaultdict(lambda: defaultdict(int))
        #--- update scipass utilization stats for forwarding rules
        for stat in body:
          dur_sec = stat.duration_sec
	  in_port = stat.match.in_port
          src_mask = 32 - ((stat.match.wildcards & ofproto.OFPFW_NW_SRC_MASK) >> ofproto.OFPFW_NW_SRC_SHIFT)
          dst_mask = 32 - ((stat.match.wildcards & ofproto.OFPFW_NW_DST_MASK) >> ofproto.OFPFW_NW_DST_SHIFT)

          if(src_mask > 0):
            #--- this is traffic TX from target prefix
            id   = ipaddr.IPv4Address(stat.match.nw_src)
            prefix = ipaddr.IPv4Network(str(id)+"/"+str(src_mask))  
            dir  = "tx"

          elif(dst_mask > 0):
            #--- this is traffic RX from target prefix
            id   = ipaddr.IPv4Address(stat.match.nw_dst)
            prefix = ipaddr.IPv4Network(str(id)+"/"+str(dst_mask))
            dir = "rx"
          else:
            #--- no mask, lets skip
            continue

          raw_bytes = stat.byte_count
          old_bytes = self.prefix_bytes[prefix][dir]
          self.prefix_bytes[prefix][dir] = raw_bytes
          bytes = raw_bytes - old_bytes
          et = stats_et 
          if(et == None or dur_sec < et):
            et = dur_sec

          try:
            rate = bytes / float(et)
          except ZeroDivisionError:
            rate = 0

          prefix_bps[prefix][dir] = rate
 

        #--- update the balancer
        for prefix in prefix_bps.keys():
	  rx = prefix_bps[prefix]["rx"]
          tx = prefix_bps[prefix]["tx"]
          self.bal.setPrefixBW(prefix,tx,rx) 
 

        #--- tell the system to rebalance
        #self.bal.balance()
        #self.logger.info(self.bal.showStatus())

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

