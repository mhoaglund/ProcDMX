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

        self.dye_range = 3
        w, h = 4, 136
        self.color_memory = [[0 for x in range(w)] for y in range(h)]
        self.palette = []
        #Prev Frame and Goal Frame are containers for data pertaining to ALL interactive channels.
        #They get split up for rendering and don't have anything to do with DMX packets.
        self.status = [0]*136
        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        self.sustain = _playersettings.sustain
        self.backfills = self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]
        self.wipeColorMemory()
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

    #when we wipe this, it isn't having the desired effect.
    #we should just return to default behavior.
    #after a couple of wipes we end up with wierd pastel colors, like we're add-mixing base or something.
    def wipeColorMemory(self):
        """If we have a period of inactivity, wipe color memory."""
        #clearing plastic color memory
        print "wiping color memory..."
        for x in range(1, len(self.color_memory)):
            self.color_memory[x] = self.colors.base
        self.shouldUpdateColor = False
        self.palette = []

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
            if x in _cdcs:
                _color = self.color_memory[x]
                if x in _fresh:
                    if _color == self.colors.base:
                        _color = self.colors.activations[randint(0, (len(self.colors.activations)-1))]
                        if not _color in self.palette:
                             self.palette.append(_color)
                             print "Added ", _color, " to palette"
                        #self.dye_memory(x, _color, self.dye_range)
                    # elif self.color_memory[x] in self.palette:
                    #     #Doing this only with freshly-changed channels has some limitations.
                    #     #Maybe we could also add a case for performing the same mix on channels with <50 status or something?
                    #     _color = self.add_mix(
                    #         self.color_memory[x], 
                    #         self.colors.activations[randint(0, (len(self.colors.activations)-1))]
                    #         )
                    #     if not _color in self.palette:
                    #         self.palette.append(_color)
                    #     self.dye_memory(x, _color, self.dye_range)
                elif _status[x] > 1:
                    #Pull color from color memory and dye it back.
                    _color = self.color_memory[x]
                self.conditional_dye(x, _color, self.dye_range)

    def dye_memory(self, center, color, distance):
        """
            Dye a range of cells in color memory array.
        """
        for cm in range(center - distance, center + distance):
            if cm >= 0 and cm < len(self.color_memory):
                self.color_memory[cm] = color

    def conditional_dye(self, center, color, distance):
        """
            Intelligently dye a range of color memory cells based on their contents.
        """
        _color = color
        start = center - distance if center - distance > 0 else 0
        end = center + distance if center + distance < len(self.color_memory) else len(self.color_memory)
        cells = self.color_memory[start:end]
        has_new = False
        try:
            #Encountered a new color, so add up.
            #need to figure out if this iter makes sense
            newcolor = next(c for c in cells if c != color and c in self.palette)
            _color = self.add_mix(newcolor, color)   
            has_new = True
        except StopIteration:
            #no new color, back to business
            has_new = False
            _color = color
        for cm in range(start, end):
            self.color_memory[cm] = _color

    @staticmethod
    def add_mix(old, new):
        """
            Mix two rgba colors, privilege to higher values.
        """
        mixed = [0,0,0,0]
        for x in range(0, len(old)):
            if new[x] > old[x]:
                mixed[x] = new[x]
            else:
                mixed[x] = old[x]
        return mixed

    def run(self):
        while self.cont:
            if not self.dataqueue.empty():
                Contours = self.dataqueue.get()
                self.compileLatestContours(Contours)
                if len(Contours) < 2:
                    if self.quietframes > self.maxquietframes:
                        if self.shouldUpdateColor:
                            self.wipeColorMemory()
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
        stripped_down = [cnt.spatialindex for cnt in _contours]
        self.setColorMemory(self.status, stripped_down, newly_active)
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
        #time.sleep(0.005) #100fps is probably good
        #A good reminder here- the player loop takes more than zero time to run!
        #So this sleep isn't A. a good design choice or B. indicative of framerate!
