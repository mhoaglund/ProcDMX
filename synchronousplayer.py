import sys
import serial
import time
import smbus
import logging
from multiprocessing import Process, Queue
from random import randint
from operator import add

DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY = chr(6)+chr(1)+chr(2)
DMXINIT1 = chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2 = chr(10)+chr(02)+chr(0)+chr(0)+chr(0)

#Sensor nodes register hits and this pushes our lights from default to threshold,
#then they cool back down over time.


class SyncPlayer(Process):
    """A Process which Handles access to iic and renders readings to DMX.
        Args:
            Player Settings (playerutils.PlayerSettings),
            Color Settings (playerutils.ColorSettings)
            Job Queue (multiprocessing Queue)
    """
    def __init__(self, _playersettings, _colorsettings, _queue):
        super(SyncPlayer, self).__init__()
        print 'starting worker'
        try:
            self.serial = serial.Serial(_playersettings.serialPort, baudrate=57600)
        except:
            print "Error: could not open Serial Port"
            sys.exit(0)
        self.cont = True
        self.myqueue = _queue
        self.colors = _colorsettings
        self.internaddr = _playersettings.internaddr
        self.delay = _playersettings.delay
        self.gates = _playersettings.edgegates
        self.arraysize = _playersettings.arraysize
        self.rendermap = _playersettings.rendermap
        self.bus = smbus.SMBus(1)
        self.dmxData = [chr(0)]* 513
        self.lastreadings = [1]* _playersettings.arraysize
        self.busyframes = 0
        self.maxbusyframes = 100
        self.isbusy = False
        self.isnightmode = False
        self.flipreadings = True
        self.edgestatus = False
        self.edgeintervalmax = 100
        self.edgeinterval = 0
        self.busylimit = _playersettings.arraysize -4
        self.channelheat = [0]*_playersettings.arraysize
        if _playersettings.decay < 5:
            self.decayframes = 5
        else:
            self.decayframes = _playersettings.decay

        self.channelsinuse = _playersettings.lights * _playersettings.channelsperlight

        self.baseframe = self.colors.base*_playersettings.lights
        self.dimframe = self.colors.dimmed*_playersettings.lights
        self.peakframe = self.colors.peak*_playersettings.lights
        self.busyframe = self.colors.busy*_playersettings.lights
        self.nightframe = self.colors.night*_playersettings.lights

        self.increment = self.colors.increment
        self.decrement = self.colors.decrement
        self.altdecrement = self.colors.altdecrement

        self.prev_frame = [0]*self.channelsinuse
        self.mod_frame = [0]*self.channelsinuse
        self.allindices = [x for x in range(0, self.channelsinuse)]

        self.blackout()
        self.render()

    def setChannel(self, chan, _intensity):
        """Set intensity on channel"""
        intensity = int(_intensity)
        if chan > 512: chan = 512
        if chan < 0: chan = 0
        if intensity > 255: intensity = 255
        if intensity < 0: intensity = 0
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

    def groom(self, _list):
        """Given an array of readings, fill in obvious gaps and spot edges"""
        listsz = len(_list)
        islands = []
        pits = []
        holes = []
        edges = []
        contigs = []
        curr = []
        currpits = []
        #find contiguous regions of positive values and log them by index
        for value in range(0, listsz):
            if _list[value] == 0:
                if len(currpits) > 0:
                    currpits.append(value)
                if len(currpits) == 0:
                    currpits = []
                    currpits.append(value)
                if len(curr) == 0:
                    continue
                if len(curr) > 0:
                    if len(curr) > 1:
                        contigs.append(curr)
                        edgepair = []
                        if curr[0] > 0:
                            edgepair.append(curr[0]-1)
                        if curr[len(curr)-1] < listsz:
                            edgepair.append(curr[len(curr)-1]+1)
                        if len(edgepair) > 1:
                            for singleedge in edgepair:
                                edges.append(singleedge)
                    else:
                        islands.append(curr)
                    curr = []

            if _list[value] > 0:
                if len(curr) > 0:
                    curr.append(value)
                if len(curr) == 0:
                    curr.append(value)

                if len(currpits) > 0:
                    if len(currpits) > 1:
                        pits.append(currpits)
                    else:
                        holes.append(currpits[0])
                    currpits = []

        if len(currpits) > 0:
            if len(currpits) > 1:
                pits.append(currpits)
            else:
                holes.append(currpits)
            currpits = []

        if len(curr) > 0:
            if len(curr) > 1:
                contigs.append(curr)
            else:
                islands.append(curr)
            curr = []

        for hole in holes:
            _list[hole] = 1

        for edge in edges:
            _list[edge] = -1

        return _list

    def run(self):
        while self.cont:
            if not self.myqueue.empty():
                currentjob = self.myqueue.get()
                if currentjob == "NIGHT":
                    logging.info('Going into Night Mode')
                    self.isnightmode = True
                if currentjob == "MORNING":
                    logging.info('Activating for the day')
                    self.isnightmode = False
            if not self.isnightmode:
                self.playlatestreadings()
            if self.isnightmode:
                self.playnightroutine()
        self.blackout()
        self.render()

    def stop(self):
        print 'Stopping...'
        self.cont = False

    def terminate(self):
        print 'Terminating...'
        self.cont = False
        self.blackout()
        self.render()

    def playnightroutine(self):
        """Set it to the night color"""
        for channel in range(0, self.channelsinuse):
            self.setChannel(channel+1, self.nightframe[channel])
        self.render()
        time.sleep(self.delay)

    def playlatestreadings(self):
        """Main loop."""
        try:
            rawinput = self.bus.read_i2c_block_data(self.internaddr, 0, self.arraysize)
            self.lastreadings = rawinput
            rawinput[16] = 0 #muting a busted channel
        except IOError as err:
            logging.info('i2c encountered a problem. %s', err)
            rawinput = self.lastreadings

        if sum(rawinput) > self.busylimit:
            self.busyframes += 1
        else:
            self.busyframes = 0
            self.isbusy = False
        #if we are super busy, just lock at 1 on all channels
        if self.busyframes > self.maxbusyframes:
            self.isbusy = True
            rawinput = [1] * self.arraysize

        if self.flipreadings is True:
            rawinput.reverse()

        if self.isbusy is False:
            #If we have an edge hit, open the gates.
            if len(self.gates) > 0:
                for edgegate in self.gates:
                    if rawinput[edgegate] > 0:
                        self.edgestatus = True
                        self.edgeinterval = 0
                        continue

            if self.edgeinterval < self.edgeintervalmax:
                #If edge gates are open but there's no activity, creep back toward gate closure
                if sum(rawinput) == 0:
                    self.edgeinterval += 1
                else:
                    if self.edgeinterval > 0:
                        self.edgeinterval -= 1
            else:
                self.edgestatus = False
                rawinput = [0] * self.arraysize

            rawinput = self.groom(rawinput)

        if self.cont != True:
            self.blackout()
            self.render()
            return
        dimchannels = []
        for i in range(1, len(rawinput)):
            mychannels = self.rendermap[i]
            foundchannels = len(mychannels)
            foundlights = foundchannels/4
            mymodifiers = [0]*foundchannels
            shoulddim = False
            if rawinput[i-1] == 1:
                self.channelheat[i-1] = self.decayframes
            myreading = self.channelheat[i-1]
            if myreading > 0:
                self.channelheat[i-1] -= 1

            if myreading > 0:
                mymodifiers = self.increment*foundlights
            if myreading == 0:
                mymodifiers = self.decrement*foundlights
            if rawinput[i-1] < 0:
                mymodifiers = self.altdecrement*foundlights
                shoulddim = True
            #TODO pass an array of 'modes' into the reconciliation code so we can dynamically clamp

            chval = 0
            for channel in mychannels:
                addr = channel
                val = mymodifiers[chval]
                self.mod_frame[addr] = val
                if shoulddim is True:
                    dimchannels.append(addr)
                chval += 1
        self.reconcilemodifiers(dimchannels)

    def reconcilemodifiers(self, _dim):
        """Reconcile the current state of lights with the desired state, expressed by deltas"""
        newframe = map(self.recchannel, self.prev_frame, self.mod_frame, self.allindices, _dim)
        self.prev_frame = newframe
        for channel in range(0, len(newframe)):
            self.setChannel(channel+1, newframe[channel])
        self.render()
        time.sleep(self.delay)

    def recchannel(self, old, mod, i, _dim):
        """Reconcile channel value with modifier, soft-clamping values modally """
        hiref = self.peakframe[i]
        loref = self.baseframe[i]
        if i in _dim:
            hiref = self.peakframe[i]
            loref = self.dimframe[i]

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
