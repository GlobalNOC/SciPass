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
import time
import ipaddr
import pprint
import libxml2
from SimpleBalancer import SimpleBalancer

class SciPassApi:
  """SciPass API for signaling when a flow is known good or bad"""
  def __init__(  self , *_args, **_kwargs):
    logger = _kwargs['logger']

    if(logger == None):
      logging.basicConfig()
      self.logger = logging.getLogger(__name__)
    else:
      self.logger = logger

    self.whiteList = []
    self.blackList = []
    self.switchForwardingChangeHandlers = []

    self._processConfig("/home/aragusa/SciPass/etc/SciPass.xml")
    
  def registerForwardingStateChangeHandler(self, handler):
    self.switchForwardingChangeHandlers.append(handler)

  def good_flow(self, obj):
    #turn this into a 
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(obj)

    in_port = 0
    out_port = 0

    #need to figure out the lan and wan ports
    for port in self.config[dpid][domain]['ports']:
      if(port['type'] == "lan"):
        for prefix in port.prefixes:
          if(prefix.prefix.Contains( obj.nw_src )):
            in_port = port['of_port_id']
      if(port['type'] == "wan"):
        out_port = port['of_port_id']
 
    if(in_port == 0 or out_port == 0):
      self.logger.error("unable to find either an output or an input port")
   
    obj['phys_port'] = in_port

    actions = [{"type": output, 
                "port": out_port}]

    if(obj.idle_timeout == None):
      idle_timout  = self.config[dpid][name]['default_idle_timeout']
    else:
      idle_timeout = obj.idle_timeout
      
    if(obj.hard_timeout == None):
      hard_timeout = self.config[dpid][name]['default_hard_timeout']
    else:
      hard_timeout = obj.hard_timeout
      
    if(obj.priority == None):
      priority = self.config[dpid][name]['default_whitelist_priority']
    else:
      priority = obj.priority

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = obj,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )
    
    obj['phys_port'] = out_port

    actions = [{"type": output,
                "port": in_port}]
    
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = obj,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )
    
    results = {}
    results['success'] = 1
    return results

  def bad_flow(self, obj):
    #turn this into a
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(obj)

    in_port = 0
    out_port = 0
    #need to figure out the lan and wan ports
    for port in self.config[dpid][domain]['ports']:
      if(port['type'] == "lan"):
        for prefix in port.prefixes:
          if(prefix.prefix.Contains( obj.nw_src )):
            in_port = port['of_port_id']
      if(port['type'] == "wan"):
        out_port = port['of_port_id']

    if(in_port == 0 or out_port == 0):
      self.logger.error("unable to find either an output or an input port")

    obj['phys_port'] = in_port

    #drop so empty actions
    actions = []
    if(obj.idle_timeout == None):
      idle_timout  = self.config[dpid][name]['default_idle_timeout']
    else:
      idle_timeout = obj.idle_timeout

    if(obj.hard_timeout == None):
      hard_timeout = self.config[dpid][name]['default_hard_timeout']
    else:
      hard_timeout = obj.hard_timeout

    if(obj.priority == None):
      priority = self.config[dpid][name]['default_blacklist_priority']
    else:
      priority = obj.priority

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = obj,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )

    obj['phys_port'] = out_port

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = obj,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )

    results = {}
    results['success'] = 1
    return results

  def get_bad_flow(self):
    return self.whiteList

  def get_good_flow(self):
    return self.blackList

  def _processConfig(self, xmlFile):
    self.logger.error("Processing Config file")
    doc = libxml2.parseFile(xmlFile)
    ctxt = doc.xpathNewContext()
    #parse the xml file
    switches = ctxt.xpathEval("//SciPass/switch")
    config = {}
    for switch in switches:
      ctxt.setContextNode(switch)
      dpid = switch.prop("dpid")
      self.logger.error("Switch DPID: " + str(dpid))
      config[dpid] = {}
      domains = ctxt.xpathEval("domain")
      for domain in domains:
        ctxt.setContextNode(domain)
        name = domain.prop("name")
        mode = domain.prop("mode")
        status = domain.prop("admin_status")
        max_prefixes = domain.prop("max_prefixes")
        most_specific_len = domain.prop("most_specific_prefix_len")
        least_specific_len = domain.prop("least_specific_preifx_len")
        idle_timeout = domain.prop("idle_timeout")
        hard_timeout = domain.prop("hard_timeout")
        default_blacklist_priority = domain.prop("blacklist_priority")
        default_whitelist_priority = domain.prop("whitelist_priority")
        sensorLoadMinThreshold = domain.prop("sensor_min_load_threshold")
        sensorLoadDeltaThreshhold = domain.prop("sensor_load_delta_threshold")
        self.logger.error("Adding Domain: name: %s, mode: %s, status: %s", name, mode, status)
        config[dpid][name] = {}
        config[dpid][name]['mode'] = mode
        config[dpid][name]['status'] = status
        config[dpid][name]['max_prefixes'] = max_prefixes
        config[dpid][name]['most_specific_prefix_len'] = most_specific_len
        config[dpid][name]['least_specific_prefix_len'] = least_specific_len
        config[dpid][name]['idle_timeout'] = idle_timeout
        config[dpid][name]['hard_timeout'] = hard_timeout
        config[dpid][name]['default_blacklist_priority'] = default_blacklist_priority
        config[dpid][name]['default_whitelist_priority'] = default_whitelist_priority
        config[dpid][name]['sensor_load_min_threshold'] = sensorLoadMinThreshold
        config[dpid][name]['sensor_load_delta_threshold'] = sensorLoadDeltaThreshhold
        config[dpid][name]['sensor_ports'] = {}
        config[dpid][name]['ports'] = {}
        config[dpid][name]['ports']['lan'] = []
        config[dpid][name]['ports']['wan'] = []
        config[dpid][name]['ports']['fw_lan'] = []
        config[dpid][name]['ports']['fw_wan'] = []
        #create a simple balancer
        config[dpid][name]['balancer'] = SimpleBalancer( logger = self.logger,
                                                         maxPrefixes = max_prefixes,
                                                         mostSpecificPrefixLen = most_specific_len,
                                                         sensorLoadMinThresh = sensorLoadMinThreshold,
                                                         sensorLoadDeltaThresh = sensorLoadDeltaThreshhold,
                                                         leastSpecificPrefixLen = least_specific_len) 
        #register the methods
        config[dpid][name]['balancer'].registerAddPrefixHandler(lambda x, y : this.addPrefix(dpid = dpid,
                                                                                            domain_name = name,
                                                                                            sensor_id = x,
                                                                                            prefix = y))

        config[dpid][name]['balancer'].registerDelPrefixHandler(lambda x, y : this.delPrefix(dpid = dpid,
                                                                                            domain_name = name,
                                                                                            sensor_id = x,
                                                                                            prefix = y))

        config[dpid][name]['balancer'].registerMovePrefixHandler(lambda x, y, z : this.movePrefix(dpid = dpid,
                                                                                              domain_name = name,
                                                                                              old_sensor_id = x,
                                                                                              new_sensor_id = y,
                                                                                              prefix = z
                                                                                              ))

        ports = ctxt.xpathEval("port")
        sensor_ports = ctxt.xpathEval("sensor_ports")

        for port in sensor_ports:
          sensor = {port_id: port.prop("of_port_id"),
                                bw: port.prop("bw"),
                    sensor_id: port.prop("sensor_id"),
                    admin_status: port.prop("admin_status"),
                    description: port.prop("description")}
          config[dpid][name]['sensor_ports'][sensor['sensor_id']] = sensor
          config[dpid][name]['balancer'].addSensor(sensor)

        for port in ports:
          ctxt.setContextNode(port)
          ptype = port.prop("type")
          prefixes = ctxt.xpathEval("prefix")
          prefixes_array = []
          for prefix in prefixes:
            prefix_obj = {}
            if(prefix.prop("type") == "v4" or prefix.prop("type") == "ipv4"):
              prefix_obj = {"type": prefix.prop("type"),
                            "prefix_str": prefix.getContent(),
                            "prefix": ipaddr.IPv4Network(prefix.getContent())}
            else:
              prefix_obj = {"type": prefix.prop("type"),
                            "prefix_str": prefix.getContent(),
                            "prefix": ipaddr.IPv6Network(prefix.getContent())}
            prefixes_array.append(prefix_obj)
            #TODO
            #todo push the prefixes to sensors
            config[dpid][name]['ports'][ptype].append({"port_id": port.prop("of_port_id"),
                                                       "name": port.prop("name"),
                                                       "description": port.prop("description"),
                                                       "prefixes": prefixes_array
                                                       })
        
    self.config = config      
    doc.freeDoc()
    ctxt.xpathFreeContext()

  def switchJoined(self, dpid):
    #check to see if we are suppose to operate on this switch
    if(self.config.has_key(dpid)):
      #first flush the rules
      self._flushRules(dpid)
      #now for each domain push the initial flows 
      #and start the balancing process
      for domain in self.config[dpid]:
        if(domain['mode'] == "SciDMZ" and len(domain['fw_lan']) > 0 and len(domain['fw_wan']) > 0):
          #we have firewals configured
          #setup the rules to them
          self.logger.error("Mode is Science DMZ")
          
        elif(domain['mode'] == "InlineIDS"):
          #no firewall
          self.logger.error("Mode is Inline IDS")
          
        elif(domain['mode'] == "Balancer"):
          #just balancer no other forwarding
          self.logger.error("Mode is Balancer")
        
            
  def _resetSwitchForwarding(self,dpid):
    self.resetSwitchForwarding(dpid)
  
  def addPrefix(self, dpid=None, domain_name=None, sensor_id=None, prefix=None):
    self.logger.debug("Add Prefix")
    #find the north and south port

    in_port  = 0
    out_port = 0
    fw_lan   = 0
    fw_wan   = 0
    #need to figure out the lan and wan ports
    for port in self.config[dpid][domain_name]['ports']:
      if(port['type'] == "lan"):
        for prefix in port.prefixes:
          if(prefix.prefix.Contains( obj.nw_src )):
            in_port = port['of_port_id']
      if(port['type'] == "wan"):
        out_port = port['of_port_id']
      if(port['type'] == "fw_lan"):
        fw_lan = port['of_port_id']
      if(port['type'] == "fw_wan"):
        fw_wan == port['of_port_id']

    if(in_port == 0 or out_port == 0):
      self.logger.error("unable to find either an output or an input port")
    
    header = {"nw_src":      int(prefix),
              "nw_src_mask": int(prefix.prefixlen),
              "phys_port":   int(in_port),
              "dl_type":     ether.ETH_TYPE_ID}

    actions = []
    #output to sensor (basically this is the IDS balance case)
    actions.append({"type": "output",
                    "port": self.config[dpid][domain_name]['sensor_ports'][sensor_id]})
    if(self.config[dpid][domain_name]['mode'] == "ScienceDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
      #append the FW or other destination
      if(fw_lan == 0):
        actions.append({"type": "output",
                        "port": out_port})
      else:
        actions.append({"type": "output",
                        "port": fw_lan})

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )    

    header = {"nw_dst":      int(prefix),
              "nw_dst_mask": int(prefix.prefixlen),
              "phys_port":   int(out_port),
              "dl_type":     ether.ETH_TYPE_ID }
    
    actions = []
    #output to sensor (basically this is the IDS balance case)
    actions.append({"type": "output",
                    "port": self.config[dpid][domain_name]['sensor_ports'][sensor_id]})
    if(self.config[dpid][domain_name]['mode'] == "ScienceDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
      #append the FW or other destination
      if(fw_lan == 0):
        actions.append({"type": "output",
                        "port": in_port})
      else:
        actions.append({"type": "output",
                        "port": fw_wan})

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = ofp.OFPFC_ADD,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )

  def delPrefix(self, dpid=None, domain_name=None, sensor_id=None, prefix=None):
    self.logger.debug("Remove Prefix")

    in_port  = 0
    out_port = 0
    fw_lan   = 0
    fw_wan   = 0

    #need to figure out the lan and wan ports
    for port in self.config[dpid][domain_name]['ports']:
      if(port['type'] == "lan"):
        for prefix in port.prefixes:
          if(prefix.prefix.Contains( obj.nw_src )):
            in_port = port['of_port_id']
      if(port['type'] == "wan"):
        out_port = port['of_port_id']
      if(port['type'] == "fw_lan"):
        fw_lan = port['of_port_id']
      if(port['type'] == "fw_wan"):
        fw_wan == port['of_port_id']

    if(in_port == 0 or out_port == 0):
      self.logger.error("unable to find either an output or an input port")

    header = {"nw_src":      int(prefix),
              "nw_src_mask": int(prefix.prefixlen),
              "phys_port":   int(in_port),
              "dl_type":     ether.ETH_TYPE_ID}

    actions = []
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = ofp.OFPFC_DELETE_STRICT,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )

    header = {"nw_dst":      int(prefix),
              "nw_dst_mask": int(prefix.prefixlen),
              "phys_port":   int(out_port),
              "dl_type":     ether.ETH_TYPE_ID }

    actions = []
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = ofp.OFPFC_DELETE_STRICT,
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority )

  def movePrefix(self, dpid = None, domain_name=None, new_sensor_id=None, old_sensor_id=None, prefix=None):
    self.logger.debug("move prefix")
    #delete and add the prefix
    self.delPrefix(dpid, domain_name, old_sensor_id, prefix)
    self.addPrefix(dpid, domain_name, new_sensor_id, prefix)

  def remove_flow(self, ev):
    self.logger.debug("remove flow")
    
  def port_status(self, ev):
    self.logger.debug("port status handler")

  def update_prefix_bw(dpid, prefix, tx, rx):
    self.logger.debug("update_prefix_bw")
    
  def port_stats(self, ev):
    self.logger.debug("port stats handler")
