#TODO: introduce abstraction layer above Serials so we can loop over all the channels
#at once and then let the Serial render layer chunk it all up

import sys
import serial
import time
import logging
from multiprocessing import Process, Queue
from random import randint
from operator import add

DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY = chr(6)+chr(1)+chr(2)
DMXINIT1 = chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2 = chr(10)+chr(02)+chr(0)+chr(0)+chr(0)

class ImmediatePlayer(Process):
    """A Process which catches packets of contour data from OpenCV and associates their locations to DMX output channels.
        Args:
            Player Settings (playerutils.OpenCVPlayerSettings),
            Color Settings (playerutils.ColorSettings)
    """
    def __init__(self, _playersettings, _colorsettings):
        super(ImmediatePlayer, self).__init__()
        print 'starting worker'
        self.isHardwareConnected = True #debug flag for working without the dmx harness
        self.dmxData = []
        self.cont = True
        self.universes = _playersettings.universes
        self.dmxDataOne = [chr(0)]* 513
        self.dmxDataTwo = [chr(0)]* 513
        if self.isHardwareConnected:
            try:
                self.serialOne = serial.Serial('/dev/ttyUSB0', baudrate=57600)
                self.serialTwo = serial.Serial('/dev/ttyUSB1', baudrate=57600)
            except:
                print "Error: could not open Serial port"
                logging.info("An issue has occurred with one of the Serial Ports. Exiting...")
                self.cont = False
                #sys.exit(0)
        else:
            print "Running in dummy mode with no Serial Output!"

        self.verbose = True
        self.dataqueue = _playersettings.dataqueue
        self.jobqueue = _playersettings.jobqueue
        self.colors = _colorsettings
        self.channelsinuse = _playersettings.lights * _playersettings.channelsperlight
        self.lightsinuse = _playersettings.lights
        self.settings = _playersettings

        self.baseframe = self.colors.base*_playersettings.lights
        self.dimframe = self.colors.dimmed*_playersettings.lights
        self.peakframe = self.colors.peak*_playersettings.lights
        self.busyframe = self.colors.busy*_playersettings.lights
        self.nightframe = self.colors.night*_playersettings.lights

        self.increment = self.colors.increment
        self.decrement = self.colors.decrement
        
        #Prev Frame and Goal Frame are containers for data pertaining to ALL interactive channels.
        #They get split up for rendering and don't have anything to do with DMX packets.
        self.status = [0]*136
        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        self.heats = [0]*136
        self.sustain = _playersettings.sustain
        self.backfills = self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]
        self.playTowardLatest()

    def setchannelOnOne(self, chan, _intensity):
        """Set intensity on channel"""
        intensity = int(_intensity)
        if chan > 512:
            chan = 512
        if chan < 0:
            chan = 0
        if intensity > 255:
            intensity = 255
        if intensity < 0:
            intensity = 0
        self.dmxDataOne[chan] = chr(intensity)

    def setchannelOnTwo(self, chan, _intensity):
        """Set intensity on channel"""
        intensity = int(_intensity)
        if chan > 512:
            chan = 512
        if chan < 0:
            chan = 0
        if intensity > 255:
            intensity = 255
        if intensity < 0:
            intensity = 0
        self.dmxDataTwo[chan] = chr(intensity)


    def render(self, _payloadOne, _payloadTwo):
        if self.isHardwareConnected:
            sdata = ''.join(self.dmxDataOne)
            self.serialOne.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)
            sdata2 = ''.join(self.dmxDataTwo)
            self.serialTwo.write(DMXOPEN+DMXINTENSITY+sdata2+DMXCLOSE)

    def constructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _temp = self.colors.base*136
        _fixturehue = self.colors.speeds[0]
        _startchannel = 0
        #for channelheat in range(0,136): #cool all the channels
        #    self.heats[channelheat] -= 1
        for x in range(0, 136):
            if _cdcs[x] > 1:
                #hot spot
                if x > 0:
                    _startchannel = x * 4
                if _startchannel > 4: #conditionally brighten the previous fixture
                    for ch in range(-4, 0):
                        _temp[_startchannel + ch] = _fixturehue[ch+4]
                for ch in range(0, 4):
                    _temp[_startchannel + ch] = _fixturehue[ch]
                if _startchannel + 7 < 544:  #conditionally brighten the next fixture
                    for ch in range(4, 8):
                        _temp[_startchannel + ch] = _fixturehue[ch-4]
        return _temp

    def run(self):
        while self.cont:
            if not self.dataqueue.empty():
                self.compileLatestContours(self.dataqueue.get())
            self.playTowardLatest()

    def stop(self):
        print 'Terminating...'
        self.cont = False
        super(ImmediatePlayer, self).terminate()

    def compileLatestContours(self, _contours):
        """When a set of contours comes in, build a goal frame out of it."""
        for y in range(0, 136):
            self.status[y] -=1
        for x in range(0, len(_contours)):
            self.status[_contours[x].spatialindex] = 100
        self.status[0] = self.status[6]
        self.status[1] = self.status[6]
        self.status[2] = self.status[7]
        self.status[3] = self.status[8]
        self.goal_frame = self.constructInteractiveGoalFrame(self.status)

    def playTowardLatest(self):
        """Always pushing every channel toward where it needs to go
           Loop over active channels, seeing which way we need to change the intensity
        """
        _actual = self.prev_frame
        for index in range(0, 544):
            _thiscurr = self.prev_frame[index]
            _thisdesired = self.goal_frame[index]
            if _thiscurr == _thisdesired:
                continue
            new = 0
            if _thiscurr > _thisdesired:
                if _thiscurr - self.settings.decay < _thisdesired:
                    new = _thisdesired
                else:
                    new = _thiscurr - self.settings.decay
            if _thiscurr < _thisdesired:
                if _thiscurr + self.settings.attack > _thisdesired:
                    new = _thisdesired
                else:
                    new = _thiscurr + self.settings.attack
            _actual[index] = new

        uni1channels = _actual[:368]
        uni1channels = uni1channels + self.backfills
        for x in range(1, len(uni1channels), 1):
            self.setchannelOnOne(x, uni1channels[x-1])

        uni2channels = _actual[368:]
        uni2channels.append(135)
        for y in range(1, len(uni2channels), 1):
            self.setchannelOnTwo(y, uni2channels[y-1])

        self.prev_frame = _actual
        self.render(self.dmxDataOne, self.dmxDataTwo)
        time.sleep(0.002)
