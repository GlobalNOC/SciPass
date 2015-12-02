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
import copy
import libxml2
import json
import lxml
import sys                                                                     
from lxml import etree
from SimpleBalancer import SimpleBalancer
from SimpleBalancer import MaxFlowCountError

class SciPass:
  """SciPass API for signaling when a flow is known good or bad"""
  def __init__(  self , *_args, **_kwargs):
    self.logger = None
    self.configFile = None
    if(_kwargs.has_key('logger')):
      self.logger = _kwargs['logger']

    if(self.logger == None):
      logging.basicConfig()
      self.logger = logging.getLogger(__name__)


    if(_kwargs.has_key('config')):
      self.configFile = _kwargs['config']
    else:
      self.configFile = "/etc/SciPass/SciPass.xml"

    if(_kwargs.has_key('readState')):
      self.readState = _kwargs['readState']
    else:
      self.readState = False
      
    if(_kwargs.has_key('schema')):
      self.configFile = _kwargs['schema']
    else:
      self.schemaFile = "/etc/SciPass/SciPass.xsd"

    self.whiteList    = []
    self.blackList    = []
    self.idleTimeouts = []
    self.hardTimeouts = []
    self.switches     = []
    self.flowCount = 0
    self.switchForwardingChangeHandlers = []
    self._validateConfig(self.configFile, self.schemaFile)
    self._processConfig(self.configFile)

  def registerForwardingStateChangeHandler(self, handler):
    self.switchForwardingChangeHandlers.append(handler)

  def good_flow(self, obj):
    """process a good flow message and changes the forwarding state to reflect that"""
    #turn this into a 
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors

    #this case is a little bit more complicated than the bad_flow case
    #it is possible for there to be an interesting case where there are either multiple LAN
    #or multiple WAN ports

    #build our prefixes
    src_prefix = ipaddr.IPv4Network(obj['nw_src'])
    dst_prefix = ipaddr.IPv4Network(obj['nw_dst'])
    
    #find the switch, domain, lan, wan ports
    for dpid in self.config:
      for name in self.config[dpid]:
        
        used_wan_ports = []
        wan_action = []
        lan_action = []
        flows = []
        results = {}
        #set these now they are cheap and it makes the rest of it cleaner
        idle_timeout = 0
        priority = 0
        if(not obj.has_key('idle_timeout')):
          idle_timeout  = self.config[dpid][name]['idle_timeout']
        else:
          idle_timeout = obj['idle_timeout']
          
        if(not obj.has_key('priority')):
          priority = self.config[dpid][name]['default_whitelist_priority']
        else:
          priority = obj['priority']

        #step one figure out the actions :)
        #lets just calculate the wan ports involved here
        if len(self.config[dpid][name]['ports']['wan']) > 1:
          for port in self.config[dpid][name]['ports']['wan']:
            for prefix in port['prefixes']:
              if prefix['prefix'].Contains( src_prefix ):
                used_wan_ports.append(port['port_id'])
                wan_action.append({"type": "output",
                                   "port": port['port_id']})
                if prefix['prefix'].Contains( dst_prefix ):
                  used_wan_ports.append(port['port_id'])
                  wan_action.append({"type": "output",
                                     "port": port['port_id']})
        #if you only have 1 wan we don't require prefixes
        elif len(self.config[dpid][name]['ports']['wan']) == 1:
          used_wan_ports.append(self.config[dpid][name]['ports']['wan'][0]['port_id'])
          wan_action.append({"type": "output",
                             "port": self.config[dpid][name]['ports']['wan'][0]['port_id']})

        #lets just calculate the wan ports involved here
        for port in self.config[dpid][name]['ports']['lan']:
          for prefix in port['prefixes']:
            if prefix['prefix'].Contains( src_prefix ):
              lan_action.append({"type": "output",
                                 "port": port['port_id']})
            if prefix['prefix'].Contains( dst_prefix ):
              lan_action.append({"type": "output",
                                 "port": port['port_id']})



        #first lets process the LAN ports
        for port in self.config[dpid][name]['ports']['lan']:
          for prefix in port['prefixes']:
            #ok we'll see if the src matches
            if(prefix['prefix'].Contains( src_prefix )):
              header = self._build_header(obj,False)    
              header['phys_port'] = int(port['port_id'])
              match = self.stringify(header)
              status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                               domain       = name,
                                                               header       = header,
                                                               actions      = wan_action,
                                                               command      = "ADD",
                                                               idle_timeout = idle_timeout,
                                                               hard_timeout = 0,
                                                               priority     = priority )
              if status != 1:
                self.logger.error("Max flow limit reached.Could not add flow")
                results['success'] = 0
                return results
              else:
                flow = { 'dpid' : dpid, 'domain' : name, 'header' : match,
                        'actions' : wan_action,'priority' : priority }
                flows.append(flow)
                self.whiteList.append(flow)

              #now do the wan side (there might be multiple)
              for wan in used_wan_ports:
                header = self._build_header(obj,True)
                header['phys_port'] = int(wan)
                match = self.stringify(header)
                status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                                 domain       = name,
                                                                 header       = header,
                                                                 actions      = lan_action,
                                                                 command      = "ADD",
                                                                 idle_timeout = idle_timeout,
                                                                 hard_timeout = 0,
                                                                 priority     = priority )
                if status != 1:
                  self.logger.error("Max flow limit reached.Could not add flow")
                  #Delete the prev installed flows for this good flow.
                  self.delete_flows(flows)
                  results['success'] = 0
                  return results
                else:
                  flow = { 'dpid' : dpid, 'domain' : name,'header': match,
                           'actions' : lan_action,'priority' : priority }
                  flows.append(flow)
                  self.whiteList.append(flow)
                
            #check the other dir          
            if(prefix['prefix'].Contains( dst_prefix )):
              header = self._build_header(obj,True)
              header['phys_port'] = int(port['port_id'])
              match = self.stringify(header)
              status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                               domain       = name,
                                                               header       = header,
                                                               actions      = wan_action,
                                                               command      = "ADD",
                                                               idle_timeout = idle_timeout,
                                                               hard_timeout = 0,
                                                               priority     = priority)
              if status != 1:
                self.logger.error("Max flow limit reached.Could not add flow")
                self.delete_flows(flows)
                results['success'] = 0
                return results
              else:
                flow = { 'dpid' : dpid, 'domain' : name,'header' : match,
                         'actions' : wan_action,'priority' : priority }
                flows.append(flow)
                self.whiteList.append(flow)

              #now do the wan side (there might be multiple)
              for wan in used_wan_ports:
                header = self._build_header(obj,False)
                header['phys_port'] = int(wan)
                match = self.stringify(header)
                status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                                 domain       = name,
                                                                 header       = header,
                                                                 actions      = lan_action,
                                                                 command      = "ADD",
                                                                 idle_timeout = idle_timeout,
                                                                 hard_timeout = 0,
                                                                 priority     = priority )
                if status != 1:
                  self.logger.error("Max flow limit reached.Could not add  flow")
                  self.delete_flows(flows)
                  results['success'] = 0
                  return results
                else:
                  flow = { 'dpid' : dpid, 'domain' : name,'header' : match,
                           'actions' : lan_action,'priority' : priority }
                  flows.append(flow)
                  self.whiteList.append(flow)
    results['success'] = 1
    return results

  def _build_header(self, obj, reverse):
    header = {}
    if(obj.has_key('nw_src')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_dst'] = prefix
      else:
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_src'] = prefix
                
    if(obj.has_key('nw_dst')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_src'] = prefix
      else:
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_dst'] = prefix
    #OF10
    if(obj.has_key('tp_src')):
      if(reverse):
        header['tp_dst'] = int(obj['tp_src'])
      else:
        header['tp_src'] = int(obj['tp_src'])
        
    if(obj.has_key('tp_dst')):
      if(reverse):
        header['tp_src'] = int(obj['tp_dst'])
      else:
        header['tp_dst'] = int(obj['tp_dst'])
        

    #O13
    if(obj.has_key('tcp_src')):
      if(reverse):
        header['tcp_dst'] = int(obj['tcp_src'])
      else:
        header['tcp_src'] = int(obj['tcp_src'])
        
    if(obj.has_key('tcp_dst')):
      if(reverse):
        header['tcp_src'] = int(obj['tcp_dst'])
      else:
        header['tcp_dst'] = int(obj['tcp_dst'])
        
    if(obj.has_key('udp_src')):
      if(reverse):
        header['udp_dst'] = int(obj['udp_src'])
      else:
        header['udp_src'] = int(obj['udp_src'])
                                    
    if(obj.has_key('udp_dst')):
      if(reverse):
        header['udp_src'] = int(obj['udp_dst'])
      else:
        header['udp_dst'] = int(obj['udp_dst'])
  
    return header


  def bad_flow(self, obj):
    #turn this into a
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors

    src_prefix = ipaddr.IPv4Network(obj['nw_src'])
    dst_prefix = ipaddr.IPv4Network(obj['nw_dst'])
    flows = []
    results = {}
    #find all the lan ports
    for datapath_id in self.config:
      for name in self.config[datapath_id]:
        #just so we don't have to do this constantly!
        idle_timeout = 0
        if(not obj.has_key('idle_timeout')):
          idle_timeout  = self.config[datapath_id][name]['idle_timeout']
        else:
          idle_timeout = obj['idle_timeout']
        priority = 65535
        if(not obj.has_key('priority')):
          priority = self.config[datapath_id][name]['default_blacklist_priority']
        else:
          priority = obj['priority']

        for port in self.config[datapath_id][name]['ports']['lan']:
          for prefix in port['prefixes']:
            
            if(prefix['prefix'].Contains( src_prefix )):
              #actions drop
              actions = []

              #build a header based on what was sent
              header = self._build_header(obj,False) 
              
              if not self.config[datapath_id][name]['mode'] == "SimpleBalancer":
                #set the port of the header
                header['phys_port'] = int(port['port_id'])
              match = self.stringify(header)
              self.logger.debug("Header: " + str(header))

              status = self.fireForwardingStateChangeHandlers( dpid         = datapath_id,
                                                               domain       = name,
                                                               header       = header,
                                                               actions      = actions,
                                                               command      = "ADD",
                                                               idle_timeout = idle_timeout,
                                                               priority     = priority)
              if status != 1:
                  self.logger.error("Max flow limit reached.Could not add flow")
                  results['success'] = 0
                  return results
              else:
                flow = { 'dpid' : datapath_id, 'domain' : name,'header' : match,
                        'actions' : actions,'priority' : priority }
                flows.append(flow)
                self.blackList.append(flow)

              for wan in self.config[datapath_id][name]['ports']['wan']:
                #build a header based on what was set
                header = self._build_header(obj,True)
                
                #set the port
                header['phys_port'] = int(wan['port_id'])
                match = self.stringify(header)
                self.logger.debug("Header: " + str(header))

                status = self.fireForwardingStateChangeHandlers( dpid         = datapath_id,
                                                                 domain       = name,
                                                                 header       = header,
                                                                 actions      = actions,
                                                                 command      = "ADD",
                                                                 idle_timeout = idle_timeout,
                                                                 priority     = priority)
                
                if status != 1:
                  self.logger.error("Max flow limit reached.Could not add  flow")
                  self.delete_flows(flows)
                  results['success'] = 0
                  return results
                else:
                  flow = { 'dpid' : datapath_id, 'domain' : name,'header' : match,
                          'actions' : actions,'priority' : priority }
                  flows.append(flow)
                  self.blackList.append(flow)

            if(prefix['prefix'].Contains( dst_prefix )):
              #actions drop
              actions = []
              #build a header based on what was setn
              header = self._build_header(obj,True)
              
              if not self.config[datapath_id][name]['mode'] == "SimpleBalancer":
                #set the port
                header['phys_port'] = int(port['port_id'])
                match = self.stringify(header)
              self.logger.debug("Header: " + str(header))

              status = self.fireForwardingStateChangeHandlers( dpid         = datapath_id,
                                                               domain       = name,
                                                               header       = header,
                                                               actions      = actions,
                                                               command      = "ADD",
                                                               idle_timeout = idle_timeout,
                                                               priority     = priority)
              if status != 1:
                self.logger.error("Max flow limit reached.Could not add  flow")
                self.delete_flows(flows)
                results['success'] = 0
                return results
              else:
                flow = { 'dpid' : datapath_id, 'domain' : name,'header' : match,
                        'actions' : actions,'priority' : priority }
                flows.append(flow)
                self.blackList.append(flow)

              for wan in self.config[datapath_id][name]['ports']['wan']:
                #build a header based on what was set
                header = self._build_header(obj,False)
                #set the port
                header['phys_port'] = int(wan['port_id'])
                match = self.stringify(header)
                self.logger.debug("Header: " + str(header))
                status = self.fireForwardingStateChangeHandlers( dpid         = datapath_id,
                                                                 domain       = name,
                                                                 header       = header,
                                                                 actions      = actions,
                                                                 command      = "ADD",
                                                                 idle_timeout = idle_timeout,
                                                                 priority     = priority)
                if status != 1:
                  self.logger.error("Max flow limit reached.Could not add flow")
                  self.delete_flows(flows)
                  results['success'] = 0
                  return results
                else:
                  flow = { 'dpid' : datapath_id, 'domain' : name,'header' : match,
                          'actions' : actions,'priority' : priority }
                  flows.append(flow)
                  self.blackList.append(flow)
    results['success'] = 1
    return results

  def delete_flows(self, flows):
    if flows: 
      for flow in flows:
        self.fireForwardingStateChangeHandlers( dpid = flow['dpid'],
                                                domain = flow['domain'],
                                                header = flow['header'],
                                                command = "DELETE_STRICT",
                                                actions = flow['actions'],
                                                priority = flow['priority'] )
       

  def get_bad_flows(self):
    if self.blackList:
      return self.blackList
    return None

  def get_good_flows(self):
    if self.whiteList:
      return self.whiteList
    return None

  # gets the config info for a sensor along with its dpid and domain
  def _getSensorInfo(self, port_id):
    # loop through dpids
    for dpid in self.config:
      # loop through domains
      for domain_name, domain in self.config[dpid].iteritems():
        for group in self.config[dpid][domain_name]['sensor_groups']:
          for sensor in self.config[dpid][domain_name]['sensor_groups'][group]['sensors']:
            if (self.config[dpid][domain_name]['sensor_groups'][group]['sensors'][sensor]['port_id'] == port_id):
              return {
                "dpid": dpid,
                "domain": domain_name,
                "group": group,
                "sensor_info": self.config[dpid][domain_name]['sensor_groups'][group]['sensors'][sensor]
                }

  def setSensorStatus(self, port_id, status):
    info = self._getSensorInfo(port_id) 
    if(info == None): return
    # set sensor status 
    self.config[info.get('dpid')][info.get('domain')]['balancer'].setSensorStatus(
        info['sensor_info'].get('sensor_id'), 
        status
    )

  def _validateConfig(self, xmlFile, schema):
    self.logger.debug("validating Config File")
    with open(schema) as f:                                                
        doc = etree.parse(f)  
    try:
      schema = etree.XMLSchema(doc)
    except lxml.etree.XMLSchemaParseError as e:
      self.logger.error("Error Parsing schema" + str(e))
      sys.exit(1)

    with open(xmlFile) as f:
      config = etree.parse(f)
    try:
      schema.assertValid(config)
    except lxml.etree.DocumentInvalid as e:
      self.logger.error("Could not validate xml file against schema" + str(e))
      sys.exit(1)
    self.logger.debug("Completed Validation of config File...")
      

  def _processConfig(self, xmlFile):
    self.logger.debug("Processing Config file")
    doc = libxml2.parseFile(xmlFile)
    ctxt = doc.xpathNewContext()
    #parse the xml file
    switches = ctxt.xpathEval("//SciPass/switch")
    config = {}
    for switch in switches:
      ctxt.setContextNode(switch)
      dpid = switch.prop("dpid")
      self.logger.debug("Switch DPID: " + str(dpid))
      config[dpid] = {}
      domains = ctxt.xpathEval("domain")
      for domain in domains:
        ctxt.setContextNode(domain)
        name = domain.prop("name")
        mode = domain.prop("mode")
        status = domain.prop("admin_status")
        max_prefixes = domain.prop("max_prefixes")
        most_specific_len = domain.prop("most_specific_prefix_len")
        least_specific_len = domain.prop("least_specific_prefix_len")
        ipv6most_specific_len = domain.prop("ipv6most_specific_prefix_len")
        ipv6least_specific_len = domain.prop("ipv6least_specific_prefix_len")
        idle_timeout = domain.prop("idle_timeout")
        hard_timeout = domain.prop("hard_timeout")
        #because of all the priority stuff in the balancer we have to set the blacklist/whitelist priority to the max
        default_blacklist_priority = 65535
        default_whitelist_priority = 65535
        sensorLoadMinThreshold = domain.prop("sensor_min_load_threshold")
        sensorLoadDeltaThreshhold = domain.prop("sensor_load_delta_threshold")
        sensorConfigurableThreshold = domain.prop("sensor_configurable_threshold")
        ignore_sensor_load = domain.prop("ignore_sensor_load")
        ignore_prefix_bw = domain.prop("ignore_prefix_bw")
        max_flow_count = domain.prop("max_flow_count")
        self.logger.debug("Adding Domain: name: %s, mode: %s, status: %s", name, mode, status)

        config[dpid][name] = {}
        config[dpid][name]['mode'] = mode
        config[dpid][name]['status'] = status
        config[dpid][name]['max_prefixes'] = max_prefixes
        config[dpid][name]['most_specific_prefix_len'] = most_specific_len
        config[dpid][name]['least_specific_prefix_len'] = least_specific_len
        config[dpid][name]['ipv6most_specific_prefix_len'] = ipv6most_specific_len
        config[dpid][name]['ipv6least_specific_prefix_len'] = ipv6least_specific_len
        config[dpid][name]['idle_timeout'] = idle_timeout
        config[dpid][name]['hard_timeout'] = hard_timeout
        config[dpid][name]['default_blacklist_priority'] = default_blacklist_priority
        config[dpid][name]['default_whitelist_priority'] = default_whitelist_priority
        config[dpid][name]['sensor_load_min_threshold'] = sensorLoadMinThreshold
        config[dpid][name]['sensor_load_delta_threshold'] = sensorLoadDeltaThreshhold
        config[dpid][name]['sensor_configurable_threshold'] = sensorConfigurableThreshold
        config[dpid][name]['max_flow_count'] = max_flow_count
        if(ignore_prefix_bw == "true"):
          config[dpid][name]['ignore_prefix_bw'] = 1
        else:
          config[dpid][name]['ignore_prefix_bw'] = 0

        if(ignore_sensor_load == "true"):
          config[dpid][name]['ignore_sensor_load'] = 1
        else:
          config[dpid][name]['ignore_sensor_load'] = 0

        config[dpid][name]['sensor_groups'] = {}
        config[dpid][name]['ports'] = {}
        config[dpid][name]['ports']['lan'] = []
        config[dpid][name]['ports']['wan'] = []
        config[dpid][name]['ports']['fw_lan'] = []
        config[dpid][name]['ports']['fw_wan'] = []
        state = None
        if self.readState:
          prevState = "/var/run/" +  dpid +  name + ".json"
          try:
            with open(prevState) as data:    
              state = json.load(data)
              state = state[0]
              data.close()
          except IOError:
            state = None
        #create a simple balancer
        config[dpid][name]['balancer'] = SimpleBalancer( logger = self.logger,
                                                         maxPrefixes = max_prefixes,
                                                         ignoreSensorLoad = config[dpid][name]['ignore_sensor_load'],
                                                         ignorePrefixBW = config[dpid][name]['ignore_prefix_bw'],
                                                         mostSpecificPrefixLen = most_specific_len,
                                                         sensorLoadMinThresh = sensorLoadMinThreshold,
                                                         sensorLoadDeltaThresh = sensorLoadDeltaThreshhold,
                                                         sensorConfigurableThresh = sensorConfigurableThreshold,
                                                         leastSpecificPrefixLen = least_specific_len,
                                                         ipv6LeastSpecificPrefixLen = ipv6least_specific_len,
                                                         ipv6MostSpecificPrefixLen = ipv6most_specific_len,
                                                         state = state
                                                         ) 
        config[dpid][name]['flows'] = []
        #register the methods
        config[dpid][name]['balancer'].registerAddPrefixHandler(lambda x, y, z, dpid=dpid, name=name: self.addPrefix(dpid = dpid,
                                                                                                                     domain_name = name,
                                                                                                                     group_id = x,
                                                                                                                     prefix = y,
                                                                                                                     priority = z))
        
        config[dpid][name]['balancer'].registerDelPrefixHandler(lambda x, y, z, dpid=dpid, name=name : self.delPrefix(dpid = dpid,
                                                                                                                      domain_name = name,
                                                                                                                      group_id = x,
                                                                                                                      prefix = y,
                                                                                                                      priority = z))
        
        config[dpid][name]['balancer'].registerMovePrefixHandler(lambda x, y, z, a, dpid=dpid, name=name: self.movePrefix(dpid = dpid,
                                                                                                                         domain_name = name,
                                                                                                                         old_group_id = x,
                                                                                                                         new_group_id = y,
                                                                                                                         prefix = z,
                                                                                                                         priority=a))
        
        #handler to save the state
        config[dpid][name]['balancer'].registerStateChangeHandler(lambda x, y, z , dpid=dpid, name=name, mode=mode: self.saveState(dpid = dpid,
                                                                                                                                   domain_name = name,
                                                                                                                                   mode = mode,
                                                                                                                                   groups = x,
                                                                                                                                   prefix_list = y,
                                                                                                                                   prefix_priorities =z
                                                                                                                                   ))

        ports = ctxt.xpathEval("port")
        sensor_groups = ctxt.xpathEval("sensor_group")
        for port in ports:
          ctxt.setContextNode(port)
          ptype = port.prop("type")
          vlan_tag = port.prop("vlan_tag")
          prefixes = ctxt.xpathEval("prefix")
          prefixes_array = []
          for prefix in prefixes:
            prefix_obj = {}
            if(prefix.prop("type") == "v4" or prefix.prop("type") == "ipv4"):
              prefix_obj = {"type": prefix.prop("type"),
                            "prefix_str": prefix.getContent(),
                            "prefix": ipaddr.IPv4Network(prefix.getContent())}
            else:
              #eventually we'll be able to do this, but for now
              #we are going to hardcode ::/128 so that its considered a single 
              #prefix that is not divisible anymore
              #prefix_obj = {"type": prefix.prop("type"),
              #              "prefix_str": "::/128", #prefix.getContent(),
              #              "prefix": ipaddr.IPv6Network(prefix.getContent())}
               prefix_obj = {"type": prefix.prop("type"),
                            "prefix_str": prefix.getContent(),
                            "prefix": ipaddr.IPv6Network(prefix.getContent())}
            prefixes_array.append(prefix_obj)

          config[dpid][name]['ports'][ptype].append({"port_id": port.prop("of_port_id"),
                                                     "name": port.prop("name"),
                                                     "description": port.prop("description"),
                                                     "prefixes": prefixes_array,
                                                     "vlan_tag": vlan_tag
                                                     })
          
        for group in sensor_groups:
          ctxt.setContextNode(group)
          group_info = {"bw": group.prop("bw"),
                        "group_id": group.prop("group_id"),
                        "admin_state": group.prop("admin_state"),
                        "description": group.prop("description"),
                        "sensors": {}}
          config[dpid][name]['sensor_groups'][group.prop("group_id")] = group_info
          sensors = ctxt.xpathEval("sensor")
          for sensor in sensors:
            sensor = {"port_id": sensor.prop("of_port_id"),
                      "sensor_id": sensor.prop("sensor_id")}
            config[dpid][name]['sensor_groups'][group_info['group_id']]['sensors'][sensor['sensor_id']] = sensor
          config[dpid][name]['balancer'].addSensorGroup(group_info)
    
    self.config = config      
    doc.freeDoc()
    ctxt.xpathFreeContext()
    

  def switchLeave(self, datapath):
    if datapath in self.switches:
      self.switches.remove(datapath)

  def switchJoined(self, datapath):
    #check to see if we are suppose to operate on this switch
    self.switches.append(datapath)
    dpid = "%016x" % datapath.id
    if(self.config.has_key(dpid)):
      self.logger.info("Switch has joined!")
      #now for each domain push the initial flows 
      #and start the balancing process
      for domain_name in self.config[dpid]:
        domain = self.config[dpid][domain_name]
        if(domain['mode'] == "SciDMZ"):
          #we have firewals configured
          #setup the rules to them
          self.logger.info("Mode is Science DMZ")
          #need to install the default rules forwarding everything through the FW
          #then install the balancing rules for our defined prefixes
          self._setupSciDMZRules(dpid = dpid,
                                 domain_name = domain_name)
          if self.readState:
            self.config[dpid][domain_name]['balancer'].pushPrevState(dpid=dpid,
                                                                     domain_name=domain_name,
                                                                     mode = domain['mode'])

        elif(domain['mode'] == "InlineIDS"):
          #no firewall
          self.logger.info("Mode is Inline IDS")
          #need to install the default rules forwarding through the switch
          #then install the balancing rules for our defined prefixes
          self._setupInlineIDS(dpid = dpid, domain_name = domain_name)
          if self.readState:
            self.config[dpid][domain_name]['balancer'].pushPrevState(dpid=dpid,
                                                                     domain_name=domain_name,
                                                                     mode = domain['mode'])
        elif(domain['mode'] == "Balancer" or domain['mode'] == "SimpleBalancer"):
          #just balancer no other forwarding
          self.logger.info("Mode is Balancer")
          #just install the balance rules, no forwarding
          self._setupBalancer(dpid = dpid, domain_name = domain_name)
          if self.readState:
            self.config[dpid][domain_name]['balancer'].pushPrevState(dpid=dpid,
                                                                     domain_name=domain_name,
                                                                     mode = domain['mode'])
        
          
  def _setupSciDMZRules(self, dpid = None, domain_name = None):
    self.logger.debug("SciDMZ rule init")
    #just in and out port rules for the 
    #NOTE this presumes many input and 1 output port total and 1 fw lan/wan port for each domain

    #lowest priority
    priority = 10
    prefixes = []
    ports = self.config[dpid][domain_name]['ports']

    if(len(ports['fw_wan']) <= 0 or len(ports['fw_lan']) <= 0):
      #well crap no fw_wan or fw_lan exist... what are bypassing?
      self.logger.warn("nothing to bypass.. you probably want InlineIDS mode... doing that instead")
      self._setupInlineIDS(dpid = dpid, domain_name = domain_name)
      return

    fw_lan_outputs = []

    for in_port in ports['lan']:
      header = {"phys_port":   int(in_port['port_id']),
                'dl_type': None}
      
      actions = []
      #output to FW
      actions.append({"type": "output",
                      "port": int(ports['fw_lan'][0]['port_id'])})

      fw_lan_outputs.append({"type": "output",
                             "port": int(in_port['port_id'])})
      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              domain     = domain_name,
                                              header       = header,
                                              actions      = actions,
                                              command      = "ADD",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = int(priority / 2))

      for prefix in in_port['prefixes']:
        self.config[dpid][domain_name]['balancer'].addPrefix(prefix['prefix'])
        prefixes.append(prefix['prefix'])
        #specific prefix forwarding rules
        #FW LAN to specific LAN PORT
        header = {}
        header = {"phys_port": int(ports['fw_lan'][0]['port_id']),
                  "nw_dst": prefix['prefix']}        
        actions = []
        actions.append({"type": "output",
                        "port": int(in_port['port_id'])})
        
        self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                domain     = domain_name,
                                                header       = header,
                                                actions      = actions,
                                                command      = "ADD",
                                                idle_timeout = 0,
                                                hard_timeout = 0,
                                                priority     = int(priority))
        
        #SPECIFIC LAN -> FW LAN port
        header = {}
        header = {"phys_port": int(in_port['port_id']),
                  "nw_src": prefix['prefix']}

        actions = []
        actions.append({"type": "output",
                        "port": int(ports['fw_lan'][0]['port_id'])})
        
        self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                domain       = domain_name,
                                                header       = header,
                                                actions      = actions,
                                                command      = "ADD",
                                                idle_timeout = 0,
                                                hard_timeout = 0,
                                                priority     = int(priority))

    #FW LAN to ALL INPUT PORTS
    header = {"phys_port": int(ports['fw_lan'][0]['port_id']),
              'dl_type': None}
    
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            domain       = domain_name,
                                            header       = header,
                                            actions      = fw_lan_outputs,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority / 3))

    #FW WAN -> WAN
    header = {"phys_port": int(ports['fw_wan'][0]['port_id']),
              'dl_type': None}
    actions = []
    actions.append({"type": "output",
                    "port": int(ports['wan'][0]['port_id'])})
    self.logger.debug("FW WAN -> WAN: ")
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            domain       = domain_name,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority))

    #WAN -> FW WAN
    header = {"phys_port": int(ports['wan'][0]['port_id']),
              'dl_type': None}
    actions = []
    actions.append({"type": "output",
                    "port": int(ports['fw_wan'][0]['port_id'])})
    self.logger.debug("WAN -> FW WAN")
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            domain       = domain_name,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority))

    #ok now that we have that done... start balancing!!!
    self.logger.info("Distributing Prefixes!")
    self.config[dpid][domain_name]['balancer'].pushToSwitch()
    

  def _setupInlineIDS(self, dpid = None, domain_name = None):
    self.logger.debug("InLine IDS rule init")
    #no firewall
    #basically distribute prefixes and setup master forwarding
    priority = 10
    prefixes = []
    ports = self.config[dpid][domain_name]['ports']

    in_port = ports['lan'][0]

    for prefix in in_port['prefixes']:
      self.config[dpid][domain_name]['balancer'].addPrefix(prefix['prefix'])
      prefixes.append(prefix['prefix'])

    #LAN to WAN
    header = {"phys_port": int(ports['lan'][0]['port_id']),
              'dl_type': None}
        
    actions = []
    actions.append({'type':'output',
                    'port':int(ports['wan'][0]['port_id'])})
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            domain       = domain_name,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority / 3))

    #WAN -> LAN
    header = {"phys_port": int(ports['wan'][0]['port_id']),
              'dl_type': None}
    actions = []
    actions.append({"type": "output",
                    "port": int(ports['lan'][0]['port_id'])})
    self.logger.debug("FW WAN -> WAN: ")
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            domain       = domain_name,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority / 3))

    #ok now that we have that done... start balancing!!!
    self.logger.info("Distributing Prefixes!")
    self.config[dpid][domain_name]['balancer'].pushToSwitch()

  def _setupBalancer(self, dpid = None, domain_name = None):
    self.logger.debug("balancer rule init")
    #ok now that we have that done... start balancing!!!
    prefixes = []
    ports = self.config[dpid][domain_name]['ports']
    for port in ports['lan']:
      in_port = port
      for prefix in in_port['prefixes']:
        self.config[dpid][domain_name]['balancer'].addPrefix(prefix['prefix'])
        prefixes.append(prefix['prefix'])

    self.logger.info("Distributing Prefixes!")
    self.config[dpid][domain_name]['balancer'].pushToSwitch()
        

  def addPrefix(self, dpid=None, domain_name=None, group_id=None, prefix=None, priority=None):
    #self.logger.error("Add Prefix " + str(domain_name) + " " + str(group_id) + " " + str(prefix))
    #find the north and south port

    flows = []
    if self.config[dpid][domain_name]['mode'] == "SimpleBalancer":
      header = {}
      header = {"nw_src": prefix}
        
      actions = []
      #output to sensor (basically this is the IDS balance case)
      sensors = self.config[dpid][domain_name]['sensor_groups'][group_id]['sensors']
      for sensor in sensors:
        self.logger.debug("output: " + str(sensors[sensor]));
        actions.append({"type": "output",
                        "port": int(sensors[sensor]['port_id'])})

      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              domain       = domain_name,
                                              header       = header,
                                              actions      = actions,
                                              command      = "ADD",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = priority)
      
      header = {"nw_dst": prefix}

      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              domain       = domain_name,
                                              header       = header,
                                              actions      = actions,
                                              command      = "ADD",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = priority)
      return
    ##END SIMPLE BALANCER CASE
    
    in_port  = None
    out_port = None
    fw_lan   = None
    fw_wan   = None

    #end simple balancer
    #need to figure out the lan and wan ports

    ports = self.config[dpid][domain_name]['ports']

    for port in ports['lan']:
      for prefix_obj in port['prefixes']:
        if(prefix_obj['prefix'].Contains( prefix )):
          self.logger.debug("Prefix: " + str(prefix_obj['prefix']) + " contains " + str(prefix)) 
          in_port = port
         
          header = {}
          header = {"nw_src":      prefix,
                    "phys_port":   int(in_port['port_id'])}

          actions = []
          #output to sensor (basically this is the IDS balance case)
          sensors = self.config[dpid][domain_name]['sensor_groups'][group_id]['sensors']
          for sensor in sensors:
            self.logger.debug("output: " + str(sensors[sensor]));
            actions.append({"type": "output",
                            "port": int(sensors[sensor]['port_id'])})
          
          if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
          #append the FW or other destination
            if(ports.has_key('fw_lan') and len(ports['fw_lan']) > 0):
              actions.append({"type": "output",
                              "port": int(ports['fw_lan'][0]['port_id'])})
            else:
              actions.append({"type": "output",
                              "port": int(ports['wan'][0]['port_id'])})

          status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                           domain       = domain_name,
                                                           header       = header,
                                                           actions      = actions,
                                                           command      = "ADD",
                                                           idle_timeout = 0,
                                                           hard_timeout = 0,
                                                           priority     = priority)
          if status!= 1:
            self.logger.error("Max flow limit reached.Could not add flow")
            self.delete_flows(flows)
            raise MaxFlowCountError("Max Flow Count Reached")
          else:
            obj = { 'dpid' : dpid, 'domain' : domain_name, 'header' : header,
                    'actions' : actions, 'priority' : priority }
            flows.append(obj)
              
          header = {}
          if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
            header = {"nw_dst": prefix,
                      "phys_port": int(ports['wan'][0]['port_id'])}
          else:
            header = {"nw_dst": prefix,
                      "phys_port": int(in_port['port_id'])}
            
          actions = []
          #output to sensor (basically this is the IDS balance case)
            
          for sensor in sensors:
            actions.append({"type": "output",
                            "port": int(sensors[sensor]['port_id'])})
          if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
              #append the FW or other destination
            if(ports.has_key('fw_wan') and len(ports['fw_wan']) > 0):
              actions.append({"type": "output",
                              "port": int(ports['fw_wan'][0]['port_id'])})
            else:
              actions.append({"type": "output",
                              "port": int(ports['wan'][0]['port_id'])})
                
          self.logger.debug("Header: %s" % str(header))
          status = self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                             domain       = domain_name,
                                                             header       = header,
                                                             actions      = actions,
                                                             command      = "ADD",
                                                             idle_timeout = 0,
                                                             hard_timeout = 0,
                                                             priority     = priority)
          if status != 1:
            self.logger.error("Max flow limit reached.Could not add flow")
            self.delete_flows(flows)
            raise MaxFlowCountError("Max Flow Count Reached")
          else:
            obj = { 'dpid' : dpid, 'domain' : domain_name, 'header' : header,
                    'actions' : actions, 'priority' : priority }
            flows.append(obj)


  def delPrefix(self, dpid=None, domain_name=None, group_id=None, prefix=None, priority=None):
    self.logger.debug("Remove Prefix")

    if self.config[dpid][domain_name]['mode'] == "SimpleBalancer":
      header = {}
      header = {"nw_src": prefix}
      actions = []
      #output to sensor (basically this is the IDS balance case)                                                                                                
      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              domain       = domain_name,
                                              header       = header,
                                              actions      = actions,
                                              command      = "DELETE_STRICT",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = priority)
      
      header = {"nw_dst": prefix}
      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              domain       = domain_name,
                                              header       = header,
                                              actions      = actions,
                                              command      = "DELETE_STRICT",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = priority)
      return

    in_port  = None
    out_port = None
    fw_lan   = None
    fw_wan   = None

    #need to figure out the lan and wan ports
    ports = self.config[dpid][domain_name]['ports']
    for port in ports['lan']:
      for prefix_obj in port['prefixes']:
        if(prefix_obj['prefix'].Contains( prefix )):
          in_port = port

          header = {}
          header = {"nw_src":      prefix,
                    "phys_port":   int(in_port['port_id'])}
    
          actions = []
          self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                  domain       = domain_name,
                                                  header       = header,
                                                  actions      = actions,
                                                  command      = "DELETE_STRICT",
                                                  idle_timeout = 0,
                                                  hard_timeout = 0,
                                                  priority     = priority)
          header = {}
          if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
            header = {}
            header = {"nw_dst":      prefix,
                      "phys_port":   int(ports['wan'][0]['port_id'])}
          else:
            header = {"nw_dst":      prefix,
                      "phys_port":   int(in_port['port_id'])}
          
          actions = []
          self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                  domain       = domain_name,
                                                  header       = header,
                                                  actions      = actions,
                                                  command      = "DELETE_STRICT",
                                                  idle_timeout = 0,
                                                  hard_timeout = 0,
                                                  priority     = priority)
    
  def movePrefix(self, dpid = None, domain_name=None, new_group_id=None, old_group_id=None, prefix=None, priority=None):
    self.logger.debug("move prefix")
    #delete and add the prefix
    self.delPrefix(dpid, domain_name, old_group_id, prefix, priority)
    self.addPrefix(dpid, domain_name, new_group_id, prefix, priority)
    
  def saveState(self, dpid = None, domain_name = None, mode = None, groups = None, prefix_list = None, prefix_priorities = None):
    self.logger.info("Saving State")
    self.logger.debug(str(dpid))
    self.logger.debug(str(domain_name))
    self.logger.debug(str(mode))
    self.logger.debug(str(groups))
    self.logger.debug(str(prefix_list))
    self.logger.debug(str(prefix_priorities))
    fileName = str(dpid) + str(domain_name) + ".json"
    
    group = copy.deepcopy(groups)
    prefixes = []
    priorities = {}
    for k, v in group.iteritems():
      v['prefixes']= [str(i) for i in v["prefixes"]]

    for prefix in prefix_list:
      prefixes = [str(i) for i in prefix_list]
     
    for k, v in prefix_priorities.iteritems():
      priorities[str(k)] = v

    curr_state = {}
    curr_state["switch"] = {}
    curr_state["switch"][dpid] = {}
    curr_state["switch"][dpid]["domain"] = {} 
    curr_state["switch"][dpid]["domain"][domain_name] = {}
    curr_state["switch"][dpid]["domain"][domain_name]["mode"] = {}
    curr_state["switch"][dpid]["domain"][domain_name]["mode"][mode] = {}
    curr_state["switch"][dpid]["domain"][domain_name]["mode"][mode]["groups"] = group
    curr_state["switch"][dpid]["domain"][domain_name]["mode"][mode]["prefixes"] = prefixes
    curr_state["switch"][dpid]["domain"][domain_name]["mode"][mode]["priorities"] = priorities
    with open("/var/run/" +fileName, 'w') as fd:
      json.dump([curr_state], fd)
    fd.close()

  def remove_flow(self, dpid=None, domain=None, header=None,priority=None):
    self.logger.debug("remove flow")
    for white in self.whiteList:
      if ((cmp(header, white['header']) == 0) and (cmp(priority, white['priority'])== 0)):
        """ if a good flow times out, remove it"""
        self.logger.error("Removing good flow due to timeout")
        self.whiteList.remove(white)
        
        
    for black in self.blackList:
      if ((cmp(header, black['header']) == 0) and (cmp(priority, black['priority'])== 0)):
        """ if a bad flow times out, remove it"""
        self.logger.error("Removing bad flow due to timeout")
        self.blackList.remove(black)
        
    if not dpid:
      return

    if not domain:
      return
    
    match = self.stringify(header)
    for flow in self.config[dpid][domain]['flows']:
      if(flow['header'] == match and flow['priority'] == priority):
        self.config[dpid][domain]['flows'].remove(flow)
        self.flowCount -= 1


  def port_status(self, ev):
    self.logger.debug("port status handler")

  def port_stats(self, ev):
    self.logger.debug("port stats handler")

  def fireForwardingStateChangeHandlers( self,
                                         domain       = None,
                                         dpid         = None,
                                         header       = None,
                                         actions      = None,
                                         command      = None,
                                         idle_timeout = 0,
                                         hard_timeout = 0,
                                         priority     = 1):
    
    self.logger.debug("fireing forwarding state change handlers")
    self.logger.debug("Header: " + str(header))
    self.logger.debug("Actions: " + str(actions))
    self.logger.debug("Idle Timeout: " + str(idle_timeout))
    self.logger.debug("Hard Timeout: " + str(hard_timeout))
    self.logger.debug("Priority: " + str(priority))
            
    for handler in self.switchForwardingChangeHandlers:
      handler( dpid = dpid,
               domain = domain,
               header = header,
               actions = actions,
               command = command,
               idle_timeout = idle_timeout,
               hard_timeout = hard_timeout,
               priority = priority)
    return 1

  def pushFlows(self, dpid=None, domain=None, header=None, actions=None, priority=None):
    match = self.stringify(header)
    self.config[dpid][domain]['flows'].append({'dpid': dpid,
                                               'header': match,
                                               'actions': actions,
                                               'priority': priority
                                               })
    self.flowCount+= 1

  def stringify(self,header=None):
    match = {}
    if(header.has_key('nw_src')):
      match['nw_src'] = str(header['nw_src'])
    if(header.has_key('nw_dst')):
      match['nw_dst'] = str(header['nw_dst'])
    for field in header:
      if(not match.has_key(field)):
        match[field] = header[field]

    return match

  def pushTimeouts(self,idle= None,hard= None):
    if idle:
      self.idleTimeouts.append(idle)
    if hard:
      self.hardTimeouts.append(hard)

  def updatePrefixBW(self,dpid, prefix, tx, rx):
    self.logger.debug("updating prefix bw")
    for domain_name in self.config[dpid]:
      for port in self.config[dpid][domain_name]['ports']['lan']:
        for pref in port['prefixes']:
          if(pref['prefix'].Contains( prefix )):
            self.logger.debug("Updating prefix " + str(prefix) + " bandwidth for %s %s", dpid, domain_name)
            self.config[dpid][domain_name]['balancer'].setPrefixBW(prefix, tx, rx)
            return

  def getSensorLoad(self, sensor):
    self.logger.debug("getting sensor load for sensor %s", sensor)
    for dpid in self.config:
      for domain in self.config['dpid']:
        if(self.config[dpid][domain]['balancer'].getSensorStatus(sensor) != -1):
          return self.config[dpid][domain]['balancer'].getSensorStatus(sensor)

  def setSensorLoad(self, sensor, load):
    self.logger.debug("updating sensor %s with load %d", sensor, load)
    for dpid in self.config:
      for domain in self.config['dpid']:
        if(self.config[dpid][domain]['balancer'].getSensorStatus(sensor) != -1):
          self.config[dpid][domain]['balancer'].setSensorStatus(sensor,load)
          return {success: 1}
    return {success: 0, msg: "Unable to find sensor with id: " + sensor}

  def getSwitchFlows(self, dpid=None):
    flows = []
    if(self.config.has_key(dpid)):
      for domain in self.config[dpid]:
        flows.extend(self.config[dpid][domain]['flows'])
    return flows

  def getDomainFlows(self, dpid=None, domain=None):
    if(self.config.has_key(dpid)):
      if(self.config[dpid].has_key(domain)):
        return self.config[dpid][domain]['flows']

  def getDomainDetails(self, dpid=None, domain=None):
    if(self.config.has_key(dpid)):
      if(self.config[dpid].has_key(domain)):
        bal = self.config[dpid][domain]['balancer']
        res = {}
        res['config'] = bal.getConfig()
        sensor_groups = self.getDomainSensorGroups(dpid, domain)
        for sensor_group in sensor_groups:
          group = sensor_groups[sensor_group]
          new_prefixes = []
          for prefix in group['prefixes']:
            new_prefixes.append(str(prefix))

        ports = copy.deepcopy(self.config[dpid][domain]['ports'])
        
        for ptype in ports:
          for p in ports[ptype]:
            new_prefixes = []
            for prefix in p['prefixes']:
              prefix['prefix'] = str(prefix['prefix'])

        res['ports'] = ports

        return res
        

  def getSwitchDomains(self, dpid=None):
    domains = []
    if(self.config.has_key(dpid)):
      for domain in self.config[dpid]:
        domains.append(domain)
    return domains

  def getSensorStatus(self, dpid=None, domain=None, sensor_id=None):
    if(self.config.has_key(dpid)):
      if(self.config[dpid].has_key(domain)):
        bal = self.config[dpid][domain]['balancer']
        return bal.getSensorStatus(sensor_id)

  def getDomainSensorGroups(self, dpid=None, domain=None):
    if(self.config.has_key(dpid)):
      if(self.config[dpid].has_key(domain)):
        bal = self.config[dpid][domain]['balancer']
        sensor_groups = copy.deepcopy(bal.getSensorGroups())
        for group in sensor_groups:
          prefixes = sensor_groups[group]['prefixes']
          new_prefixes = []
          for prefix in prefixes:
            new_prefixes.append(str(prefix))
          sensor_groups[group]['prefixes'] = new_prefixes
            
        return sensor_groups


  def getDomainSensorGroup(self, dpid=None, domain=None, sensor_group=None):
    if(self.config.has_key(dpid)):
      if(self.config[dpid].has_key(domain)):
        bal = self.config[dpid][domain]['balancer']
        sensor_group = copy.deepcopy(bal.getSensorGroup(sensor_group))
        new_prefixes = []
        for prefix in sensor_group['prefixes']:
          new_prefixes.append(str(prefix))
        sensor_group['prefixes'] = new_prefixes

        return sensor_group
          

  def getSwitches(self):
    switches = []
    for switch in self.switches:
      ports = []
      for port in switch.ports:
        port = switch.ports[port]        
        ports.append({'port_no': port.port_no,
                      'mac_addr': port.hw_addr,
                      'name': port.name,
                      'config': port.config,
                      'state': port.state,
                      'curr': port.curr,
                      'advertised': port.advertised,
                      'supported': port.supported,
                      'peer': port.peer
                      })
      switches.append({'dpid': "%016x" % switch.id,
                       'ports': ports,
                       'address': switch.address[0],
                       'is_active': switch.is_active
                       })
    return switches

  def get_domain_sensors(self, dpid=None, domain=None):
    if(dpid == None or domain == None):
      return
    return self.config[dpid][domain]['balancer'].getSensors()

  def run_balancers(self):
    for dpid in self.config:
      for domain_name in self.config[dpid]:
        self.logger.debug("Balancing: %s %s", dpid, domain_name)
        self.config[dpid][domain_name]['balancer'].balance()
        
  def getBalancer(self, dpid, domain_name):
    return self.config[dpid][domain_name]['balancer']

  

  def TimeoutFlows(self, dpid, flows):
    self.logger.debug("Looking for flows to timeout")
    now = time.time()
    for flow in self.hardTimeouts:
      if(flow['dpid'] == dpid):
        if(flow['timeout'] <= now):
          self.logger.info("Timing out flow due to Hard Timeout")
          #remove the flow
          self.fireForwardingStateChangeHandlers( dpid         = flow['dpid'],
                                                  domain       = flow['domain'],
                                                  header       = flow['header'],
                                                  actions      = flow['actions'],
                                                  command      = "DELETE_STRICT",
                                                  priority     = flow['priority'])
          self.hardTimeouts.remove(flow)

    #need to improve this! its a O(n^2)
    for flow in flows:
      for idle in self.idleTimeouts:
        if(dpid == idle['dpid']):
          #need to compare the flow match to the header
          #self.logger.error(str(flow['match']))
          #self.logger.error(str(idle['header']))
          try:
            if(cmp(flow['match'], idle['header']) == 0 and cmp(int(idle['priority']),int(flow['priority']))==0):
              #compare the dicts and they are the same
              #so update the flow count and the expires time
              if(idle['pkt_count'] == flow['packet_count']):
              #hasn't been updated since last time...
                self.logger.debug("Flow has not been updated")
              else:
                self.logger.debug("Flow has been updated")
                idle['timeout'] = time.time() + idle['idle_timeout']
                self.logger.debug("New Timeout: " + str(idle['timeout']))
                idle['pkt_count'] = flow['packet_count']
          except TypeError:
            pass

    for flow in self.idleTimeouts:
      if(flow['dpid'] == dpid):
        self.logger.debug("Flows current timeout: " + str(flow['timeout']) + " now " + str(now))
        if(flow['timeout'] <= now):
          self.logger.info("removing the flow due to idle timeout")
          #remove the flow
          of_actions = []
          for action in flow['actions']:
            if action.type == 0:
              of_actions.append({"type" : "output",
                                 "port" : int(action.port)})
          self.fireForwardingStateChangeHandlers( dpid         = flow['dpid'],
                                                  domain       = flow['domain'],
                                                  header       = flow['header'],
                                                  actions      = of_actions,
                                                  command      = "DELETE_STRICT",
                                                  priority     = flow['priority'])
          
          self.idleTimeouts.remove(flow)
