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


class SimpleBalancer:
  """A simple balancer using only OpenFlow"""
  def __init__(  self,
                 ignoreSensorLoad	= 1,
                 ignorePrefixBW         = 1,
		 maxPrefixes		= 32,
  		 mostSpecificPrefixLen	= 29,
 		 leastSpecificPrefixLen	= 24,
     		 sensorLoadMinThresh	= .02,
		 sensorLoadDeltaThresh	= .05,
                 logger                 = None):
          
      if(logger == None):
          logging.basicConfig()
          self.logger = logging.getLogger(__name__)
      else:
          self.logger = logger
      #--- used to limit the number of subnets / forwarding rules we install on the swtich
      self.maxPrefixes		       = maxPrefixes;
      self.prefixCount		       = 0;

      self.mostSpecificPrefixLen       = mostSpecificPrefixLen
      self.leastSpecificPrefixLen      = leastSpecificPrefixLen
  
      self.ignoreSensorLoad	       = ignoreSensorLoad
      self.sensorLoadMinThreshold      = float(sensorLoadMinThresh)
      self.sensorLoadDeltaThreshold    = float(sensorLoadDeltaThresh)


      self.ignorePrefixBW              = ignorePrefixBW
      self.sensorBandwidthMinThreshold = 1
      self.groups                     = defaultdict(list)
      
      #--- prefix bandwidth in GigaBits/sec
      self.prefixBW		       = defaultdict(float)

      self.addPrefixHandlers  = []
      self.delPrefixHandlers  = []
      self.movePrefixHandlers = []
      
      return
  
  def __str__(self):
      """a string representation"""
      res = "Balancer: \n";
 #     res = res + "  Prefixes: "+str(self.sensorPrefixes)+"\n"
 #     res = res + "  Load: "+str(self.sensorLoad)+"\n";
 #     res = res + "  PrefixBW: "+str(self.prefixBW) +"\n"
 #     res = res + "  pre2sensor: "+str(self.prefixSensor)+"\n"
      return res 

  def __repr__(self):
      return json.dumps(self,default=lambda o: o.__dict__, sort_keys=True, indent=4)

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

      status = "Balance Method: "+mode+":\n";

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
 

  def distributePrefixes(self, prefix_array):
      self.logger.debug("Distrbiuting prefixes")
      for prefix in prefix_array:
          self.logger.debug("prefix len: " + str(prefix.prefixlen))
          self.logger.debug("least speciifc: " + str(self.leastSpecificPrefixLen))
          if(prefix.prefixlen > self.leastSpecificPrefixLen):
              self.logger.debug("prefix exceeds the most specific prefix len")
              #split it in half and try again
              self.distributePrefixes( self.splitPrefix(prefix))
          else:
              group = self.groups.keys()[0]
              self.logger.debug(group)
              self.addGroupPrefix( self.groups[group]['group_id'] , prefix, 0)
              self.balanceByIP()
              
          
              

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
    if(self.prefixBW.has_key(prefix)):
        self.prefixBW[prefix] = bwTx+bwRx
        return 1
    self.logger.error( "Error updating prefixBW... prefix does not exist")
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

  def fireAddPrefix(self,group,prefix):
    """When called will fire each of the registered add prefix handlers"""
    for handler in self.addPrefixHandlers:
      handler(group,prefix)

  def fireDelPrefix(self,group,prefix):
    """When called will fire each of the registered del prefix handlers"""
    for handler in self.delPrefixHandlers:
      handler(group,prefix)

  def fireMovePrefix(self,oldGroup,newGroup,prefix):
    """when called will fire each of the registered move prefix handlers"""
    for handler in self.movePrefixHandlers:
      handler(oldGroup,newGroup,prefix)


  def delGroupPrefix(self,group,targetPrefix):
    """looks for prefix and removes it if its associated with the sensor"""
    if(not self.groups.has_key(group)):
        return 0

    prefixList = self.groups[group]['prefixes']

    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
	    #--- call function to remove this from the switch
        self.fireDelPrefix(group,targetPrefix)
        #--- remove from list
        prefixList.pop(x)
        self.prefixCount = self.prefixCount -1
        del self.prefixBW[targetPrefix]
#        del self.prefixSensor[targetPrefix]
        return 1
      x = x+1
    return 0

  def addGroupPrefix(self,group,targetPrefix,bw=0):
    """adds a prefix to the sensor"""

    if(not self.groups.has_key(group)):
        self.logger.error("No Group: " + str(group) + " could be found")
        return 0

    if(self.prefixCount >= self.maxPrefixes):
        raise MaxPrefixesError()
    
    prefixList = list(self.groups[group]['prefixes'])

    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
        #--- already in list
        raise DuplicatePrefixError()
        return 0;

    #--- call function to add this to the switch
    self.fireAddPrefix(group,targetPrefix)
    self.groups[group]['prefixes'].append(targetPrefix)
    self.prefixCount = self.prefixCount + 1
    self.prefixBW[targetPrefix] = bw
    #self.prefixSensor[targetPrefix] = sensor

    return 1;

  def moveGroupPrefix(self,oldGroup,newGroup,targetPrefix):
    """used to move a prefix from one sensor to another"""
#    if(not self.sensorLoad.has_key(oldSensor) or not self.sensorLoad.has_key(newSensor)):
    if(not self.groups.has_key(oldGroup) or not self.groups.has_key(newGroup)):
        return 0
    prefixList = self.groups[oldGroup]['prefixes']
    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
        #--- found
        prefixList.pop(x)
        self.groups[newGroup]['prefixes'].append(prefix)
#        self.prefixSensor[targetPrefix] = newSensor
        self.fireMovePrefix(oldGroup,newGroup,targetPrefix)
        return 1
      x = x+1 
    return 0


  def splitSensorPrefix(self,group,candidatePrefix):
      """used to split a prefix that is on a sensor"""
      try:
          subnets = self.splitPrefix(candidatePrefix)
          bw = self.prefixBW[candidatePrefix]
          self.logger.error( "split prefix "+str(candidatePrefix) +" bw "+str(bw))
          #--- update the bandwidth we are guessing is going to each prefix to smooth things, before real data is avail
          self.prefixBW[candidatePrefix] = 0
          
          #--- first, add the more specific rules
          for prefix in subnets:
              #--- set a guess that each of the 2 subnets gets half of the traffic
              try:
                  prefixBw = bw / 2.0
              except ZeroDivisionError:
                  prefixBW = 0
              
              self.logger.debug( "  -- "+str(prefix)+" bw "+str(prefixBw) )
              self.addGroupPrefix(group,prefix,prefixBw)

              #--- now remove the less specific and now redundant rule
              self.delGroupPrefix(group,candidatePrefix)
          return 1
      except MaxPrefixlenError as e:
          self.logger.error( "max prefix len limit:  "+str(candidatePrefix) )
          return 0



  def mergeContiguousPrefixes(self,prefixList):
    """reviews a set of prefixes looking for 2 that are contiguous and merges them."""
    subnetDict = {}
    for prefix in prefixList:
       if(prefix._prefixlen > self.leastSpecificPrefixLen):
         supernet = prefix.Supernet()
         if(not  subnetDict.has_key(supernet)):
           subnetDict[supernet] = prefix

    return subnetDict.keys()
      

  def splitPrefix(self,prefix):
    """takes a prefix and splits it into 2 subnets that by increasing masklen by 1 bit"""
    self.logger.debug("Most Specific: " + str(self.mostSpecificPrefixLen))
    if(prefix._prefixlen <= self.mostSpecificPrefixLen - 1):
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

    if(self.ignorePrefixBW == 0):
      #--- use prefix bandwidth to estimate load
      targetBW     = self.prefixBW[targetPrefix]
      if(totalBW > 0 and targetBW > 0):
        percentTotal = totalBW / targetBW
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

  def balanceByNetBytes(self):
    """Balance by network traffic with no regard to sensor load"""
    minLoad         = 100
    minGroup       = ""

    maxLoad         = 0    
    maxGroup       = ""

    prefixBW = self.prefixBW
    totalBW  = 0
    groupBW = defaultdict(float)
    for group in self.groups:
      # don't include disabled sensors
      if(not self.getGroupStatus(group)): continue

      for prefix in self.groups[group]['prefixes']:
        #--- figure out total amount of traffic going over each sensor
        totalBW  =totalBW + prefixBW[prefix]
        groupBW[group] = groupBW[group] + prefixBW[prefix]

    for group in self.groups:
      # don't include disabled sensors
      if(not self.getGroupStatus(group)): continue

      if(totalBW > 0):
        load =groupBW[group] / float(totalBW)
      else:
        load = 0

      if(load > maxLoad):
        maxLoad = load
        maxGroup = group

      if(load < minLoad):
        minLoad = load
        minGroup = group;

    loadDelta = maxLoad - minLoad;

    #---
   
    self.logger.debug("max sensor = '"+str(maxGroup)+"' load "+str(maxLoad))
    #print("min sensor = '"+minSensor+"' load "+str(minLoad))
    self.logger.debug("load delta = "+str(loadDelta)+" max "+str(maxGroup)+" min "+str(minGroup))

    if( maxLoad >= self.sensorLoadMinThreshold ):
      if(loadDelta >= self.sensorLoadDeltaThreshold):
        #-- a sensor is above balance threshold and the delta is large enough to consider balancing
        #--- get the prefix with largest esitmated load from maxSensor
	tmpDict = defaultdict(float)
        for prefix in self.groups[maxGroup]['prefixes']:
          tmpDict[prefix] = prefixBW[prefix]

        #--- see if we can move a prefix first 
        for candidatePrefix in sorted(tmpDict,key=tmpDict.get,reverse=True):
          estPrefixLoad = prefixBW[candidatePrefix]/float(totalBW)
          estNewGroupLoad = estPrefixLoad+minLoad;

          #--- check if it will fit on minSensor and if the new sensor will have less load than max sensor 
          if(estNewGroupLoad <=  1  and estNewGroupLoad < (maxLoad-estPrefixLoad)):
            #--- it will fit on minsensor and provides a better balance, move it to minsensor
            self.moveGroupPrefix(maxGroup,minGroup,candidatePrefix)
            return


        #--- could not move something, consider splitting a prefix 
        for candidatePrefix in sorted(tmpDict,key=tmpDict.get,reverse=True):
          if(self.splitSensorPrefix(maxGroup,candidatePrefix)):
            #--- success
            break
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
      
      if(self.ignoreSensorLoad and self.ignorePrefixBW):
          return self.balanceByIP()

      if(self.ignoreSensorLoad):
          return self.balanceByNetBytes()

      prefixBW = self.prefixBW

      #--- find the current loads and figure out max, min and range
      if(self.ignoreSensorLoad == 0):
          #--- calc load by looking at sensor load
          for sensor in self.sensorLoad.keys():
              # don't include disabled sensors
              if(not self.getSensorStatus(sensor)): continue

              load = self.sensorLoad[sensor]
              
              if(load > maxLoad):
                  maxLoad = load
                  maxSensor = sensor
                  
              if(load < minLoad):
                  minLoad = load
                  minSensor = sensor;

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
                      self.moveSensorPrefix(maxSensor,minSensor,candidatePrefix)

                  else:
                  #--- will not fit, split, then leave on original sensor and retry later after
                  #--- better statistics are gathered 
                      self.logger.debug("-- need to split candidate and try again later after load measures");
                      try:
                          subnets = self.splitPrefix(candidatePrefix);
                          for prefix in subnets:
                              self.addSensorPrefix(maxSensor,prefix)
                              
                          self.delSensorPrefix(maxSensor,candidatePrefix)
                      except MaxPrefixlenError as e:
                          self.logger.warn( "at max prefix length limit" )
           
              else:
                  self.logger.warn("below load Delta Threshold")

          else:
              self.logger.warn("below sensorLoadMinThreshold")
              #self.logger.info("sensor prefixes: %s"%(self.sensorPrefixes))
