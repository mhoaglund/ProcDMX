#TODO: is the name right? it matches the settings object for this but...

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
        try:
            self.serial = serial.Serial(_playersettings.serialport, baudrate=57600)
        except:
            print "Error: could not open Serial Port"
            sys.exit(0)
        self.cont = True
        self.dataqueue = _playersettings.dataqueue
        self.jobqueue = _playersettings.jobqueue
        self.colors = _colorsettings
        self.dmxData = [chr(0)]* 513
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

        self.prev_frame = [0]*self.channelsinuse
        self.mod_frame = [0]*self.channelsinuse
        self.allindices = [x for x in range(0, self.channelsinuse)]

        self.SHAPE = [0,0]
        self.blackout()
        self.render()

    def setchannel(self, chan, _intensity):
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
        self.dmxData[chan] = chr(intensity)

    def blackout(self):
        """Zero out intensity on all channels"""
        print 'blacking out'
        for i in xrange(1, 512, 1):
            self.dmxData[i] = chr(0)

    def render(self):
        """Send off our DMX intensities to the hardware"""
        sdata = ''.join(self.dmxData)
        self.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

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
        self.blackout()
        self.render()

    def terminate(self):
        print 'Terminating...'
        self.cont = False
        self.blackout()
        self.render()

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

    def playlatestcontours(self, _contours):
        """When we get a set of contours from a frame, process here
           Data comes in the form of a collection of points which mark the centers of
           Contour areas. That will need to change later.
        """
        #print _contours
        if len(self.SHAPE) < 2:
            self.blackout()
            return
        self.mod_frame = self.colors.decrement*self.lightsinuse
        if len(_contours) > 0:
            for c in _contours:
                c_ratio = (float(c[0])/self.SHAPE[0], float(c[1])/self.SHAPE[1])
                target = (0, 0)
                if c_ratio[0] < 0.25:
                    target = (0, 4)
                elif c_ratio[0] > 0.25 and c_ratio[0] < 0.5:
                    target = (4, 8)
                elif c_ratio[0] > 0.5 and c_ratio[0] < 0.75:
                    target = (8, 12)
                elif c_ratio[0] > 0.75:
                    target = (12, 16)
                self.warmChannels(target)
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
