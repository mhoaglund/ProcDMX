import sys
import serial
import time
import logging
import math
import uuid
import random
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
        try:
            self.serialOne = serial.Serial('/dev/ttyUSB0', baudrate=57600)
            self.serialTwo = serial.Serial('/dev/ttyUSB1', baudrate=57600)
        except:
            print "Error: could not open Serial port"
            logging.info("An issue has occurred with one of the Serial Ports. Running in dummy mode with no serial output.")
            self.isHardwareConnected = False
		    try:
                from DMXgui import Emulator
                from Tkinter import Tk
                self.root = Tk()
                self.gui = Emulator(self.root)
			except ImportError:
			    print "Missing GUI library..."
			    logging.info("Tkinter is missing...")
			    self.cont = False

        self.current_active_color = 0
        self.quietframes = 0
        self.maxquietframes = 140
        self.shouldUpdateColor = False
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
        self.prev_contours = []
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
        else:
            _payloadTwo.pop(0)
            _payloadTwo.append(chr(0))
            _all = _payloadOne + _payloadTwo
            _all.pop(0)
            self.gui.renderDMX(_all)
            self.root.update()

    def updateActiveColor(self):
        """If we have a period of inactivity, switch the activation color."""
        print "cycling active color"
        if self.current_active_color == len(self.colors.activations)-1:
            self.current_active_color = 0
        else:
            self.current_active_color += 1
        self.shouldUpdateColor = False

    def constructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _temp = self.colors.base*136
        _fixturehue = self.colors.activations[self.current_active_color]
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

    #TODO handle the case of contours that land in the same index but have different colors
    #kyle's suggestion was the highest-first style where we additively filter the two colors together.
    def constructVariableInteractiveGoalFrame(self, _status, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        _temp = self.colors.base*136
        _fixturehue = self.colors.activations[self.current_active_color]
        _startchannel = 0
        #for channelheat in range(0,136): #cool all the channels
        #    self.heats[channelheat] -= 1
        for x in range(0, 136):
            _color = _fixturehue
            for x in _cdcs:
                if x.color != _fixturehue and x.color != [0, 0, 0, 0,]:
                    #TODO blend colors here
                    _color = x.color
                    break

            if _status[x] > 1:
                if x > 0:
                    _startchannel = x * 4
                if _startchannel > 4: #conditionally brighten the previous fixture
                    for ch in range(-4, 0):
                        _temp[_startchannel + ch] = _color[ch+4]
                for ch in range(0, 4):
                    _temp[_startchannel + ch] = _color[ch]
                if _startchannel + 7 < 544:  #conditionally brighten the next fixture
                    for ch in range(4, 8):
                        _temp[_startchannel + ch] = _color[ch-4]
        return _temp


    def run(self):
        while self.cont:
            if not self.dataqueue.empty():
                Contours = self.dataqueue.get()
                self.compileLatestContours(Contours)
                if len(Contours) < 2:
                    if self.quietframes > self.maxquietframes:
                        if self.shouldUpdateColor:
                            self.updateActiveColor()
                        self.quietframes = 0
                    else:
                        self.quietframes += 1
                else:
                    self.quietframes = 0
                    self.shouldUpdateColor = True
            self.playTowardLatest()

    #TODO figure out if this spacing_limit is reasonable.
    #TODO figure out how to do multiple passes of this recursively back into the past
    cont_limit = 2
    spacing_limit = 150
    def findContinuity(self, contours):
        """
            Given a set of new contours, compare to previous set and
            try to identify nearest neighbors.
        """
        ordered_contours = sorted(contours, key=lambda cntr: cntr.spatialindex)
        if len(self.prev_contours) == 0:
            self.prev_contours = ordered_contours
            return
        else:
            indices = len(ordered_contours)
            for cnt in range(0, indices):
                cnt.color = self.colors.activations[self.current_active_color]
                _associated = False
                _with = None
                _thisnew = ordered_contours[cnt]
                if cnt -1 > 0:
                    _prevold = self.prev_contours[cnt -1]
                    if abs(_prevold.pos[1] - _thisnew.pos[1]) < spacing_limit and abs(_prevold.spatialindex - _thisnew.spatialindex) < cont_limit:
                        _associated = True
                        _with = _prevold
                        #a contour moved from the previous index to the current index
                if cnt + 1 < indices:
                     _nextold = self.prev_contours[cnt + 1]
                    if abs(_nextold.pos[1] - _thisnew.pos[1]) < spacing_limit and abs(_nextold.spatialindex - _thisnew.spatialindex) < cont_limit:
                        _associated = True
                        _with = _nextold
                        #a contour moved from the previous index to the current index
                #if this contour has a neighbor, get the neighbor's color.
                if _associated and _with:
                    _thisnew.color = _with.color
                else:
                    _thisnew.color = self.colors.activations[randint(0, len(self.colors.activations))]

        return ordered_contours

    def stop(self):
        print 'Terminating...'
        self.cont = False
        super(ImmediatePlayer, self).terminate()

    def tweakNoisyChannels(self):
        """Some channels get feedback. We can just lock them at 0 for a moment after they drop to prevent this."""
        return 0

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
        #self.goal_frame = self.constructInteractiveGoalFrame(self.status)
        self.goal_frame = self.constructVariableInteractiveGoalFrame(findContinuity(_contours), self.status)

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
        time.sleep(0.01) #100fps is probably good
