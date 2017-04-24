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
        self.dmxData = []
        self.cont = True
        self.universes = _playersettings.universes

        for _universe in self.universes:
            try:
                _universe.serial = serial.Serial(_universe.serialport, baudrate=57600)
                _universe.serial.write( DMXOPEN+DMXINIT1+DMXCLOSE)
                _universe.serial.write( DMXOPEN+DMXINIT2+DMXCLOSE)
            except:
                print "Error: could not open Serial Port: ", _universe.serialport
                sys.exit(0)

        self.dataqueue = _playersettings.dataqueue
        self.jobqueue = _playersettings.jobqueue
        self.colors = _colorsettings
        self.channelsinuse = _playersettings.lights * _playersettings.channelsperlight
        self.lightsinuse = _playersettings.lights

        self.baseframe = self.colors.base*_playersettings.lights
        self.dimframe = self.colors.dimmed*_playersettings.lights
        self.peakframe = self.colors.peak*_playersettings.lights
        self.busyframe = self.colors.busy*_playersettings.lights
        self.nightframe = self.colors.night*_playersettings.lights

        self.increment = self.colors.increment
        self.decrement = self.colors.decrement

        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        self.backfills = self.colors.backfill * 4
        self.blackout()
        self.playTowardLatest()

    def cleanValue(self, value):
        """Clean byte values for dmx"""
        intensity = int(value)
        if intensity > 255:
            intensity = 255
        if intensity < 0:
            intensity = 0
        return intensity

    def blackout(self, universe=0):
        """Zero out intensity on all channels"""
        print 'blacking out'
        for uni in self.universes:
            uni.myDMXdata = [0]*513
        self.render()

    def applyAll(self, _channels):
        """Given a total set of channels, break it up and get it to the proper devices"""
        #Break off the first chunk of the interactive channels for the first universe. Should 368.
        uni1channels = _channels[:self.universes[0].interactivechannels]
        uni1channels = uni1channels + self.backfills
        uni1remainder = 513 - len(uni1channels)
        uni1channels = uni1channels + ([0]*uni1remainder)
        self.universes[0].myDMXdata = uni1channels

        #Break off the second chunk of the interactive channels for the second universe. Should 176.
        uni2channels = _channels[:self.universes[0].interactivechannels:]
        uni2remainder = 513 - len(uni2channels)
        uni2channels = uni2channels + ([0]*uni2remainder)
        self.universes[1].myDMXdata = uni2channels
        self.render()

    def render(self):
        for uni in self.universes:
            prep = [chr(x) for x in uni.myDMXdata] #this is the ONLY cast to char we're doing!
            sdata = ''.join(prep)
            uni.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

    def constructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _dirty = [0]*544
        _temp = self.colors.base*136
        for cdc in _cdcs:
            _fixturehue = self.colors.speeds[cdc.spd]
            for ch in range (1, 4): #should this be 0,3? only one way to find out.
                _temp[cdc.spatialindex + ch] = _fixturehue[ch]
                _dirty[cdc.spatialindex + ch] = 1
        logging.info('Setting a goal frame: %s', _temp)
        return _temp


    def run(self):
        while self.cont:
            if not self.jobqueue.empty():
                currentjob = self.jobqueue.get()
                if currentjob.job == "TERM":
                    self.cont = False
                if currentjob.job == "MORNING":
                    logging.info('Activating for the day')
                    self.isnightmode = False
            if not self.dataqueue.empty():
                self.compileLatestContours(self.dataqueue.get())
            self.playTowardLatest()

    def stop(self):
        print 'Terminating...'
        self.cont = False
        super(ImmediatePlayer, self).terminate()

    def compileLatestContours(self, _contours):
        """When a set of contours comes in, build a goal frame out of it."""
        print 'compiling goal frame'
        self.goal_frame = self.constructInteractiveGoalFrame(_contours)

    def playTowardLatest(self):
        """Always pushing every channel toward where it needs to go
           Loop over active channels, seeing which way we need to change the intensity
        """
        _actual = self.prev_frame
        for index in range(1, 544):
            _thiscurr = self.prev_frame[index]
            _thisdesired = self.goal_frame[index]
            if _thiscurr == _thisdesired:
                continue
            new = 0
            if _thiscurr > _thisdesired:
                if _thiscurr -4 < _thisdesired:
                    new = _thisdesired
                else:
                    new = _thiscurr - 4
            if _thiscurr < _thisdesired:
                if _thiscurr + 4 > _thisdesired:
                    new = _thisdesired
                else:
                    new = _thisdesired + 4

            _actual[index] = self.cleanValue(new)
        self.prev_frame = _actual
        self.applyAll(_actual)
        time.sleep(0.02)
