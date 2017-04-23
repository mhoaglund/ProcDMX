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
                self.dmxData.append([chr(0)]* _universe.usingchannels) #this doesn't make sense anymore
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
        self.blanklight = [chr(0)]*_playersettings.channelsperlight

        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        #self.prev_frame = [0]*self.channelsinuse
        self.mod_frame = [0]*self.channelsinuse
        self.allindices = [x for x in range(0, self.channelsinuse)]

        self.SHAPE = [0,0]
        self.blackout()
        self.render()

    def setchannel(self, chan, _intensity, universe=0):
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
        self.dmxData[universe][chan] = chr(intensity)
        #self.dmxData[chan] = chr(intensity)

    def blackout(self, universe=0):
        """Zero out intensity on all channels"""
        print 'blacking out'
        for i in xrange(1, 512, 1):
            self.dmxData[universe][i] = chr(0)
            #self.dmxData[i] = chr(0)

    def render(self, universe=0):
        """Send off our DMX intensities to the hardware"""
        sdata = ''.join(self.dmxData[universe])
        self.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

    def renderAll(self, _channels):
        """Given a total set of channels, intelligently break it up and get it to the proper devices"""


    def contructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _dirty = [0]*544
        _temp = self.colors.base*136
        for cdc in _cdcs:
            _fixturehue = self.colors.speeds[cdc.spd]
            for ch in range (1,4): #should this be 0,3? only one way to find out.
                _temp[cdc.spatialindex + ch] = _fixturehue[ch]
                _dirty[cdc.spatialindex + ch] = 1
        return _temp


    def run(self):
        while self.cont:
            if not self.jobqueue.empty():
                currentjob = self.jobqueue.get()
                if currentjob.job == "TERM":
                    self.cont = False
                if currentjob.job == "SET_SHAPE":
                    logging.info('Setting video shape %s', currentjob.payload)
                    self.SHAPE[0] = currentjob.payload[1]
                    self.SHAPE[1] = currentjob.payload[0]
                    print self.SHAPE
                if currentjob.job == "NIGHT":
                    logging.info('Going into Night Mode')
                    self.isnightmode = True
                if currentjob.job == "MORNING":
                    logging.info('Activating for the day')
                    self.isnightmode = False
            if not self.dataqueue.empty():
                self.playlatestcontours(self.dataqueue.get())
        self.render()

    def stop(self):
        print 'Terminating...'
        self.cont = False
        self.render()
        super(ImmediatePlayer, self).terminate()

    def playnightroutine(self):
        """Set it to the night color"""
        for channel in range(0, self.channelsinuse):
            self.setchannel(channel+1, self.nightframe[channel])
        self.render()
        time.sleep(2)

    def warmChannels(self, _channelrange):
        i = 0
        for channel in range(_channelrange[0], _channelrange[1]):
            self.mod_frame[channel] = self.colors.increment[i]
            i +=1
    def compileLatestContours(self, _contours):
        """When a set of contours comes in, build a goal frame out of it."""

    def playTowardLatest(self):
        """Always pushing every channel toward where it needs to go"""
        """Loop over active channels, seeing which way we need to change the intensity"""
        _actual = self.prev_frame
        for index in range(1,544):
            _thiscurr = self.prev_frame[index]
            _thisdesired = self.goal_frame[index]
            if _thiscurr == _thisdesired:
                continue
            if _thiscurr > _thisdesired:
                if _thiscurr -4 < _thisdesired:
                    _actual[index] = _thisdesired
                else:
                    _actual[index] = _thiscurr - 4
            if _thiscurr < _thisdesired:
                if _thiscurr + 4 > _thisdesired:
                    _actual[index] = _thisdesired
                else:
                    _actual[index] = _thisdesired + 4
        self.prev_frame = _actual
        renderAll(_actual)

    def playlatestcontours(self, _contours):
        """When we get a set of contours from a frame, process here
           Data comes in the form of a collection of CalcdContours, with centers, spatial indices for fixtures,
           and aspect ratios.
        """
        goal = self.contructInteractiveGoalFrame(_contours)
        self.mod_frame = self.colors.decrement*self.lightsinuse
        self.reconcilemodifiers()

    def reconcilemodifiers(self):
        """Reconcile the current state of lights with the desired state, expressed by deltas"""
        newframe = map(self.recchannel, self.prev_frame, self.mod_frame, self.allindices)
        self.prev_frame = newframe
        for channel in range(0, len(newframe)):
            self.setchannel(channel+1, newframe[channel])
        self.render()

    def recchannel(self, old, mod, i):
        """Reconcile channel value with modifier, soft-clamping values modally """
        hiref = self.peakframe[i]
        loref = self.baseframe[i]

        temp = old + mod
        if temp > hiref:
            temp = hiref
        if temp < loref:
            diff = loref-temp
            if diff > 4:
                temp += 4
            else:
                temp = loref
        return temp
