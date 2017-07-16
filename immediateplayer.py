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

        self.dye_range = 6
        self.cont_limit = 12
        self.spacing_limit = 250
        w, h = 4, 136
        self.color_memory = [[0 for x in range(w)] for y in range(h)]
        for arr in self.color_memory:
            arr[0] = self.colors.base[0]
            arr[1] = self.colors.base[1]
            arr[2] = self.colors.base[2]
            arr[3] = self.colors.base[3]
        #Prev Frame and Goal Frame are containers for data pertaining to ALL interactive channels.
        #They get split up for rendering and don't have anything to do with DMX packets.
        self.prev_contours = []
        self.status = [0]*136
        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        self.sustain = _playersettings.sustain
        self.backfills = self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]
        self.updateActiveColor()
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
        #clearing plastic color memory
        for arr in self.color_memory:
            arr[0] = self.colors.base[0]
            arr[1] = self.colors.base[1]
            arr[2] = self.colors.base[2]
            arr[3] = self.colors.base[3]
        self.shouldUpdateColor = False

    def constructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _temp = self.colors.base*136
        _fixturehue = self.colors.activations[self.current_active_color]
        _startchannel = 0
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

    def constructColorMemoryGoalFrame(self, _status):
        """
            Using color memory, construct a goal frame.
            :param _status: array with cooldown state of each fixture
        """
        _temp = self.colors.base*136
        for x in range(0, 136):
            _color = self.color_memory[x]
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

    def constructVariableInteractiveGoalFrame(self, _status, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        _temp = self.colors.base*136
        _startchannel = 0

        #For each fixture...
        for x in range(0, 136):
            _color = self.color_memory[x]
            contours_at_this_fixture = [cnt for cnt in _cdcs if cnt['spatialindex'] == x]
            if len(contours_at_this_fixture) > 0:
                _tempcolor = [0, 0, 0, 0]
                for c in contours_at_this_fixture:
                    for channel in range(0, len(c['color'])):
                        if c['color'][channel] > _tempcolor[channel]:
                            _tempcolor[channel] = c['color'][channel]
                _color = _tempcolor
                self.color_memory[x][0] = _tempcolor[0]
                self.color_memory[x][1] = _tempcolor[1]
                self.color_memory[x][2] = _tempcolor[2]
                self.color_memory[x][3] = _tempcolor[3]

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

    def setColorMemory(self, _status, _cdcs, _fresh):
        """
            Given status and contours, dye sections of cooled-down color memory
            where new contours have appeared. Contours that show up in already-dyed
            regions should pick up the dye.
            When new sections get dyed, check for running into other dyed regions and
            mix accordingly.
            :param _status: array with cooldown state of each fixture
            :param _cdcs: array of contours from opencv procs
        """
        for x in range(0, 136):
            contours_at_this_fixture = [cnt for cnt in _cdcs if cnt.spatialindex == x]
            if len(contours_at_this_fixture) < 1:
                return
            if x in _fresh:
                print "dying blank area..."
                _color = self.colors.activations[randint(0, (len(self.colors.activations)-1))]
                self.dye_memory(x, _color)
            elif _status[x] > 1:
                #Pull color from color memory and dye it back.
                _color = self.color_memory[x]
                self.dye_memory(x, _color)

    def dye_memory(self, center, color):
        for cm in range(center - self.dye_range, center + self.dye_range):
            if cm >= 0 and cm <= len(self.color_memory):
                self.color_memory[cm] = color

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

    def stop(self):
        print 'Terminating...'
        self.cont = False
        super(ImmediatePlayer, self).terminate()

    def compileLatestContours(self, _contours):
        """When a set of contours comes in, build a goal frame out of it."""
        newly_active = []
        for y in range(0, 136):
            if self.status[y] > 0:
                self.status[y] -= 1
        for x in range(0, len(_contours)):
            if self.status[_contours[x].spatialindex] < 1:
                newly_active.append(_contours[x].spatialindex)
            self.status[_contours[x].spatialindex] = 100
        
        #TODO figure out this bullshit. These channels just never get tripped
        self.status[0] = self.status[6]
        self.status[1] = self.status[6]
        self.status[2] = self.status[7]
        self.status[3] = self.status[8]
        print len(newly_active)
        self.setColorMemory(self.status, _contours, newly_active)
        self.goal_frame = self.constructColorMemoryGoalFrame(self.status)

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
        #A good reminder here- the player loop takes more than zero time to run!
        #So this sleep isn't A. a good design choice or B. indicative of framerate!
