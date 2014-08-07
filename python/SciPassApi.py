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


    self.whiteList = []
    self.blackList = []
    self.switchForwardingChangeHandlers = []

    self._processConfig(self.configFile)
    
  def registerForwardingStateChangeHandler(self, handler):
    self.switchForwardingChangeHandlers.append(handler)

  def good_flow(self, obj):
    #turn this into a 
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors
    in_port = None
    out_port = None
    dpid = None
    domain = None
    reverse = False
    new_prefix = ipaddr.IPv4Network(obj['nw_src'])

    #need to figure out the lan and wan ports
    for datapath_id in self.config:
      for name in self.config[datapath_id]:
        for port in self.config[datapath_id][name]['ports']['lan']:
            for prefix in port['prefixes']:
              if(prefix['prefix'].Contains( new_prefix )):
                in_port = port
                dpid = datapath_id
                domain = name
                
    if(in_port == None):
      new_prefix = ipaddr.IPv4Network(obj['nw_dst'])
      #do the same but look for the dst instead of the src
      for datapath_id in self.config:
        for name in self.config[datapath_id]:
          for port in self.config[datapath_id][name]['ports']['lan']:
            for prefix in port['prefixes']:
              if(prefix['prefix'].Contains( new_prefix )):
                in_port = port
                dpid = datapath_id
                domain = name
                reverse = True

    if(in_port == None):
      self.logger.error("unable to find either an output or an input port")
      return

    obj['phys_port'] = in_port['port_id']

    actions = [{"type": "output", 
                "port": self.config[dpid][name]['ports']['wan'][0]['port_id']}]

    idle_timeout = None
    hard_timeout = None
    priority     = self.config[dpid][name]['default_whitelist_priority']
    self.logger.debug("Idle Timeout: " + self.config[dpid][name]['idle_timeout'])
    self.logger.debug("Hard Timeout: " + self.config[dpid][name]['hard_timeout'])
    self.logger.debug("Priority: " + priority)
    
    header = {}
    if(not obj.has_key('idle_timeout')):
      idle_timeout  = self.config[dpid][name]['idle_timeout']
    else:
      idle_timeout = obj['idle_timeout']
      
    self.logger.debug("Selected Idle Timeout: " + str(idle_timeout))
    if(not obj.has_key('hard_timeout')):
      hard_timeout = self.config[dpid][name]['hard_timeout']
    else:
      hard_timeout = obj['hard_timeout']
      
    if(not obj.has_key('priority')):
      priority = self.config[dpid][name]['default_whitelist_priority']
    else:
      priority = obj['priority']

    if(obj.has_key('nw_src')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)

    if(obj.has_key('nw_dst')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)

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

    header['phys_port'] = in_port['port_id']

    self.logger.debug("Header: " + str(header))

    

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority)
      

    header = {}
    if(not obj.has_key('idle_timeout')):
      idle_timeout  = self.config[dpid][name]['idle_timeout']
    else:
      idle_timeout = obj['idle_timeout']

    self.logger.debug("Selected Idle Timeout: " + str(idle_timeout))
    if(not obj.has_key('hard_timeout')):
      hard_timeout = self.config[dpid][name]['hard_timeout']
    else:
      hard_timeout = obj['hard_timeout']

    if(not obj.has_key('priority')):
      priority = self.config[dpid][name]['default_whitelist_priority']
    else:
      priority = obj['priority']

    if(obj.has_key('nw_src')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
    if(obj.has_key('nw_dst')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)

    if(obj.has_key('tp_src')):
      if(reverse):
        header['tp_src'] = int(obj['tp_src'])
      else:
        header['tp_dst'] = int(obj['tp_src'])

    if(obj.has_key('tp_dst')):
      if(reverse):
        header['tp_dst'] = int(obj['tp_dst'])
      else:
        header['tp_src'] = int(obj['tp_dst'])

    header['phys_port'] = self.config[dpid][name]['ports']['wan'][0]['port_id']
    
    actions = [{"type": "output",
                "port": in_port['port_id']}]
    
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority)
    
    results = {}
    results['success'] = 1
    return results

  def bad_flow(self, obj):
    #turn this into a
    #presumes that we get a nw_src, nw_dst, tcp_src_port, tcp_dst_port
    #we need to do verification here or conversion depending on what we get from the sensors
    in_port = None
    out_port = None
    dpid = None
    domain = None
    reverse = False

    new_prefix = ipaddr.IPv4Network(obj['nw_src'])
    self.logger.debug("New preifx: " + str(new_prefix))
    #need to figure out the lan and wan ports
    for datapath_id in self.config:
      for name in self.config[datapath_id]:
        for port in self.config[datapath_id][name]['ports']['lan']:
            for prefix in port['prefixes']:
              if(prefix['prefix'].Contains( new_prefix )):
                in_port = port
                dpid = datapath_id
                domain = name

    if(in_port == None):
      new_prefix = ipaddr.IPv4Network(obj['nw_dst'])
      #do the same but look for the dst instead of the src                                                             
      for datapath_id in self.config:
        for name in self.config[datapath_id]:
          for port in self.config[datapath_id][name]['ports']['lan']:
            for prefix in port['prefixes']:
              if(prefix['prefix'].Contains( new_prefix )):
                in_port = port
                dpid = datapath_id
                domain = name
                reverse = True

    if(in_port == None):
      self.logger.debug("unable to find either an output or an input port")
      return

    obj['phys_port'] = in_port['port_id']

    #actions = drop
    actions = []

    idle_timeout = None
    hard_timeout = None
    priority     = self.config[dpid][name]['default_blacklist_priority']

    header = {}
    if(not obj.has_key('idle_timeout')):
      idle_timeout  = self.config[dpid][name]['idle_timeout']
    else:
      idle_timeout = obj['idle_timeout']

    self.logger.debug("Selected Idle Timeout: " + str(idle_timeout))
    if(not obj.has_key('hard_timeout')):
      hard_timeout = self.config[dpid][name]['hard_timeout']
    else:
      hard_timeout = obj['hard_timeout']

    if(not obj.has_key('priority')):
      priority = self.config[dpid][name]['default_whitelist_priority']
    else:
      priority = obj['priority']

    if(obj.has_key('nw_src')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
    if(obj.has_key('nw_dst')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)

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

    header['phys_port'] = in_port['port_id']

    self.logger.debug("Header: " + str(header))

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority)

    header = {}
    if(not obj.has_key('idle_timeout')):
      idle_timeout  = self.config[dpid][name]['idle_timeout']
    else:
      idle_timeout = obj['idle_timeout']

    self.logger.debug("Selected Idle Timeout: " + str(idle_timeout))
    if(not obj.has_key('hard_timeout')):
      hard_timeout = self.config[dpid][name]['hard_timeout']
    else:
      hard_timeout = obj['hard_timeout']

    if(not obj.has_key('priority')):
      priority = self.config[dpid][name]['default_whitelist_priority']
    else:
      priority = obj['priority']

    if(obj.has_key('nw_src')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_src'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
    if(obj.has_key('nw_dst')):
      if(reverse):
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_dst'] = int(prefix)
        header['nw_dst_mask'] = int(prefix.prefixlen)
      else:
        prefix = ipaddr.IPv4Network(obj['nw_dst'])
        header['nw_src'] = int(prefix)
        header['nw_src_mask'] = int(prefix.prefixlen)
    if(obj.has_key('tp_src')):
      if(reverse):
        header['tp_src'] = int(obj['tp_src'])
      else:
        header['tp_dst'] = int(obj['tp_src'])

    if(obj.has_key('tp_dst')):
      if(reverse):
        header['tp_dst'] = int(obj['tp_dst'])
      else:
        header['tp_src'] = int(obj['tp_dst'])

    header['phys_port'] = self.config[dpid][name]['ports']['wan'][0]['port_id']

    #actions = drop
    actions = []

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = idle_timeout,
                                            hard_timeout = hard_timeout,
                                            priority     = priority)


    results = {}
    results['success'] = 1
    return results

  def get_bad_flow(self):
    return self.whiteList

  def get_good_flow(self):
    return self.blackList

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
        idle_timeout = domain.prop("idle_timeout")
        hard_timeout = domain.prop("hard_timeout")
        default_blacklist_priority = domain.prop("blacklist_priority")
        default_whitelist_priority = domain.prop("whitelist_priority")
        sensorLoadMinThreshold = domain.prop("sensor_min_load_threshold")
        sensorLoadDeltaThreshhold = domain.prop("sensor_load_delta_threshold")
        self.logger.debug("Adding Domain: name: %s, mode: %s, status: %s", name, mode, status)
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
        config[dpid][name]['balancer'].registerAddPrefixHandler(lambda x, y : self.addPrefix(dpid = dpid,
                                                                                            domain_name = name,
                                                                                            sensor_id = x,
                                                                                            prefix = y))

        config[dpid][name]['balancer'].registerDelPrefixHandler(lambda x, y : self.delPrefix(dpid = dpid,
                                                                                            domain_name = name,
                                                                                            sensor_id = x,
                                                                                            prefix = y))

        config[dpid][name]['balancer'].registerMovePrefixHandler(lambda x, y, z : self.movePrefix(dpid = dpid,
                                                                                              domain_name = name,
                                                                                              old_sensor_id = x,
                                                                                              new_sensor_id = y,
                                                                                              prefix = z
                                                                                              ))

        ports = ctxt.xpathEval("port")
        sensor_ports = ctxt.xpathEval("sensor_port")

        for port in sensor_ports:
          sensor = {"port_id": port.prop("of_port_id"),
                    "bw": port.prop("bw"),
                    "sensor_id": port.prop("sensor_id"),
                    "admin_status": port.prop("admin_status"),
                    "description": port.prop("description")}
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

          config[dpid][name]['ports'][ptype].append({"port_id": port.prop("of_port_id"),
                                                     "name": port.prop("name"),
                                                     "description": port.prop("description"),
                                                     "prefixes": prefixes_array
                                                     })
        
    self.config = config      
    doc.freeDoc()
    ctxt.xpathFreeContext()

  def switchJoined(self, datapath):
    #check to see if we are suppose to operate on this switch
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

        elif(domain['mode'] == "InlineIDS"):
          #no firewall
          self.logger.info("Mode is Inline IDS")
          #need to install the default rules forwarding through the switch
          #then install the balancing rules for our defined prefixes
          self._setupInlineIDS(dpid = dpid, domain_name = domain['name'])
        elif(domain['mode'] == "Balancer"):
          #just balancer no other forwarding
          self.logger.info("Mode is Balancer")
          #just install the balance rules, no forwarding
          self._setupBalancer(dpid = dpid, domain_name = domain['name'])
        
          
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
      header = {"phys_port":   int(in_port['port_id'])}

      actions = []
      #output to FW
      actions.append({"type": "output",
                      "port": int(ports['fw_lan'][0]['port_id'])})

      fw_lan_outputs.append({"type": "output",
                             "port": int(in_port['port_id'])})

      self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                              header       = header,
                                              actions      = actions,
                                              command      = "ADD",
                                              idle_timeout = 0,
                                              hard_timeout = 0,
                                              priority     = int(priority / 2))

      for prefix in in_port['prefixes']:
        prefixes.append(prefix['prefix'])
        #specific prefix forwarding rules
        #FW LAN to specific LAN PORT
        header = {"phys_port": int(ports['fw_lan'][0]['port_id']),
                  "nw_dst": int(prefix['prefix']),
                  "nw_dst_mask": int(prefix['prefix'].prefixlen)}
        
        actions = []
        actions.append({"type": "output",
                        "port": int(in_port['port_id'])})
        
        self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                header       = header,
                                                actions      = actions,
                                                command      = "ADD",
                                                idle_timeout = 0,
                                                hard_timeout = 0,
                                                priority     = int(priority))
        
        #SPECIFIC LAN -> FW LAN port
        header = {"phys_port": int(in_port['port_id']),
                  "nw_src": int(prefix['prefix']),
                  "nw_src_mask": int(prefix['prefix'].prefixlen)}

        actions = []
        actions.append({"type": "output",
                        "port": int(ports['fw_lan'][0]['port_id'])})

        self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                                header       = header,
                                                actions      = actions,
                                                command      = "ADD",
                                                idle_timeout = 0,
                                                hard_timeout = 0,
                                                priority     = int(priority))

    #FW LAN to ALL INPUT PORTS
    header = {"phys_port": int(ports['fw_lan'][0]['port_id'])}
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = fw_lan_outputs,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority / 3))

    #FW WAN -> WAN
    header = {"phys_port": int(ports['fw_wan'][0]['port_id'])}
    actions = []
    actions.append({"type": "output",
                    "port": int(ports['wan'][0]['port_id'])})
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = fw_lan_outputs,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority))

    #WAN -> FW WAN
    header = {"phys_port": int(ports['wan'][0]['port_id'])}
    actions = []
    actions.append({"type": "output",
                        "port": int(ports['fw_wan'][0]['port_id'])})
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = fw_lan_outputs,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = int(priority))

    #ok now that we have that done... start balancing!!!
    self.config[dpid][domain_name]['balancer'].distributePrefixes(prefixes)
    

  def _setupInlineIDS(self, dpid = None, domain_name = None):
    self.logger.debug("InLine IDS rule init")

  def _setupBalancer(self, dpid = None, domain_name = None):
    self.logger.debug("balancer rule init")
  
  def _resetSwitchForwarding(self,dpid):
    self.resetSwitchForwarding(dpid)
  
  def addPrefix(self, dpid=None, domain_name=None, sensor_id=None, prefix=None):
    self.logger.debug("Add Prefix " + str(domain_name) + " " + str(sensor_id) + " " + str(prefix))
    #find the north and south port

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

    if(in_port == None):
      self.logger.error("unable to find either an output or an input port")
      return

    header = {"nw_src":      int(prefix),
              "nw_src_mask": int(prefix.prefixlen),
              "phys_port":   int(in_port['port_id'])}

    actions = []
    #output to sensor (basically this is the IDS balance case)
    actions.append({"type": "output",
                    "port": self.config[dpid][domain_name]['sensor_ports'][sensor_id]['port_id']})
    if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
      #append the FW or other destination
      if(len(ports['fw_lan']) == 0):
        actions.append({"type": "output",
                        "port": ports['wan'][0]['port_id']})
      else:
        actions.append({"type": "output",
                        "port": ports['fw_lan'][0]['port_id']})

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = 500)

    header = {"nw_dst":      int(prefix),
              "nw_dst_mask": int(prefix.prefixlen),
              "phys_port":   int(ports['wan'][0]['port_id'])}
    
    actions = []
    #output to sensor (basically this is the IDS balance case)
    actions.append({"type": "output",
                    "port": self.config[dpid][domain_name]['sensor_ports'][sensor_id]['port_id']})
    if(self.config[dpid][domain_name]['mode'] == "SciDMZ" or self.config[dpid][domain_name]['mode'] == "InlineIDS"):
      #append the FW or other destination
      if(fw_lan == 0):
        actions.append({"type": "output",
                        "port": in_port['port_id']})
      else:
        actions.append({"type": "output",
                        "port": ports['fw_wan'][0]['port_id']})

    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "ADD",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = 500)

  def delPrefix(self, dpid=None, domain_name=None, sensor_id=None, prefix=None):
    self.logger.debug("Remove Prefix")

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

    if(in_port == None):
      self.logger.error("Unable to find an input port for the prefix")
      return

    header = {"nw_src":      int(prefix),
              "nw_src_mask": int(prefix.prefixlen),
              "phys_port":   int(in_port['port_id'])}
    
    actions = []
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "DELETE_STRICT",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = 500)

    header = {"nw_dst":      int(prefix),
              "nw_dst_mask": int(prefix.prefixlen),
              "phys_port":   int(ports['wan'][0]['port_id'])}
    
    actions = []
    self.fireForwardingStateChangeHandlers( dpid         = dpid,
                                            header       = header,
                                            actions      = actions,
                                            command      = "DELETE_STRICT",
                                            idle_timeout = 0,
                                            hard_timeout = 0,
                                            priority     = 500)
    
  def movePrefix(self, dpid = None, domain_name=None, new_sensor_id=None, old_sensor_id=None, prefix=None):
    self.logger.debug("move prefix")
    #delete and add the prefix
    self.delPrefix(dpid, domain_name, old_sensor_id, prefix)
    self.addPrefix(dpid, domain_name, new_sensor_id, prefix)

  def _flush_rules(self, dpid):
    self.logger.debug("flush rules")
    

  def remove_flow(self, ev):
    self.logger.debug("remove flow")
    
  def port_status(self, ev):
    self.logger.debug("port status handler")

  def port_stats(self, ev):
    self.logger.debug("port stats handler")

  def fireForwardingStateChangeHandlers( self,
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
               header = header,
               actions = actions,
               command = command,
               idle_timeout = idle_timeout,
               hard_timeout = hard_timeout,
               priority = priority)

  def updatePrefixBW(self,dpid, prefix, tx, rx):
    self.logger.debug("updating prefix bw")
    for domain_name in self.config[dpid]:
      for port in self.config[dpid][domain_name]['ports']['lan']:
        for pref in port['prefixes']:
          if(pref['prefix'].Contains( prefix )):
            self.logger.debug("Updating prefix " + str(prefix) + " bandwidth for %s %s", dpid, domain_name)
            self.config[dpid][domain_name]['balancer'].setPrefixBW(prefix, tx, rx)
            return

  def run_balancers(self):
    for dpid in self.config:
      for domain_name in self.config[dpid]:
        self.logger.info("Balancing: %s %s", dpid, domain_name)
        self.config[dpid][domain_name]['balancer'].balance()
        

  def getBalancer(self, dpid, domain_name):
    return self.config[dpid][domain_name]['balancer']
