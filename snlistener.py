#Needs:

#Receipt method that receives an array from a sensor and patches it into the 'live' one

#Reboot signal method (might not be possible, not sure)

#Warning method for logging the addys of nodes that havent been tripped in a while
#to mark them for maintenance attention

#possible sensor report format: Sender ID, speed int (low res), rising or falling direction

import uuid
import logging
import time
import datetime
import threading
import schedule
import atexit
import os
import Queue
import math
import sys
from operator import sub

logging.basicConfig(filename='logs.log',level=logging.DEBUG) #TODO get this pointed at good directory in a cross-platform way
isHardWareConnected = False

if isHardWareConnected:
    import RPi.GPIO as gpio
    import smbus
    bus = smbus.SMBus(1)
    address = '0x04' #Arduino subject address

def readNumber():
    number = bus.read_byte(address)
    # number = bus.read_byte_data(address, 1)
    return number

Channels_Per_Sensor = 12
#Intent: match sensor nodes to lights
#TODO make this a convenient json file thing for customizing
#30 lights, 4 channels each
RenderMap = {
    1: [x for x in range(Channels_Per_Sensor * 1)],
    2: [x for x in range(Channels_Per_Sensor * 1, Channels_Per_Sensor * 2)],
    3: [x for x in range(Channels_Per_Sensor * 2, Channels_Per_Sensor * 3)],
    4: [x for x in range(Channels_Per_Sensor * 3, Channels_Per_Sensor * 4)],
    5: [x for x in range(Channels_Per_Sensor * 4, Channels_Per_Sensor * 5)],
    6: [x for x in range(Channels_Per_Sensor * 5, Channels_Per_Sensor * 6)],
    7: [x for x in range(Channels_Per_Sensor * 6, Channels_Per_Sensor * 7)],
    8: [x for x in range(Channels_Per_Sensor * 7, Channels_Per_Sensor * 8)],
    9: [x for x in range(Channels_Per_Sensor * 8, Channels_Per_Sensor * 9)],
    10:[x for x in range(Channels_Per_Sensor * 9, Channels_Per_Sensor * 10)]
}

LiveModifiers = {}
Frame_Queue = Queue.Queue() #we play from this

Business_Threshold = 1500 #total guess here
Busy_Color = [75,125,255,75] * 128
Busy_Mode = False
#we'll divide intensity readings by this
Intensity_Modifier = 10
#we'll multiply channel modifiers by this to ease spatially
Intensity_Dropoff = 1.0/2

Previous_Readings = []

Default_Color = [125,125,25,75]
Default_Modifier_Bias = [15,15,50,50] #will be multiplying intensity modifiers by this, basically...

def CatchReading(senderId, dir, intensity):
    RenderReading(senderId, intensity)
    if len(LiveModifiers) < 2: #in a calm state we might only have one reading come in at a time, so just chuck it on the stack
        MergeModifiers()

def QueryReadings(readings):
    global Previous_Readings
    global Busy_Mode
    Current_Readings = []
    #bus.getreadings whatever
    Readings_Delta = map(abs(sub), Previous_Readings, Current_Readings) #will this work?
    Business = sum(Readings_Delta)
    if Business > Business_Threshold:
        Busy_Mode = True #Challenge: obliterate this variable to push code in fuctional direction
        RenderBusyColor()
        Previous_Readings
    else:
        Busy_Mode = False
        RenderReadingSet(readings)
    Previous_Readings = Current_Readings

def RenderBusyColor():
    global Busy_Color
    layerId = uuid.uuid4()
    LiveModifiers[layerId] = Busy_Color

# Intent: catch a sensor packet and create a set of channel modifiers to be layered onto the universe in another function
def RenderReading(senderId, intensity):
    layerId = uuid.uuid4()
    global RenderMap
    global Intensity_Modifier
    global LiveModifiers
    targetLights = RenderMap[senderId] #grab a list of lights that correspond to the sensor that spoke
    outputLayer = []
    intensity_change = intensity/Intensity_Modifier
    base_intensity = [ch / Intensity_Modifier for ch in Default_Modifier_Bias]

    startlight = targetLights[0]
    if startlight != 0: #add some padding for lights that fall in the midst of the universe so we can cleanly merge later
        for space in range(0, startlight * 4):
            outputLayer.append(-1) #a -1 flag tells the merge function what to 'not touch', not sure how that will work yet

    for light in range(len(targetLights)):
        if light == 0 or light == len(targetLights)-1:
            channels = [ch * Intensity_Dropoff for ch in base_intensity]
            for channel in channels:
                outputLayer.append(channel)
        else:
            for channel in base_intensity:
                outputLayer.append(channel)

    LiveModifiers[layerId] = outputLayer

#Intent: address the likely I2C scenario of regularly prodding a bus to get a whole set of readings.
#TODO: we're ending up with an extra reading. find out why
def RenderReadingSet(readings):
    layerId = uuid.uuid4()
    global RenderMap
    global Intensity_Modifier
    global LiveModifiers
    outputLayer = [0] * 512
    for reading in readings:
        targetLights = RenderMap[reading[0]] #grab a list of lights that correspond to the sensor that spoke

        intensity_change = reading[1]/Intensity_Modifier
        base_intensity = [ch / Intensity_Modifier + intensity_change for ch in Default_Modifier_Bias]

        for light in range(len(targetLights)):
            startchannel = targetLights[light] * 4
            outputLayer[startchannel] = base_intensity[0]
            outputLayer[startchannel + 1] = base_intensity[1]
            outputLayer[startchannel + 2] = base_intensity[2]
            outputLayer[startchannel + 3] = base_intensity[3]

    LiveModifiers[layerId] = outputLayer

#The fun part. Given a set of channel modifiers, squish them down into eachother so we have on summed-up reading for each channel.
#at some point, figuring out when in time to do this will be important.
#This is being moved into a worker thread... but why? If we get our data in a synchronous way from i2c, we can just call this.
#maybe just hang onto both implementations
def MergeModifiers():
    if len(LiveModifiers) < 2:
        mergedCopy = LiveModifiers.values()[0]
    else:
        mergedCopy = []
        #merge code here
    Frame_Queue.put(mergedCopy)
    return
            
#CatchReading(1, 0, 255)

QueryReadings([[1, 25],[2, 215],[3, 150]])


