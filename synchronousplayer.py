import sys, serial, math, time, Queue, copy, schedule, smbus, logging
from multiprocessing import Process
from random import randint
from operator import add
from functools import partial

DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY=chr(6)+chr(1)+chr(2)				
DMXINIT1= chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2= chr(10)+chr(02)+chr(0)+chr(0)+chr(0)
EMPTY_FRAME = [0]*512
MOD_FRAME = [0]*512
PREV_FRAME = [0]*512
INDICES = [x for x in range(0,512)]

#Sensor nodes register hits and this pushes our lights from default to threshold, then they cool back down over time.
Default_Color = [25,125,75,75]
Threshold_Color = [255,150,150,255]
Increment = [3,1,2,3] #the core aesthetic
CoolDown = [-1,-1,-1,-2]

BASE_FRAME = Default_Color*128
MAX_FRAME = Threshold_Color*128

Channels_Per_Sensor = 12
#TODO: for future-proofing, we should set something up for staggering sets of lights for nodes.
RenderMap = {
    1: [x+1 for x in range(Channels_Per_Sensor * 1)],
    2: [x+1 for x in range(Channels_Per_Sensor * 1, Channels_Per_Sensor * 2)],
    3: [x+1 for x in range(Channels_Per_Sensor * 2, Channels_Per_Sensor * 3)],
    4: [x+1 for x in range(Channels_Per_Sensor * 3, Channels_Per_Sensor * 4)],
    5: [x+1 for x in range(Channels_Per_Sensor * 4, Channels_Per_Sensor * 5)],
    6: [x+1 for x in range(Channels_Per_Sensor * 5, Channels_Per_Sensor * 6)],
    7: [x+1 for x in range(Channels_Per_Sensor * 6, Channels_Per_Sensor * 7)],
    8: [x+1 for x in range(Channels_Per_Sensor * 7, Channels_Per_Sensor * 8)],
    9: [x+1 for x in range(Channels_Per_Sensor * 8, Channels_Per_Sensor * 9)],
    10:[x+1 for x in range(Channels_Per_Sensor * 9, Channels_Per_Sensor * 10)]
}

#The Synchronous Player is a simpler implementation that just grabs a buffer from i2c and throws it to the lights.
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
        self.delay = _delay * 0.001
        self.arraysize = _arraysize
        self.bus = smbus.SMBus(_bus)
        self.dmxData = [chr(0)]*513   #128 plus "spacer".

    def setChannel(self, chan, _intensity):
        intensity = int(_intensity)
        if chan > 512: chan = 512
        if chan < 0: chan = 0
        if intensity > 255: intensity = 255
        if intensity < 0: intensity = 0
        self.dmxData[chan] = chr(intensity)
		
    def blackout(self):
        for i in xrange(1, 512, 1):
            self.dmxData[i] = chr(0)

    def render(self):
        sdata = ''.join(self.dmxData)
        self.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

    def run(self):
        while self.cont:
            self.PlayLatestReadings()
            #do we need to destroy the smbus or anything?

    def PlayLatestReadings(self):
        try:
            allReadings = self.bus.read_i2c_block_data(self.internaddr, 0, self.arraysize)
        except IOError as e:
            logging.info('i2c encountered a problem. %s', e)
        for i in range(1, len(allReadings)):
            myModifiers = [0]*Channels_Per_Sensor #clean array
            myChannelSet = RenderMap[i] #get channels to work with
            myReading = allReadings[i-1] #get the reading
            #todo: loop over channelset in sets of four, using incrementer array
            if myReading > 0:
                myModifiers = Increment*3
            else:
                myModifiers = CoolDown*3

            i = 0
            for channel in myChannelSet:
                #addr = myChannelSet[i]
                addr = channel
                val = myModifiers[i]
                MOD_FRAME[addr] = val
                i += 1
        self.ReconcileModifiers()

    #intent: apply mod layer to previous light frame.
    def ReconcileModifiers(self): 
        global PREV_FRAME
        global CURRENT_FRAME

        NEW_FRAME = map(self.RecChannelCompact, PREV_FRAME, MOD_FRAME, INDICES) #sweet
        PREV_FRAME = NEW_FRAME
        self.render()
        time.sleep(self.delay)

    #It's not ideal that this handles channel assignment.
    def RecChannelCompact(x,y,i):
        temp = x + y
        hiref = MAX_FRAME[i]
        loref = BASE_FRAME[i]
        if temp > hiref:
            temp = hiref
        if temp < loref:
            temp = loref
        self.setChannel(i, intensity)
        return temp



        