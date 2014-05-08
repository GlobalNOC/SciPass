#!/usr/bin/python

import time
import ipaddr
import pprint
import json
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
		 sensorLoadDeltaThresh	= .05):

    #--- used to limit the number of subnets / forwarding rules we install on the swtich
    self.maxPrefixes		     = maxPrefixes;
    self.prefixCount		     = 0;

    self.mostSpecificPrefixLen       = mostSpecificPrefixLen
    self.leastSpecificPrefixLen      = leastSpecificPrefixLen

    self.ignoreSensorLoad	     = ignoreSensorLoad
    self.sensorLoadMinThreshold      = sensorLoadMinThresh
    self.sensorLoadDeltaThreshold    = sensorLoadDeltaThresh


    self.ignorePrefixBW              = ignorePrefixBW
    self.sensorBandwidthMinThreshold = 1
    self.sensorLoad                  = defaultdict(list)
    self.sensorStatus                = defaultdict(list)
    self.sensorPrefixes              = defaultdict(list)
    
    #--- prefix bandwidth in GigaBits/sec
    self.prefixBW		     = defaultdict(float)
    self.prefixSensor	             = defaultdict(str)

    self.addPrefixHandlers = []
    self.delPrefixHandlers = []
    self.movePrefixHandlers = []

    return

  def __str__(self):
    """a string representation"""
    res = "Balancer: \n";
    res = res + "  Prefixes: "+str(self.sensorPrefixes)+"\n"
    res = res + "  Load: "+str(self.sensorLoad)+"\n";
    res = res + "  PrefixBW: "+str(self.prefixBW) +"\n"
    res = res + "  pre2sensor: "+str(self.prefixSensor)+"\n"
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
 

  def addSensor(self,sensor):
    """adds sensor, inits to load 0"""
    self.sensorLoad[sensor] = 0;
    return 1
 
  
  def setSensorLoad(self,sensor,load):
    """sets the load value for the sensor, 0-1 float is range"""
    self.sensorLoad[sensor] = load;
    return 1

  def setSensorStatus(self,sensor,status):
    """sets the load value for the sensor, 0-1 int is range"""
    self.sensorStatus[sensor] = status
 
    if(status == 0):
	print "sensor "+sensor+" status "+status
      #--- need to react to port down on sensor port by rebalancing
      #--- this is some thing we should be careful with
    return 1

  def setPrefixBW(self,prefix,bwTx,bwRx):
    """updates balancers understanding trafic bandwidth associated with each prefix"""
    #print "update prefixBW: "+str(prefix)+" "+str(bwTx/1000000.0)+" "+str(bwRx/1000000.0)
    self.prefixBW[prefix] = bwTx+bwRx
    return 1

  def registerAddPrefixHandler(self,handler):
    """used to register a handler for add prefix events"""
    self.addPrefixHandlers.append(handler)

  def registerDelPrefixHandler(self,handler):
    """used to register a handler for del prefix events"""
    self.delPrefixHandlers.append(handler)

  def registerMovePrefixHandler(self,handler):
    """used to register a handler for del prefix events"""
    self.movePrefixHandlers.append(handler)

    

  def fireAddPrefix(self,sensor,prefix):
    """When called will fire each of the registered add prefix handlers"""
    for handler in self.addPrefixHandlers:
      handler(sensor,prefix)

  def fireDelPrefix(self,sensor,prefix):
    """When called will fire each of the registered del prefix handlers"""
    for handler in self.delPrefixHandlers:
      handler(sensor,prefix)

  def fireMovePrefix(self,oldSensor,newSensor,prefix):
    """when called will fire each of the registered move prefix handlers"""
    for handler in self.movePrefixHandlers:
      handler(oldSensor,newSensor,prefix)

  def setSensorPrefixList(self,sensor,prefixList):
    """update the sensor's prefix list"""
    if(len(prefixList) >self.maxPrefixes):
        raise MaxPrefixesError(str(prefixList))

    #--- reset the list
    del self.sensorPrefixes[sensor][:]

    for prefix in prefixList:
        self.addSensorPrefix(sensor,prefix)

    return 1


  def delSensorPrefix(self,sensor,targetPrefix):
    """looks for prefix and removes it if its associated with the sensor"""
    prefixList = self.sensorPrefixes[sensor]
    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
	#--- call function to remove this from the switch
        self.fireDelPrefix(sensor,targetPrefix)
        #--- remove from list
        prefixList.pop(x)
        self.prefixCount = self.prefixCount -1
        del self.prefixBW[targetPrefix]
        del self.prefixSensor[targetPrefix]
        return 1
      x = x+1
    return 0

  def addSensorPrefix(self,sensor,targetPrefix,bw=0):
    """adds a prefix to the sensor"""
    if(self.prefixCount >= self.maxPrefixes):
        raise MaxPrefixesError()

    prefixList = self.sensorPrefixes[sensor]
    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
        #--- already in list
        raise DuplicatePrefixError()
        return 0;

    #--- call function to add this to the switch
    self.fireAddPrefix(sensor,targetPrefix)
    prefixList.append(targetPrefix)
    self.prefixCount = self.prefixCount +1
    self.prefixBW[targetPrefix] = bw
    self.prefixSensor[targetPrefix] = sensor

    return 1;

  def moveSensorPrefix(self,oldSensor,newSensor,targetPrefix):
    """used to move a prefix from one sensor to another"""
    prefixList = self.sensorPrefixes[oldSensor]
    x = 0;
    for prefix in prefixList:
      if(targetPrefix == prefix):
        #--- found
        prefixList.pop(x)
        self.sensorPrefixes[newSensor].append(prefix)
        self.prefixSensor[targetPrefix] = newSensor
        self.fireMovePrefix(oldSensor,newSensor,targetPrefix)
      x = x+1 
    return 0;


  def splitSensorPrefix(self,sensor,candidatePrefix):
    """used to split a prefix that is on a sensor"""
    try:
      subnets = self.splitPrefix(candidatePrefix)
      bw = self.prefixBW[candidatePrefix]
      print "split prefix "+str(candidatePrefix) +" bw "+str(bw)
      #--- update the bandwidth we are guessing is going to each prefix to smooth things, before real data is avail
      self.prefixBW[candidatePrefix] = 0

      #--- first, add the more specific rules
      for prefix in subnets:
        #--- set a guess that each of the 2 subnets gets half of the traffic
        try:
          prefixBw = bw / 2.0
        except ZeroDivisionError:
          prefixBW = 0
        #print "  -- "+str(prefix)+" bw "+str(prefixBw)
        self.addSensorPrefix(sensor,prefix,prefixBw)

      #--- now remove the less specific and now redundant rule
      self.delSensorPrefix(sensor,candidatePrefix)
      return 1
    except MaxPrefixlenError as e:
      print "max prefix len limit:  "+str(candidatePrefix)
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
    if(prefix._prefixlen <= self.mostSpecificPrefixLen -1):
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
    return self.sensorLoad

  def getPrefixes(self):
    """returns the set of prefixes and their current load"""
    return self.prefixBW

  def getPrefixSensor(self,targetPrefix):
    """returns the sensor the prefix is currently assigned to"""
    return self.prefixSensor[targetPrefix]

  def getLargestPrefix(self,sensor):
    """returns the largest prefix assigned to the sensor"""
    best_len = 128;
    largestPrefix = None;
    for prefix in self.sensorPrefixes[sensor]:
      if (prefix._prefixlen < best_len):
        largestPrefix = prefix

    return largestPrefix;

  def getEstLoad(self,sensor,targetPrefix):
    """returns the estimated load impact for the specified prefix on the specified sensor"""
    #--- calculate the total address space the sensor has 
    totalHosts 		= 0;
    totalBW		= 0; 
    percentTotal	= 0;

    #print"getEstLoad: "+sensor+" "+str(targetPrefix)
    for prefix in self.sensorPrefixes[sensor]:
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
        return self.sensorLoad[sensor] * percentTotal
      else:
        return percentTotal

  
  def balanceByIP(self):
    """method to balance based soly on IP space"""
     #--- calc load based on routable address space
    sensorSpace = defaultdict(float)
    totalSpace  = 0
    maxMetric   = 0
    minMetric   = 1
    maxSensor   = ""
    minSensor   = ""

    for sensor in self.sensorPrefixes.keys():
      for prefix in self.sensorPrefixes[sensor]:
        totalSpace = totalSpace + prefix.numhosts
        #print "sensor "+sensor+" prefix "+str(prefix)+" space = "+str(prefix.numhosts)
        sensorSpace[sensor] = sensorSpace[sensor] + prefix.numhosts

    for sensor in self.sensorLoad.keys():
      x =sensorSpace[sensor] / float(totalSpace)

      if(x > maxMetric):
        maxMetric   = x 
        maxSensor = sensor

      if(x < minMetric):
        minMetric   = x
        minSensor = sensor

    delta = maxMetric - minMetric

    if(delta >= self.sensorLoadDeltaThreshold):

      #--- get the prefix with largest esitmated load from maxSensor
      candidatePrefix = self.getLargestPrefix(maxSensor)

      self.moveSensorPrefix(maxSensor,minSensor,candidatePrefix)

      #try:
      #  subnets = self.splitPrefix(candidatePrefix);
      #  for prefix in subnets:
      #    self.addSensorPrefix(minxSensor,prefix)

      #  self.delSensorPrefix(maxSensor,candidatePrefix)
      #except MaxPrefixlenError as e:
      #  print "at max prefix length limit"

      #else:
      #  print("below load Delta Threshold")


  def balanceByNetBytes(self):
    """Balance by network traffic with no regard to sensor load"""
    minLoad         = 100
    minSensor       = ""

    maxLoad         = 0    
    maxSensor       = ""

    prefixBW = self.prefixBW
    totalBW  = 0
    sensorBW = defaultdict(float)
    for sensor in self.sensorPrefixes.keys():
      for prefix in self.sensorPrefixes[sensor]:
        #--- figure out total amount of traffic going over each sensor
        totalBW  =totalBW + prefixBW[prefix]
        sensorBW[sensor] = sensorBW[sensor] + prefixBW[prefix]

    for sensor in self.sensorLoad.keys():
      if(totalBW > 0):
        load =sensorBW[sensor] / float(totalBW)
      else:
        load = 0

      if(load > maxLoad):
        maxLoad = load
        maxSensor = sensor

      if(load < minLoad):
        minLoad = load
        minSensor = sensor;

    loadDelta = maxLoad - minLoad;

    #---
   
    #print("max sensor = '"+maxSensor+"' load "+str(maxLoad))
    #print("min sensor = '"+minSensor+"' load "+str(minLoad))
    print("load delta = "+str(loadDelta)+" max "+maxSensor+" min "+minSensor)

    if( maxLoad >= self.sensorLoadMinThreshold ):
      if(loadDelta >= self.sensorLoadDeltaThreshold):
        #-- a sensor is above balance threshold and the delta is large enough to consider balancing
        #--- get the prefix with largest esitmated load from maxSensor
	tmpDict = defaultdict(float)
        for prefix in self.sensorPrefixes[maxSensor]:
          tmpDict[prefix] = prefixBW[prefix]

        #--- see if we can move a prefix first 
        for candidatePrefix in sorted(tmpDict,key=tmpDict.get,reverse=True):
          estPrefixLoad = prefixBW[candidatePrefix]/float(totalBW)
          estNewSensorLoad = estPrefixLoad+minLoad;

          #--- check if it will fit on minSensor and if the new sensor will have less load than max sensor 
          if(estNewSensorLoad <=  1  and estNewSensorLoad < (maxLoad-estPrefixLoad)):
            #--- it will fit on minsensor and provides a better balance, move it to minsensor
            self.moveSensorPrefix(maxSensor,minSensor,candidatePrefix)
            return


        #--- could not move something, consider splitting a prefix 
        for candidatePrefix in sorted(tmpDict,key=tmpDict.get,reverse=True):
          if(self.splitSensorPrefix(maxSensor,candidatePrefix)):
            #--- success
            break
      else:
        print("below load Delta Threshold")

    else:
      print("below sensorLoadMinThreshold") 
 

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
        load = self.sensorLoad[sensor]
      
        if(load > maxLoad):
          maxLoad = load
	  maxSensor = sensor

        if(load < minLoad):
          minLoad = load
          minSensor = sensor;

      loadDelta = maxLoad - minLoad;

    print("max sensor = '"+maxSensor+"' load "+str(maxLoad))
    print("min sensor = '"+minSensor+"' load "+str(minLoad))
    print("load delta = "+str(loadDelta))
    if(self.ignoreSensorLoad > 0 or maxLoad >= self.sensorLoadMinThreshold ):
      if(loadDelta >= self.sensorLoadDeltaThreshold):
        #-- a sensor is above balance threshold and the delta is large enough to consider balancing

        #--- get the prefix with largest esitmated load from maxSensor
        candidatePrefix = self.getLargestPrefix(maxSensor)

        if(candidatePrefix == None):
          print "sensor "+maxSensor+" has no prefixes but claimes to have highest load?"
          return 0;

        estPreLoad = self.getEstLoad(maxSensor,candidatePrefix)
        estNewSensorLoad = estPreLoad+minLoad;
        #print("prefix: "+str(candidatePrefix)+"' est prefix load "+str(estPreLoad)+" est new sensor load "+str(estNewSensorLoad));
        #--- check if it will fit on minSensor and if the new sensor will have less load than max sensor 
        if(estPreLoad <  (1 - minLoad) and estNewSensorLoad < maxLoad):
          #--- if it will fit, move it to minsensor
          self.moveSensorPrefix(maxSensor,minSensor,candidatePrefix)
          #--- as a simulation hack (MUST REMOVE THIS SOON) lets guess at what the new load will be
          #self.setSensorLoad(maxSensor,self.sensorLoad[maxSensor]-estPreLoad)
          #self.setSensorLoad(minSensor,estNewSensorLoad) 

        else:
          #--- will not fit, split, then leave on original sensor and retry later after
 	  #--- better statistics are gathered 
          #print("-- need to split candidate and try again later after load measures");

 	  try:
            subnets = self.splitPrefix(candidatePrefix);
            for prefix in subnets:
              self.addSensorPrefix(maxSensor,prefix)

            self.delSensorPrefix(maxSensor,candidatePrefix)
          except MaxPrefixlenError as e:
            print "at max prefix length limit"
           
      else:
        print("below load Delta Threshold")

    else:
      print("below sensorLoadMinThreshold")
  
      

