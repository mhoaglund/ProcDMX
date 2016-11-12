import time
from random import randint
from operator import add

Channels_Per_Sensor = 12

Default_Color = [25,125,75,75]
Threshold_Color = [255,150,150,255]
Increment = [3,1,2,3] #the core aesthetic
CoolDown = [-1,-1,-1,-2]

BASE_FRAME = Default_Color*128
MAX_FRAME = Threshold_Color*128
PREV_FRAME = Default_Color*128
MOD_FRAME = [0]*512
CURRENT_FRAME = [0]*512
INDICES = [x for x in range(0,512)]

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

def PlayLatestReadings(allReadings):
        for i in range(1, len(allReadings)):
            myModifiers = [0]*Channels_Per_Sensor #clean array
            myChannelSet = RenderMap[i] #get channels to work with
            myReading = allReadings[i-1] #get the reading
            #todo: loop over channelset in sets of four, using incrementer array
            if myReading > 0:
                myModifiers = Increment*3
            else:
                myModifiers = CoolDown*3

            salt = randint(0,Channels_Per_Sensor-1)
            myModifiers[salt] += 2

            i = 0
            for channel in myChannelSet:
                addr = myChannelSet[i]
                val = myModifiers[i]
                MOD_FRAME[addr] = val
                i+=1
        ReconcileModifiers()

def ReconcileModifiers(): #intent: apply mod layer to previous light frame.
    global PREV_FRAME
    global CURRENT_FRAME

    NEW_FRAME = map(RecChannelCompact, PREV_FRAME, MOD_FRAME, INDICES)

    PREV_FRAME = NEW_FRAME
    #self.render()
    time.sleep(0.005)

def RecChannel(index): #would be cool and faster to do this with map() and partial()
    temp = PREV_FRAME[index] + MOD_FRAME[index]
    hiref = MAX_FRAME[index]
    loref = BASE_FRAME[index]
    if temp > hiref:
        temp = hiref
    if temp < loref:
        temp = loref
    return temp


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

PlayLatestReadings([0,1,1,0,0,0,1,1,0,0])
PlayLatestReadings([0,1,1,0,0,0,1,1,0,0])
PlayLatestReadings([0,1,1,0,0,0,1,1,0,0])
PlayLatestReadings([0,1,0,1,1,0,1,1,0,0])
PlayLatestReadings([0,1,1,0,0,0,1,1,0,0])
#print MOD_FRAME

