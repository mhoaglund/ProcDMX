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
INCREMENT = [2, 1, 3, 1] #the core aesthetic
COOLDOWN = [-2, -1, -2, -2]
VOLATILITY = 3

BASE_FRAME = DEFAULT_COLOR*LIGHTS_IN_USE
MAX_FRAME = THRESHOLD_COLOR*LIGHTS_IN_USE
BUSY_FRAME = THRESHOLD_COLOR*LIGHTS_IN_USE
NIGHT_FRAME = NIGHT_IDLE_COLOR*30

CHANNELS_PER_SENSOR = 12
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

#The Synchronous Player is a simpler implementation that just grabs a buffer from i2c
#and throws it to the lights.
#Can delay between frames, but mostly this is just being run as fast as possible.
#Not really insulated against any i2c faults.
class syncPlayer(Process):
    def __init__(self, _serialPort, _queue, _delay, _internaddr, _bus, _arraysize):
        super(syncPlayer, self).__init__()
        print 'starting worker'
        try:
            self.serial = serial.Serial(_serialPort, baudrate=57600)
        except:
            print "Error: could not open Serial Port"
            sys.exit(0)
        self.cont = True
        self.MyQueue = _queue
        self.internaddr = _internaddr
        self.delay = _delay
        self.arraysize = _arraysize
        self.bus = smbus.SMBus(_bus)
        self.dmxData = [chr(0)]*513   #128 plus "spacer".
        self.lastreadings = [1]*_arraysize
        self.busyframes = 0
        self.maxbusyframes = 100
        self.isbusy = False
        self.busylimit = _arraysize -2
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
        sdata = ''.join(self.dmxData)
        self.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

    def run(self):
        while self.cont:
            self.playlatestreadings()
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

    def playlatestreadings(self):
        """Main loop."""
        if not self.MyQueue.empty():
            currentjob = self.MyQueue.get()
            if currentjob == "NIGHT":
                print 'Going into night mode' #TODO this for real
                return
            if currentjob == "MORNING":
                print 'Activating for the day' #TODO undo whatever night mode means
        try:
            allreadings = self.bus.read_i2c_block_data(self.internaddr, 0, self.arraysize)
            self.lastreadings = allreadings
            if sum(allreadings) > self.busylimit:
                self.busyframes += 1
            else:
                self.busyframes = 0

            #if we are super busy, just lock at 1 on all channels
            if self.busyframes > self.maxbusyframes:
                allreadings = [1] * self.arraysize
        except IOError as e:
            logging.info('i2c encountered a problem. %s', e)
            allreadings = self.lastreadings
        if self.cont != True:
            self.blackout()
            self.render()
            return
        for i in range(1, len(allreadings)):
            mymodifiers = [0]*CHANNELS_PER_SENSOR #clean array
            mychannels = RENDERMAP[i] #get channels to work with
            myReading = allreadings[i-1] #get the reading
            if myReading > 0:
                mymodifiers = INCREMENT*3
            else:
                mymodifiers = COOLDOWN*3

            i = 0
            for channel in mychannels:
                #addr = myChannelSet[i]
                addr = channel
                val = mymodifiers[i]
                MOD_FRAME[addr] = val
                i += 1
        self.ReconcileModifiers()

    #intent: apply mod layer to previous light frame.
    def ReconcileModifiers(self): 
        global PREV_FRAME
        global CURRENT_FRAME

        NEW_FRAME = map(self.RecChannelCompact, PREV_FRAME, MOD_FRAME, INDICES) #sweet
        PREV_FRAME = NEW_FRAME
        for ch in range(0, len(NEW_FRAME)):
           self.setChannel(ch+1, NEW_FRAME[ch])
        self.render()
        time.sleep(self.delay)

    def RecChannelCompact(self, x,y,i):
        temp = x + y
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
