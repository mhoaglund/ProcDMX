import sys, serial, time, smbus, logging
from multiprocessing import Process, Queue
from random import randint
from operator import add

DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY = chr(6)+chr(1)+chr(2)
DMXINIT1 = chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2 = chr(10)+chr(02)+chr(0)+chr(0)+chr(0)

LIGHTS_IN_USE = 30
CHANNELS_IN_USE = LIGHTS_IN_USE*4
EMPTY_FRAME = [0]*CHANNELS_IN_USE
MOD_FRAME = [0]*CHANNELS_IN_USE
PREV_FRAME = [0]*CHANNELS_IN_USE
INDICES = [x for x in range(0, CHANNELS_IN_USE)]

#Sensor nodes register hits and this pushes our lights from default to threshold,
#then they cool back down over time.
DEFAULT_COLOR = [35, 0, 75, 0]
THRESHOLD_COLOR = [125, 50, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 80, 255, 200]
NIGHT_IDLE_COLOR = [0, 0, 120, 255]
INCREMENT = [4, 2, 6, 2] #the core aesthetic
COOLDOWN = [-2, -1, -2, -2]
VOLATILITY = 3

BASE_FRAME = DEFAULT_COLOR*LIGHTS_IN_USE
MAX_FRAME = THRESHOLD_COLOR*LIGHTS_IN_USE
BUSY_FRAME = BUSY_THRESHOLD_COLOR*LIGHTS_IN_USE
NIGHT_FRAME = NIGHT_IDLE_COLOR*LIGHTS_IN_USE

CHANNELS_PER_SENSOR = 8 #two lights per sensor in other words, about 3 feet of distance
NARROW_BAND = 4 #if we have to alternate

RENDERMAP = {
    1: [x+1 for x in range(CHANNELS_PER_SENSOR * 1)],
    2: [x+1 for x in range(CHANNELS_PER_SENSOR * 1, CHANNELS_PER_SENSOR * 2)],
    3: [x+1 for x in range(CHANNELS_PER_SENSOR * 2, CHANNELS_PER_SENSOR * 3)],
    4: [x+1 for x in range(CHANNELS_PER_SENSOR * 3, CHANNELS_PER_SENSOR * 4)],
    5: [x+1 for x in range(CHANNELS_PER_SENSOR * 4, CHANNELS_PER_SENSOR * 5)],
    6: [x+1 for x in range(CHANNELS_PER_SENSOR * 5, CHANNELS_PER_SENSOR * 6)],
    7: [x+1 for x in range(CHANNELS_PER_SENSOR * 6, CHANNELS_PER_SENSOR * 7)],
    8: [x+1 for x in range(CHANNELS_PER_SENSOR * 7, CHANNELS_PER_SENSOR * 8)],
    9: [x+1 for x in range(CHANNELS_PER_SENSOR * 8, CHANNELS_PER_SENSOR * 9)],
    10:[x+1 for x in range(CHANNELS_PER_SENSOR * 9, CHANNELS_PER_SENSOR * 10)]
}

NEWRENDERMAP = {
    1: [x+1 for x in range(NARROW_BAND * 1)], #truncated
    2: [x+1 for x in range(NARROW_BAND * 1, NARROW_BAND * 2)], #truncated
    3: [x+1 for x in range(NARROW_BAND * 2, NARROW_BAND * 3)], #truncated
    4: [x+1 for x in range(NARROW_BAND * 3, NARROW_BAND * 5)],
    5: [x+1 for x in range(NARROW_BAND * 5, NARROW_BAND * 7)],
    6: [x+1 for x in range(NARROW_BAND * 7, NARROW_BAND * 9)],
    7: [x+1 for x in range(NARROW_BAND * 9, NARROW_BAND * 11)],
    8: [x+1 for x in range(NARROW_BAND * 11, NARROW_BAND * 13)],
    9: [x+1 for x in range(NARROW_BAND * 13, NARROW_BAND * 15)],
    10: [x+1 for x in range(NARROW_BAND * 15, NARROW_BAND * 17)],
    11: [x+1 for x in range(NARROW_BAND * 17, NARROW_BAND * 19)],
    12: [x+1 for x in range(NARROW_BAND * 19, NARROW_BAND * 21)],
    13: [x+1 for x in range(NARROW_BAND * 21, NARROW_BAND * 23)],
    14: [x+1 for x in range(NARROW_BAND * 23, NARROW_BAND * 25)],
    15: [x+1 for x in range(NARROW_BAND * 25, NARROW_BAND * 27)],
    16: [x+1 for x in range(NARROW_BAND * 27, NARROW_BAND * 28)], #truncated
    17: [x+1 for x in range(NARROW_BAND * 28, NARROW_BAND * 29)], #truncated
    18: [x+1 for x in range(NARROW_BAND * 29, NARROW_BAND * 30)] #truncated
}

#The Synchronous Player is a simple implementation that just grabs a buffer from i2c
#and throws it to the lights.
#Can delay between frames, but mostly this is just being run as fast as possible.
#Not really insulated against any i2c faults.
class syncPlayer(Process):
    """Handles access to iic and rendering of readings"""
    def __init__(self, _serialPort, _queue, _delay, _internaddr, _bus, _arraysize):
        super(syncPlayer, self).__init__()
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
        self.bus = smbus.SMBus(_bus)
        self.dmxData = [chr(0)]*513   #128 plus "spacer".
        self.lastreadings = [1]*_arraysize
        self.busyframes = 0
        self.maxbusyframes = 100
        self.isbusy = False
        self.isnightmode = False
        self.flipreadings = False
        self.busylimit = _arraysize -4
        self.blackout()
        self.render()

    def setChannel(self, chan, _intensity):
        intensity = int(_intensity)
        if chan > 512: chan = 512
        if chan < 0: chan = 0
        if intensity > 255: intensity = 255
        if intensity < 0: intensity = 0
        self.dmxData[chan] = chr(intensity)

    def blackout(self):
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
        except IOError as e:
            logging.info('i2c encountered a problem. %s', e)
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
        
        if self.flipreadings == True:
            allreadings.reverse()
            
        if self.cont != True:
            self.blackout()
            self.render()
            return
        for i in range(1, len(allreadings)):
            mychannels = NEWRENDERMAP[i] #get channels to work with
            foundchannels = len(mychannels)
            foundlights = foundchannels/4 #either one or two
            mymodifiers = [0]*foundchannels #clean array
            myreading = allreadings[i-1] #get the reading
            if myreading > 0:
                mymodifiers = INCREMENT*foundlights
            else:
                mymodifiers = COOLDOWN*foundlights
            i = 0
            for channel in mychannels:
                #addr = myChannelSet[i]
                addr = channel
                val = mymodifiers[i]
                MOD_FRAME[addr] = val
                i += 1
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
