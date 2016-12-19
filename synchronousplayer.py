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

CHAN_PER_FIXTURE = 4
LIGHTS_IN_USE = 30
CHANNELS_IN_USE = LIGHTS_IN_USE*CHAN_PER_FIXTURE
EMPTY_FRAME = [0]*CHANNELS_IN_USE
MOD_FRAME = [0]*CHANNELS_IN_USE
PREV_FRAME = [0]*CHANNELS_IN_USE
INDICES = [x for x in range(0, CHANNELS_IN_USE)]

#Sensor nodes register hits and this pushes our lights from default to threshold,
#then they cool back down over time.
DEFAULT_COLOR = [100, 0, 180, 0]
THRESHOLD_COLOR = [125, 50, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [4, 2, 6, 2] #the core aesthetic
COOLDOWN = [-2, -1, -2, -2]

BASE_FRAME = DEFAULT_COLOR*LIGHTS_IN_USE
MAX_FRAME = THRESHOLD_COLOR*LIGHTS_IN_USE
BUSY_FRAME = BUSY_THRESHOLD_COLOR*LIGHTS_IN_USE
NIGHT_FRAME = NIGHT_IDLE_COLOR*LIGHTS_IN_USE

RENDERMAP = {
    1: [x+1 for x in range(CHAN_PER_FIXTURE * 1)],
    2: [x+1 for x in range(CHAN_PER_FIXTURE * 1, CHAN_PER_FIXTURE * 2)],
    3: [x+1 for x in range(CHAN_PER_FIXTURE * 2, CHAN_PER_FIXTURE * 4)],
    4: [x+1 for x in range(CHAN_PER_FIXTURE * 4, CHAN_PER_FIXTURE * 6)],
    5: [x+1 for x in range(CHAN_PER_FIXTURE * 6, CHAN_PER_FIXTURE * 8)],
    6: [x+1 for x in range(CHAN_PER_FIXTURE * 8, CHAN_PER_FIXTURE * 10)],
    7: [x+1 for x in range(CHAN_PER_FIXTURE * 10, CHAN_PER_FIXTURE * 12)],
    8: [x+1 for x in range(CHAN_PER_FIXTURE * 12, CHAN_PER_FIXTURE * 14)],
    9: [x+1 for x in range(CHAN_PER_FIXTURE * 14, CHAN_PER_FIXTURE * 16)],
    10: [x+1 for x in range(CHAN_PER_FIXTURE * 16, CHAN_PER_FIXTURE * 18)],
    11: [x+1 for x in range(CHAN_PER_FIXTURE * 18, CHAN_PER_FIXTURE * 20)],
    12: [x+1 for x in range(CHAN_PER_FIXTURE * 20, CHAN_PER_FIXTURE * 22)],
    13: [x+1 for x in range(CHAN_PER_FIXTURE * 22, CHAN_PER_FIXTURE * 24)],
    14: [x+1 for x in range(CHAN_PER_FIXTURE * 24, CHAN_PER_FIXTURE * 26)],
    15: [x+1 for x in range(CHAN_PER_FIXTURE * 26, CHAN_PER_FIXTURE * 28)],
    16: [x+1 for x in range(CHAN_PER_FIXTURE * 28, CHAN_PER_FIXTURE * 30)],
    17: [x+1 for x in range(CHAN_PER_FIXTURE * 30, CHAN_PER_FIXTURE * 31)],
    18: [x+1 for x in range(CHAN_PER_FIXTURE * 31, CHAN_PER_FIXTURE * 32)]
}

class SyncPlayer(Process):
    """Handles access to iic and rendering of readings"""
    def __init__(self, _serialPort, _queue, _delay, _internaddr, _arraysize, _decay):
        super(SyncPlayer, self).__init__()
        print 'starting worker'
        try:
            self.serial = serial.Serial(_serialPort, baudrate=57600)
        except:
            print "Error: could not open Serial Port"
            sys.exit(0)
        self.cont = True
        self.myqueue = _queue
        self.internaddr = _internaddr
        self.delay = _delay
        self.arraysize = _arraysize
        self.bus = smbus.SMBus(1)
        self.dmxData = [chr(0)]*513
        self.lastreadings = [1]*_arraysize
        self.busyframes = 0
        self.maxbusyframes = 100
        self.isbusy = False
        self.isnightmode = False
        self.flipreadings = False
        self.edgestatus = False
        self.edgeintervalmax = 100
        self.edgeinterval = 0
        self.busylimit = _arraysize -4
        self.channelheat = [0]*_arraysize
        self.decayframes = _decay
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
        #TODO ease into the night color instead of just popping over
        for channel in range(0, CHANNELS_IN_USE):
            self.setChannel(channel+1, NIGHT_FRAME[channel])
        self.render()
        time.sleep(self.delay)


    def playlatestreadings(self):
        """Main loop."""
        try:
            allreadings = self.bus.read_i2c_block_data(self.internaddr, 0, self.arraysize)
            self.lastreadings = allreadings
        except IOError as err:
            logging.info('i2c encountered a problem. %s', err)
            allreadings = self.lastreadings

        if sum(allreadings) > self.busylimit:
            self.busyframes += 1
        else:
            self.busyframes = 0
            self.isbusy = False
        #if we are super busy, just lock at 1 on all channels
        if self.busyframes > self.maxbusyframes:
            self.isbusy = True
            allreadings = [1] * self.arraysize

        if self.flipreadings is True:
            allreadings.reverse()

        if self.isbusy is False:
            #If we have an edge hit, open the gates.
            if (
                    allreadings[self.arraysize-1] is 1 or
                    allreadings[self.arraysize-2] is 1 or
                    allreadings[0] is 1 or
                    allreadings[1] is 1
                ):
                self.edgestatus = True
                self.edgeinterval = 0

            if self.edgeinterval < self.edgeintervalmax:
                #If edge gates are open but there's no activity, creep back toward gate closure
                if sum(allreadings) == 0:
                    self.edgeinterval += 1
                else:
                    if self.edgeinterval > 0:
                        self.edgeinterval -= 1
            else:
                self.edgestatus = False
                allreadings = [0] * self.arraysize

        if self.decayframes > 0:
            self.channelheat = [val * self.decayframes for val in allreadings] #set the decay

        if self.cont != True:
            self.blackout()
            self.render()
            return
        for i in range(1, len(allreadings)):
            mychannels = RENDERMAP[i]
            foundchannels = len(mychannels)
            foundlights = foundchannels/4
            mymodifiers = [0]*foundchannels
            if self.decayframes == 0:
                myreading = allreadings[i-1]
            else:
                myreading = self.channelheat[i-1]
                if myreading is not 0:
                    self.channelheat[i-1] -= 1

            if myreading > 0:
                mymodifiers = INCREMENT*foundlights
            else:
                mymodifiers = COOLDOWN*foundlights

            chval = 0
            for channel in mychannels:
                addr = channel
                val = mymodifiers[chval]
                MOD_FRAME[addr] = val
                chval += 1
        self.reconcilemodifiers()

    def reconcilemodifiers(self):
        """Reconcile the current state of lights with the desired state, expressed by deltas"""
        global PREV_FRAME

        newframe = map(self.recchannel, PREV_FRAME, MOD_FRAME, INDICES) #sweet
        PREV_FRAME = newframe
        for channel in range(0, len(newframe)):
            self.setChannel(channel+1, newframe[channel])
        self.render()
        time.sleep(self.delay)

    def recchannel(self, old, mod, i):
        """Reconcile channel value with modifier, taking max and mins into account """
        temp = old + mod
        if self.isbusy:
            hiref = BUSY_FRAME[i]
            loref = BASE_FRAME[i]
        else:
            hiref = MAX_FRAME[i]
            loref = BASE_FRAME[i]
        if temp > hiref:
            temp = hiref
        if temp < loref:
            temp = loref
        return temp
