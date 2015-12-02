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


import time
import ipaddr
import pprint
import json
import logging
from collections import defaultdict


class PrefixlenInvalidError(Exception):
    """Raised when split is called with a bad prefixlen_diff."""

    def __init__(self, msg):
      self.msg = msg

class MaxPrefixlenError(Exception):
    """Raised when split is called on a prefx at the most specific len limit."""

    def __init__(self, msg):
      self.msg = msg


class MaxPrefixesError(Exception):
    """Raised when attempt to add a prefix will exeed max prefixes limit"""

    def __init__(self, msg):
      self.msg = msg

class DuplicatePrefixError(Exception):
    """Raised when attempt to add a prefix that has been already added"""

    def __init__(self, msg):
      self.msg = msg

class MaxFlowCountError(Exception):
    """Raised when attempt to split a prefix will exceed max flow count limit"""

    def __init__(self, msg):
        self.msg = msg

class SimpleBalancer:
  """A simple balancer using only OpenFlow"""
  def __init__(  self,
                 ignoreSensorLoad	= 0,
                 ignorePrefixBW         = 1,
		 maxPrefixes		= 32,
  		 mostSpecificPrefixLen	= 29,
 		 leastSpecificPrefixLen	= 24,
                 ipv6MostSpecificPrefixLen  = 64,
                 ipv6LeastSpecificPrefixLen = 48,
     		 sensorLoadMinThresh	= .02,
		 sensorLoadDeltaThresh	= .05,
                 sensorConfigurableThresh = 100,
                 state                  = None,
                 logger                 = None):
      
      if(logger == None):
          logging.basicConfig()
          self.logger = logging.getLogger(__name__)
      else:
          self.logger = logger
      #--- used to limit the number of subnets / forwarding rules we install on the swtich
      self.maxPrefixes		       = maxPrefixes;
      self.prefixCount		       = 0;
      self.prefixPriorities           = defaultdict(list)
      self.mostSpecificPrefixLen       = int(mostSpecificPrefixLen)
      self.leastSpecificPrefixLen      = int(leastSpecificPrefixLen)
      self.ipv6MostSpecificPrefixLen       = int(ipv6MostSpecificPrefixLen)
      self.ipv6LeastSpecificPrefixLen      = int(ipv6LeastSpecificPrefixLen)
      self.ignoreSensorLoad	       = ignoreSensorLoad
      self.sensorLoadMinThreshold      = float(sensorLoadMinThresh)
      self.sensorLoadDeltaThreshold    = float(sensorLoadDeltaThresh)
      self.sensorConfigurableThreshold = float(sensorConfigurableThresh)
      self.curr_priority               = 500

      self.ignorePrefixBW              = ignorePrefixBW
      self.sensorBandwidthMinThreshold = 1
      self.groups                     = defaultdict(list)
      
      #--- prefix bandwidth in GigaBits/sec
      self.prefixBW		       = defaultdict(float)
      #--- previous State
      self.state = state
      self.addPrefixHandlers  = []
      self.delPrefixHandlers  = []
      self.movePrefixHandlers = []
      self.saveStateChangeHandlers = []
      self.prefix_list = []
      self.initialized = False
      return
  
  def __str__(self):
      """a string representation"""
      res = "Balancer: \n";
 #     res = res + "  Prefixes: "+str(self.sensorPrefixes)+"\n"
 #     res = res + "  Load: "+str(self.sensorLoad)+"\n";
 #     res = res + "  PrefixBW: "+str(self.prefixBW) +"\n"
 #     res = res + "  pre2sensor: "+str(self.prefixSensor)+"\n"
      return res 

  def addPrefix(self, prefix):
      if(prefix not in self.prefix_list):
          self.prefix_list.append(prefix)

  def pushToSwitch(self):
      """initialize a device"""
      if(self.initialized):
          self.pushAllPrefixes()
      else:
          self.distributePrefixes(self.prefix_list)
          self.fireSaveState()
          self.initialized = True
      self.logger.info("Switch Initialized")

  def pushPrevState(self, dpid=None, domain_name=None, mode=None):
      #Assumes no change in configuration from previous configuration
      if not self.state:
          return
      
      if  self.state["switch"][dpid]["domain"][domain_name]["mode"].has_key(mode):
          self.logger.info("Pushing Previous State") 
          newPrefixes = []
          delPrefixes = []
          prevPrefixes = []
          
          #calculate previous prefixes
          for prefix in self.state["switch"][dpid]["domain"][domain_name]["mode"][mode]["prefixes"]:
              try:
                  prevPrefixes.append(ipaddr.IPv4Network(prefix))
              except:
                  prevPrefixes.append(ipaddr.IPv6Network(prefix))
                  
          
          previous = set(prevPrefixes)
          current  = set(self.prefix_list)
          
          #calculate del prefixes
          delPrefixes = current.difference(previous)
          #calculate new prefixes
          newPrefixes = previous.difference(current)
          
                        
          #delete the old prefixes from sensor group
          if delPrefixes:
              for delPrefix in delPrefixes:
                  group = self.getPrefixGroup(delPrefix)
                  if group:
                      self.delGroupPrefix(group, delPrefix)

          #distribute the new prefixes to the sensor groups
          if newPrefixes:
              self.distributePrefixes(list(newPrefixes))  


  def getConfig(self):
      obj = {}
      obj['max_prefixes'] = self.maxPrefixes
      obj['prefixCount'] = self.prefixCount
      obj['ignoreSnesorLoad'] = self.ignoreSensorLoad
      obj['mostSpecificPrefixLen'] = self.mostSpecificPrefixLen
      obj['leastSpecificPrefixLen'] = self.leastSpecificPrefixLen
      obj['sensorLoadMinThreshold'] = self.sensorLoadMinThreshold
      obj['sensorLoadDeltaThreshold'] = self.sensorLoadDeltaThreshold

      return obj

  def getTotals(self):
      """calculates total bandwidth bypassed, dropped, and balanced"""
      obj = {}
      return obj

  def __repr__(self):
      return json.dumps(self,default=lambda o: o.__dict__, sort_keys=True, indent=4)

  def getPrefixPriority(self, prefix):
      for pfix in self.prefixPriorities:
          if(pfix.Contains(prefix)):
              return self.prefixPriorities[pfix]

  def showStatus(self):
      """returns text represention in show format of the current status balancing"""

      mode = "Sensor Load and Prefix Bandwidth"
      
      if(self.ignoreSensorLoad > 0):
          mode = "Prefix Bandwidth"

      if(self.ignoreSensorLoad > 0 and  self.ignorePrefixBW > 0):
          mode = "IP Space"

      status = ""; 
      totalHosts = 0
      totalBW    = 0;

      status = "Balance Method: %s:\n" % mode

      sensorHosts = defaultdict(int)
      sensorBW    = defaultdict(int)
      for prefix in self.prefixSensor:
          totalHosts = totalHosts +  prefix.numhosts
          totalBW    = totalBW    +  self.prefixBW[prefix]
          sensor     = self.prefixSensor[prefix]
          sensorBW[sensor]  = sensorBW[sensor] + self.prefixBW[prefix]
  
          lastCount = sensorHosts[sensor]
          sensorHosts[sensor] = lastCount + prefix.numhosts

      for sensor in self.sensorLoad:
          sensorHostVal = sensorHosts[sensor] / float(totalHosts)
          try:
              sensorBwPer = sensorBW[sensor] / float(totalBW)
          except ZeroDivisionError:
              sensorBwPer = 0 
              
      status = status + "sensor: '"+sensor+"'  bw: %.2f load: %.3f  hosts: %.3f"%(sensorBwPer,self.sensorLoad[sensor],sensorHostVal )+"\n"
    
      for prefix in self.prefixSensor:
          if(self.prefixSensor[prefix] == sensor):
              prefixBW = self.prefixBW[prefix]
              status = status + " "+str(prefix)+": %.3f "%(prefixBW/1000000.0)+"mbps\n"

          status = status + "\n"

      return status
 

  #distributes prefixes through all groups
  #this is not going to be event but it is at least a start
  def distributePrefixes(self, prefix_array):
      self.logger.debug("Distributing prefixes: " + str(prefix_array))
      prefix_array = list(prefix_array)
      group_index = 0
      for prefix in prefix_array:
          
          self.logger.debug("prefix len: %d", prefix.prefixlen)
          self.logger.debug("least speciifc: %d", self.leastSpecificPrefixLen)

          #because we don't have OF 1.3 yet
          if(prefix.version == 4):
              if(prefix.prefixlen < self.leastSpecificPrefixLen):
                  self.logger.debug("prefix: %s exceeds the least specific prefix len %d", str(prefix), self.leastSpecificPrefixLen )
                  #split it in half and try again
                  try:
                      self.distributePrefixes( self.splitPrefix(prefix) )
                  except MaxPrefixlenError:
                      self.logger.error("Exceeded the most specific prefix len!\n");
              else:
                  group = self.groups.keys()[group_index]
                  self.logger.debug("Adding prefix %s to group: %s", str(prefix), str(self.groups[group]['group_id']))
                  try:
                      self.addGroupPrefix( self.groups[group]['group_id'], prefix, 0)
                  except DuplicatePrefixError:
                      self.logger.debug("Already have prefix: " + str(prefix))
                  except MaxFlowCountError:
                      self.logger.debug("Max Flow Count Error")
                  group_index += 1
                  if(group_index >= len(self.groups)):
                      group_index = 0
          else:
              #handle IPv6 differently
              if(prefix.prefixlen < self.ipv6LeastSpecificPrefixLen):
                  try:
                      self.distributePrefixes( self.splitPrefix(prefix) )
                  except MaxPrefixlenError:
                      self.logger.error("Exceeded the most specific prefix len!\n");
              else:
                  group = self.groups.keys()[group_index]
                  self.logger.debug("Adding prefix %s to group: %s", str(prefix), str(self.groups[group]['group_id']))
                  try:
                      self.addGroupPrefix( self.groups[group]['group_id'], prefix, 0)
                  except DuplicatePrefixError:
                      self.logger.debug("Already have prefix: " + str(prefix))
                  except MaxFlowCountError:
                      self.logger.debug("Max Flow Count Error")
                  group_index += 1
                  if(group_index >= len(self.groups)):
                      group_index = 0
              
  def pushAllPrefixes(self):
      for group in self.groups:
          for prefix in self.groups[group]['prefixes']:
              priority = self.getPrefixPriority(prefix)
              self.fireAddPrefix(group, prefix, priority['priority'])
              self.fireSaveState()

  def addSensorGroup(self, group):
    """adds sensor, inits to load 0, sets status to 1"""
    if(group == None):
        self.logger.error("No Sensor Group Specified")
        return 0

    if(self.groups.has_key(group['group_id'])):
        self.logger.error("SensorGroup %s already exists", group['group_id'])
        return 0

    group['load'] = 0
    group['status'] = 1
    group['prefixes'] = []

    #create sensor status/load for each sensor in the group
    for sensor in group['sensors']:
        group['sensors'][sensor]['status'] = 1
        group['sensors'][sensor]['load'] = 0

    self.groups[group['group_id']] = group

    return 1
 
  
  def setSensorLoad(self,sensor,load):
    """sets the load value for the sensor, 0-1 float is range"""
    if(load >= 0 and load <= 1):
        for group in self.groups:
            if(self.groups[group]['sensors'].has_key(sensor)):
                self.groups[group]['sensors'][sensor]['load'] = load
                return 1
        return 0
    else:
        return 0

  def getGroupLoad(self, group):
      if(self.groups.has_key(group)):
          sensors = self.groups[group]['sensors']
          maxLoad = -1
          maxSensor = -1
          for sensor in sensors:
              if(maxLoad == -1):
                  maxLoad = sensors[sensor]['load']
                  maxSensor = sensor
              else:
                  if(sensors[sensor]['load'] > maxLoad):
                      maxSensor = sensor
                      maxLoad = sensors[sensor]['load']
          return maxLoad
      return
          

  def unloadGroupPrefixes(self, group):
    """moves all the prefixes off of a sensor an onto the sensor with the least load"""
    minLoad       = 100
    minLoadGroup  = ""
    
    #--- get the sensor with the least load 
    for other_group in self.groups.keys():
      
      # make sure it's not the sensor were moving prefixes off of
      if(other_group == group): continue
      # don't include disabled sensors
      if(not self.getGroupStatus(group)): continue
      
      load = self.getGroupLoad(other_group)
      
      if(load < minLoad):
          minLoad       = load
          minLoadGroup = other_group;

    # move all of this sensor prefixes onto the minLoadSensor
    prefixList = list(self.groups[group]['prefixes'])
    self.logger.info("prefixList: %s" % (prefixList))
    for prefix in prefixList:
        self.logger.info("moving prefix %s from %s to %s" % (prefix, group, minLoadGroup))
        self.moveSensorPrefix(sensor, minLoadGroup, prefix)

  def getGroupStatus(self,group):
      if(self.groups.has_key(group)):
          stat = 1
          sensors = self.groups[group]['sensors']
          for sensor in sensors:
              if(sensors[sensor]['status'] == 0):
                  return 0
          if(stat):
              return 1

  def getSensorGroups(self):
      return self.groups

  def getSensorGroup(self, sensor_group):
      if(self.groups.has_key(sensor_group)):
          return self.groups[sensor_group]

  def setSensorStatus(self,sensor,status):
      """sets the load value for the sensor, 0-1 int is range"""
      for group in self.groups:
          if(self.groups[group]['sensors'].has_key(sensor)):
              action = 'enabling' if(status == 1) else 'disabling'
              self.logger.info("%s sensor: %s" % (action, sensor))
              self.groups[group]['sensors'][sensor]['status'] = status
              if(not self.getGroupStatus(group)):
                  self.unloadGroupPrefixes(group)   
              return 1
      
      self.logger.error( "Error updating sensor")
      return -1

  def getSensors(self):
      sensors = []
      for sensor in self.sensorStatus:
          obj = {}
          obj['sensor_id'] = sensor
          obj['status'] = self.sensorStatus[sensor]
          obj['load'] = self.sensorLoad[sensor]
          obj['bandwidth'] = self.getSensorBW(sensor)
          sensors.append(obj)
      return sensors

  def getSensorStatus(self,sensor):
      for group in self.groups:
          if(self.groups[group]['sensors'].has_key(sensor)):
              return self.groups[group]['sensors'][sensor]['status']
      self.logger.error("Sensor: " + str(sensor) + " does not exist")
      return -1

  def setPrefixBW(self,prefix,bwTx,bwRx):
    """updates balancers understanding trafic bandwidth associated with each prefix"""
    self.logger.debug("Updating prefix BW for " + str(prefix) + " to " + str((bwTx/1000/1000)*8) + "Mb/s " + str((bwRx/1000/1000)*8) + "Mb/s")
    if(self.prefixBW.has_key(prefix)):
        self.prefixBW[prefix] = (bwTx * 8) + (bwRx * 8)
        return 1
    self.logger.debug( "Error updating prefixBW for " + str(prefix) + "... prefix does not exist")
    return 0

  def registerAddPrefixHandler(self,handler):
    """used to register a handler for add prefix events"""
    self.addPrefixHandlers.append(handler)

  def registerDelPrefixHandler(self,handler):
    """used to register a handler for del prefix events"""
    self.delPrefixHandlers.append(handler)

  def registerMovePrefixHandler(self,handler):
    """used to register a handler for del prefix events"""
    self.movePrefixHandlers.append(handler)

  def registerStateChangeHandler(self, handler):
      """used to register a handler for save state events"""
      self.saveStateChangeHandlers.append(handler)

  def fireAddPrefix(self,group,prefix, priority):
    """When called will fire each of the registered add prefix handlers"""
    for handler in self.addPrefixHandlers:
      handler(group,prefix, priority)

  def fireDelPrefix(self,group,prefix, priority):
    """When called will fire each of the registered del prefix handlers"""
    for handler in self.delPrefixHandlers:
      handler(group,prefix, priority)

  def fireMovePrefix(self,oldGroup,newGroup,prefix, priority):
    """when called will fire each of the registered move prefix handlers"""
    for handler in self.movePrefixHandlers:
      handler(oldGroup,newGroup,prefix, priority)

  def fireSaveState(self):
      """when called will fire each of the registered save state handlers"""
      for handler in self.saveStateChangeHandlers:
          handler(self.groups, self.prefix_list, self.prefixPriorities)

  def delGroupPrefix(self,group,targetPrefix):
    """looks for prefix and removes it if its associated with the sensor"""
    if(not self.groups.has_key(group)):
        return 0

    prefixList = self.groups[group]['prefixes']

    priority = self.getPrefixPriority(targetPrefix)

    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
	    #--- call function to remove this from the switch
        self.fireDelPrefix(group,targetPrefix, priority['priority'])
        #--- remove from list
        prefixList.pop(x)
        self.prefixCount = self.prefixCount -1
        if targetPrefix in self.prefix_list:
            self.prefix_list.remove(targetPrefix)
        if(self.prefixBW.has_key(targetPrefix)):
            del self.prefixBW[targetPrefix]
        if(targetPrefix in self.groups[group]['prefixes']):
            self.groups[group]['prefixes'].remove(targetPrefix)
        if(self.prefixPriorities.has_key(targetPrefix)):
            del self.prefixPriorities[targetPrefix]
        if(self.initialized):
            self.fireSaveState()
        return 1
      x = x+1
    return 0

  def addGroupPrefix(self,group,targetPrefix,bw=0):
    """adds a prefix to the sensor"""

    if(not self.groups.has_key(group)):
        self.logger.error("No Group: " + str(group) + " could be found")
        return 0

    if(self.prefixCount >= self.maxPrefixes):
        raise MaxPrefixesError("prefix greater than max prefixes")
    
    if targetPrefix in self.prefix_list:
        sensor = self.getPrefixGroup(targetPrefix)
        if sensor:
            self.logger.error(str(targetPrefix) + " already contained in " + str(sensor))
            return 0
    prefixList = list(self.groups[group]['prefixes'])
    priority = self.getPrefixPriority(targetPrefix)

    if(priority == None):
        self.prefixPriorities[targetPrefix] = {'priority': self.curr_priority, 'total': 100, 'bandwidth': 0}
        priority = self.prefixPriorities[targetPrefix]
        self.curr_priority += 100
    
    x = 0;
    for prefix in prefixList:
        if(targetPrefix == prefix):
        #--- already in list
            raise DuplicatePrefixError("Prefix already in list")
            return 0;
        elif(targetPrefix.Contains(prefix)):
            raise DuplicatePrefixError("Prefix is already contained by something else")
            return 0
        elif(prefix.Contains(targetPrefix)):
            raise DuplicatePrefixError("Prefix is already contained by something else")
            return 0

    #--- call function to add this to the switch
    try:
        self.fireAddPrefix(group,targetPrefix, priority['priority'])
    except MaxFlowCountError:
        return 0
    self.groups[group]['prefixes'].append(targetPrefix)
    self.prefixCount = self.prefixCount + 1
    self.prefixBW[targetPrefix] = bw
    if targetPrefix not in self.prefix_list:
        self.prefix_list.append(targetPrefix)
    if(self.initialized):
        self.fireSaveState()
    return 1;

  def moveGroupPrefix(self,oldGroup,newGroup,targetPrefix):
    """used to move a prefix from one sensor to another"""

    if(not self.groups.has_key(oldGroup) or not self.groups.has_key(newGroup)):
        return 0
    prefixList = self.groups[oldGroup]['prefixes']
    x = 0;
    
    priority = self.getPrefixPriority(targetPrefix)
    
    for prefix in prefixList:
      if(targetPrefix == prefix):
        #--- found
        prefixList.pop(x)
        self.groups[newGroup]['prefixes'].append(prefix)
        if(prefix in self.groups[oldGroup]['prefixes']):
            self.groups[oldGroup]['prefixes'].remove(targetPrefix)
        self.fireMovePrefix(oldGroup,newGroup,targetPrefix, priority['priority'])
        if(self.initialized):
            self.fireSaveState()
        return 1
      x = x+1 
    return 0


  def splitSensorPrefix(self,group,candidatePrefix,check=False):
      """used to split a prefix that is on a sensor"""
      # @param check : If set, checks that the bw on Candidate Prefix
      # is greater than configurable threshold, to prevent continous
      # split and merge
      try:
          subnets = self.splitPrefix(candidatePrefix)
          bw = self.prefixBW[candidatePrefix]
          if check:
              if float(bw/1000/1000) < float(self.sensorConfigurableThreshold):
                  self.logger.error("Candidate Prefix : " + str(candidatePrefix) + " bw " + str(bw/1000/1000) + " Mbps" )
                  self.logger.error("Configurable Threshold :" + str(self.sensorConfigurableThreshold))
                  self.logger.error("Preventing split of prefix " + str(candidatePrefix))
                  return 0
          self.logger.info( "split prefix "+str(candidatePrefix) +" bw "+str((bw / 1000 / 1000 )) + "Mbps")
          #--- update the bandwidth we are guessing is going to each prefix to smooth things, before real data is avail
          self.prefixBW[candidatePrefix] = 0
          priority = self.getPrefixPriority(candidatePrefix)
          
          incrementer = priority['total'] / len(subnets)
          cur_priority = priority['priority']
          prefixes = []
          #--- first, add the more specific rules
          for prefix in subnets:
              #--- set a guess that each of the 2 subnets gets half of the traffic
              prefixes.append(prefix)
              try:
                  prefixBw = bw / 2.0
              except ZeroDivisionError:
                  prefixBW = 0
              
              self.logger.debug( "  -- "+str(prefix)+" bw "+str((prefixBw / 1000 / 1000)) + "Mbps" )
              self.delGroupPrefix(group, candidatePrefix)
              self.prefixPriorities[prefix] = {'priority': cur_priority, 'total': incrementer}
              
              try:
                  self.addGroupPrefix(group, prefix, prefixBw)
              except MaxFlowCountError:
                  self.logger.error("Max Flow Count Reached")
                  self.addGroupPrefix(group, candidatePrefix)
                  for prefix in prefixes:
                      self.prefixPriorities.delete(prefix)
                  return 0
              cur_priority += incrementer

              #--- now remove the less specific and now redundant rule
          return 1

      except MaxPrefixlenError as e:
          self.logger.error( "max prefix len limit:  "+str(candidatePrefix) )
          return 0



  def mergeContiguousPrefixes(self,prefixList):
    """reviews a set of prefixes looking for 2 that are contiguous and merges them."""
    subnetDict = defaultdict(list)
    for prefix in prefixList:
        if prefix.version == 4:
            if(prefix._prefixlen > self.leastSpecificPrefixLen):
                supernet = prefix.Supernet()
                subnetDict[supernet].append(prefix)
        elif prefix.version == 6:
            if(prefix._prefixlen > self.ipv6LeastSpecificPrefixLen):
                supernet = prefix.Supernet()
                subnetDict[supernet].append(prefix)
    return subnetDict
      

  def splitPrefix(self,prefix):
    """takes a prefix and splits it into 2 subnets that by increasing masklen by 1 bit"""
    if(prefix.version == 4):
        self.logger.debug("Most Specific: " + str(self.mostSpecificPrefixLen))
        if(prefix.prefixlen <= int(self.mostSpecificPrefixLen) - 1):
            return prefix.Subnet()
        else:
            raise MaxPrefixlenError(prefix);   

    else:
        self.logger.debug("Most Specific: " + str(self.ipv6MostSpecificPrefixLen))
        if(prefix.prefixlen <= int(self.ipv6MostSpecificPrefixLen) - 1):
            return prefix.Subnet()
        else:
            raise MaxPrefixlenError(prefix);

  def splitPrefixForSensors(self,prefix,numSensors):
    """splits a prefix into subnets for balancing across, it will go up to the power of 2 value that contains numSensors"""
    x = 0
    subnetCount = 2**x
    while(subnetCount < numSensors):
      x = x+1
      subnetCount = 2**x

    return prefix.subnet(prefixlen_diff=x)

  def getSensorLoad(self):
      sensors = defaultdict(list)
      for group in self.groups:
          for sensor in self.groups[group]['sensors']:
              sensors[sensor] = self.groups[group]['sensors'][sensor]['load']
      return sensors

  def getPrefixBW(self, prefix):
      return self.prefixBW[prefix]

  def getPrefixes(self):
    """returns the set of prefixes and their current load"""
    return self.prefixBW

  def getPrefixGroup(self,targetPrefix):
    """returns the sensor the prefix is currently assigned to"""
    for group in self.groups:
        for prefix in self.groups[group]['prefixes']:
            if(prefix == targetPrefix):
                return group
    return None

  def getLargestPrefix(self,group):
    """returns the largest prefix assigned to the sensor"""
    if(self.groups.has_key(group)):
        best_len = 128;
        largestPrefix = None;
        for prefix in self.groups[group]['prefixes']:
            if (prefix._prefixlen < best_len):
                largestPrefix = prefix
                
        return largestPrefix;
    return None

  def getGroupBW(self,group):
      totalBW = 0
      for prefix in list(self.groups[group]['prefixes']):
          totalBW    = totalBW    +  self.prefixBW[prefix]
      return totalBW

  def getEstLoad(self,group,targetPrefix):
    """returns the estimated load impact for the specified prefix on the specified sensor"""
    #--- calculate the total address space the sensor has 
    totalHosts 		= 0;
    totalBW		= 0; 
    percentTotal	= 0;

    self.logger.debug("getEstLoad: "+str(group)+" "+str(targetPrefix))
    for prefix in self.groups[group]['prefixes']:
      totalHosts = totalHosts +  prefix.numhosts
      totalBW    = totalBW    +  self.prefixBW[prefix]

    self.logger.debug("Total BW for group = %s" % totalBW)

    if(self.ignorePrefixBW == 0):
      #--- use prefix bandwidth to estimate load
      targetBW     = self.prefixBW[targetPrefix]
      self.logger.debug("targetBW: %s" % targetBW)
      if(totalBW > 0 and targetBW > 0):
        percentTotal = targetBW / (totalBW * 1.0)
      else:
        percentTotal = 0

      return percentTotal
    else:
      #--- ignoring prefix load, do percent of address space
      percentTotal = targetPrefix.numhosts / float(totalHosts)
  
      if(self.ignoreSensorLoad == 0):
        #-- use sensor load to esitmate prefix laod
        return self.getGroupLoad(group) * percentTotal
      else:
        return percentTotal

  # finds two prefixes that are next to each other
  # when merged, bw is less than configurable threshold
  # deletes the two prefixes and adds the candidate prefix
  def merge(self):
      self.logger.debug("Balance By Merge")
      subnetDict = self.mergeContiguousPrefixes(self.prefix_list)
      
      if not subnetDict:
          return

      for candidatePrefix in subnetDict:
          prefix_list = []
          prefix_list = subnetDict[candidatePrefix]
          
          if len(prefix_list) != 2: continue
          
          prefix_a = prefix_list[0]
          prefix_b = prefix_list[1]
          bw1 = self.prefixBW[prefix_a]
          bw2 = self.prefixBW[prefix_b]
          aggBW = (bw1/1000/1000) + (bw2/1000/1000)
 
          self.logger.error("Prefixes :"  + str(prefix_a) + ", " + str(prefix_b) + " Aggregate BW : " + str(aggBW) + " Mbps" )
          self.logger.error("Configurable Threshold :" + str(self.sensorConfigurableThreshold))

          #if the bw is less than configurable threshold.
          if aggBW < self.sensorConfigurableThreshold:
              minLoad         = 100
              minSensor       = ""

              for group in self.groups.keys():

                  if(not self.getGroupStatus(group)): continue

              load = self.getGroupLoad(group)

              if(load < minLoad):
                  minLoad = load
                  minSensor = group;

              self.logger.debug("Min Group: " + str(minSensor))
              group_a = self.getPrefixGroup(prefix_a)
              group_b = self.getPrefixGroup(prefix_b)

              if candidatePrefix.version == 4:
                  if(candidatePrefix.prefixlen > self.mostSpecificPrefixLen):
                      return
              elif candidatePrefix.version == 6:
                  if(candidatePrefix.prefixlen > self.ipv6MostSpecificPrefixLen):
                      return
              else:
                  return

              #delete the prefixes
              self.logger.error("Merging Prefixes " + str(prefix_a) + ", " + str(prefix_b))
              
              self.delGroupPrefix(group_a,prefix_a)
              self.delGroupPrefix(group_b,prefix_b)
              
              #add the candidate prefix to min sesnor with aggBW
              self.logger.info("Adding Prefix : " + str(candidatePrefix) + " to " + str(minSensor) + " with bw " + str(aggBW) + "Mbps")
              try:
                  aggBW = aggBW*1000*1000
                  self.addGroupPrefix(minSensor, candidatePrefix, aggBW)
              except DuplicatePrefixError:
                  self.logger.debug("Already have prefix: " + str(candidatePrefix))
                  self.addGroupPrefix(group_a, prefix_a, bw1)
                  self.addGroupPrefix(group_b, prefix_b, bw2)
                  return
              except MaxFlowCountError:
                  self.logger.debug("Max Flow Count Error")
                  self.addGroupPrefix(group_a, prefix_a, bw1)
                  self.addGroupPrefix(group_b, prefix_b, bw2)
                  return
              return


  def balanceByIP(self):
    """method to balance based soly on IP space"""
     #--- calc load based on routable address space
    groupSpace = defaultdict(float)
    totalSpace  = 0
    maxMetric   = 0
    minMetric   = 1
    maxGroup   = ""
    minGroup   = ""

    for group in self.groups:
      # don't include disabled sensors
      if(not self.getGroupStatus(group)): continue

      for prefix in self.groups[group]['prefixes']:
          totalSpace = totalSpace + prefix.numhosts
          self.logger.debug( "group "+str(group)+" prefix "+str(prefix)+" space = "+str(prefix.numhosts))
          groupSpace[group] = groupSpace[group] + prefix.numhosts

    for group in self.groups:
      if(not self.getGroupStatus(group)): continue
      try:
        x = groupSpace[group] / float(totalSpace)
      except ZeroDivisionError:
          x = 0
      if(x > maxMetric):
        maxMetric   = x 
        maxGroup = group

      if(x < minMetric):
        minMetric   = x
        minGroup = group

    delta = maxMetric - minMetric
    self.logger.debug("delta: " + str(delta))
    self.logger.debug("Group load delta threshold: " + str(self.sensorLoadDeltaThreshold))

    if(delta >= self.sensorLoadDeltaThreshold):
        self.logger.debug("moving prefixes")
        #--- get the prefix with largest esitmated load from maxSensor
        candidatePrefix = self.getLargestPrefix(maxGroup)
        self.moveGroupPrefix(maxGroup,minGroup,candidatePrefix)
    else:
        self.logger.debug("everything is fine")


  def _balanceMove():
      tmpDict = defaultdict(float)
      for prefix in self.groups[maxGroup]['prefixes']:
          tmpDict[prefix] = prefixBW[prefix]
          
      candidatePrefixes = sorted(tmpDict,key=tmpDict.get,reverse=True)
      #--- see if we can move a prefix first
      for candidatePrefix in candidatePrefixes:
          estPrefixLoad = prefixBW[candidatePrefix]/float(totalBW)
          estNewGroupLoad = estPrefixLoad+minLoad;
              
          #--- check if it will fit on minSensor and if the new sensor will have less load than max sensor
          if(estNewGroupLoad <= 1 and estNewGroupLoad < (maxLoad-estPrefixLoad)):
              #--- it will fit on minsensor and provides a better balance, move it to minsensor
              self.moveGroupPrefix(maxGroup,minGroup,candidatePrefix)
              self.logger.info("Sensor prefix moved successfully")
              return


  def _calcGroupBW(self):
      #figure out total BW and group BW
      for group in self.groups:
          self.logger.debug("Group: " + str(group))
          self.logger.debug("Group Prefixes: {0}".format(self.groups[group]['prefixes']))
          groupBW = float(0)
          for prefix in self.groups[group]['prefixes']:
              #--- figure out total amount of traffic going over each sensor
              self.logger.debug("Prefix: " + str(prefix) + " BW: " + str((self.prefixBW[prefix]/1000/1000)) + "Mbps")
              groupBW += self.prefixBW[prefix]
          self.groups[group]['bandwidth'] =  groupBW
          #self.logger.debug("Group %s has bandwidth: %d" % str(group),float(groupBW))
      
      return

  #so here is our algorithm
  #given all of the groups calculate their load
  #as their bandwidth / total bandwidth to all groups
  #if the difference is > the min load delta balance
  #check to see if the highest loaded sensor has a prefix
  #we can move to the lowest loaded sensor if so move it
  #next attempt to split the highest load prefix on the highest loaded sensor

  def balanceByNetBytes(self, ignored_groups):
    """Balance by network traffic with no regard to sensor load"""

    #calcualtes all groups current bandwidth
    self._calcGroupBW()

    totalBW = 0
    #ok now get their load
    for group in self.groups:
        if group in ignored_groups: continue
        if not self.getGroupStatus(group): continue
        totalBW += self.groups[group]['bandwidth']

    if(totalBW <= 0):
        self.logger.error("Total Bandwidth: 0bps, not balancing")
        return

    for group in self.groups:
        if group in ignored_groups: continue
        if not self.getGroupStatus(group): continue
        self.groups[group]['load'] = self.groups[group]['bandwidth'] / totalBW

    #sort the groups by their bandwidth
    sortedLoadGroups = sorted(self.groups.items(),key=lambda (k,v): v['load'] ,reverse=True)

    maxGroup = None
    minGroup = None

    for group in sortedLoadGroups:
        if group[1]['group_id'] in ignored_groups: continue
        if not self.getGroupStatus(group[1]['group_id']): continue
        if maxGroup is None:
            maxGroup = group[1]['group_id']
        minGroup = group[1]['group_id']

    loadDelta = self.groups[maxGroup]['load'] - self.groups[minGroup]['load']

    self.logger.error("max sensor = '" + str(maxGroup) + "' load " + str(self.groups[maxGroup]['load']))
    self.logger.error("min sensor = '" + str(minGroup) + "' load " + str(self.groups[minGroup]['load']))
    self.logger.debug("loadminthreshold = " + str(self.sensorLoadMinThreshold))
    self.logger.error("load delta = "+str(loadDelta)+" max " + str(maxGroup) + " min " + str(minGroup))
    
    if(  self.groups[maxGroup]['load'] >= self.sensorLoadMinThreshold ):
        if(loadDelta >= self.sensorLoadDeltaThreshold):
            #base condition
            #if our biggest loaded sensor has 1 prefix at max-len do this again without that sensor
            #essentially say there is nothing we can do with it, and check on the rest of the sensors
            if len(self.groups[maxGroup]['prefixes']) == 1 and self.groups[maxGroup]['prefixes'][0].prefixlen > int(self.mostSpecificPrefixLen) - 1:
                ignored_groups.append(maxGroup)
                #it is possible that besides this one host (or X hosts) that everything is as balanced as we can get it
                self.balanceByNetBytes(ignored_groups)
                return
  
            #move a prefix
            
            tmpDict = defaultdict(float)
            for prefix in self.groups[maxGroup]['prefixes']:
                tmpDict[prefix] = self.prefixBW[prefix]
            
            sortedPrefixes = sorted(tmpDict,key=tmpDict.get,reverse=True)

    
            moved = False
            for prefix in sortedPrefixes:
                estPrefixLoad = self.prefixBW[prefix] / totalBW
                estNewGroupLoad = estPrefixLoad + self.groups[minGroup]['load']
                if(estNewGroupLoad <= 1 and estNewGroupLoad < (self.groups[maxGroup]['load'] - estPrefixLoad)):
                    self.moveGroupPrefix(maxGroup, minGroup, prefix)
                    sortedPrefixes.remove(prefix)
                    self.logger.info("Moved Prefix %s from group %s to group %s",str(prefix), str(maxGroup), str(minGroup))
                    self.groups[maxGroup]['load'] = self.groups[maxGroup]['load'] - estPrefixLoad
                    self.groups[minGroup]['load'] = self.groups[minGroup]['load'] + estPrefixLoad
                    moved = True
                else:
                    self.logger.debug("Could not move prefix %s from group %s to group %s because new load %f vs %f and prefix load=%f",
                                      str(prefix),str(maxGroup),str(minGroup),estNewGroupLoad,self.groups[maxGroup]['load'],estPrefixLoad)
                    
            if moved:
                return
            else:
                for prefix in sortedPrefixes:
                    if self.splitSensorPrefix(maxGroup, prefix, check=True):
                        self.logger.info("Sensor prefix %s on sensor %s was successfully split",str(prefix), str(maxGroup))
                                                
            self.merge()
            return

        else:
            self.logger.warn("below load Delta Threshold")

    else:
        self.logger.warn("below sensorLoadMinThreshold") 
 

  def balance(self):
      """evaluate sensor load and come up with better balance if possible"""
      """multistep process, spread across time, considers sensor with min and max load"""
      minLoad         = 100
      minSensor	    = ""
      
      maxLoad         = 0    
      maxSensor       = ""
      
      #both sensor load and bandwidth are disabled
      #just balance by total hosts
      if(self.ignoreSensorLoad and self.ignorePrefixBW):
          return self.balanceByIP()

      #balance by network traffic
      if(self.ignoreSensorLoad):
          return self.balanceByNetBytes([])

      prefixBW = self.prefixBW

      #--- find the current loads and figure out max, min and range
      if(self.ignoreSensorLoad == 0):
          #--- calc load by looking at sensor load
          for group in self.groups.keys():
              # don't include disabled sensors
              if(not self.getGroupStatus(group)): continue

              load = self.getGroupLoad(group)
              
              if(load > maxLoad):
                  maxLoad = load
                  maxSensor = group
                  
              if(load < minLoad):
                  minLoad = load
                  minSensor = group;

          loadDelta = maxLoad - minLoad;

          self.logger.debug("max sensor = '"+str(maxSensor)+"' load "+str(maxLoad))
          self.logger.debug("min sensor = '"+str(minSensor)+"' load "+str(minLoad))
          self.logger.debug("load delta = "+str(loadDelta))

          if(self.ignoreSensorLoad > 0 or maxLoad >= self.sensorLoadMinThreshold ):
              if(loadDelta >= self.sensorLoadDeltaThreshold):
                  #-- a sensor is above balance threshold and the delta is large enough to consider balancing
                  #--- get the prefix with largest esitmated load from maxSensor
                  candidatePrefix = self.getLargestPrefix(maxSensor)

                  if(candidatePrefix == None):
                      self.logger.error( "sensor "+maxSensor+" has no prefixes but claimes to have highest load?")
                      return 0;

                  estPreLoad = self.getEstLoad(maxSensor,candidatePrefix)
                  estNewSensorLoad = estPreLoad+minLoad;

                  #--- check if it will fit on minSensor and if the new sensor will have less load than max sensor 
                  if(estPreLoad <  (1 - minLoad) and estNewSensorLoad < maxLoad):
                      #--- if it will fit, move it to minsensor
                      self.moveGroupPrefix(maxSensor,minSensor,candidatePrefix)

                  else:
                  #--- will not fit, split, then leave on original sensor and retry later after
                  #--- better statistics are gathered 
                      self.logger.debug("-- need to split candidate and try again later after load measures");
                      try:
                          subnets = self.splitPrefix(candidatePrefix);
                          for prefix in subnets:
                              self.addGroupPrefix(maxSensor,prefix)
                              
                          self.delGroupPrefix(maxSensor,candidatePrefix)
                      except MaxPrefixlenError as e:
                          self.logger.warn( "at max prefix length limit" )
                      except MaxFlowCountError:
                          self.logger.warn("Max Flow Count is reached")
              else:
                  self.logger.warn("below load Delta Threshold")

          else:
              self.logger.warn("below sensorLoadMinThreshold")
              #self.logger.info("sensor prefixes: %s"%(self.sensorPrefixes))
