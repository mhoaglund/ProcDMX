import sys, math, time, Queue, copy, schedule, smbus
from threading import Thread

#this object's job is to rapidly poll the master arduino for readings and pull them in over i2c,
#adding them to a queue of readings that other threads will work away on.
class i2cManager(Thread):
    def __init__(self,_queue, _interval, _internaddr, _bus, _arraysize):
        super(i2cManager, self).__init__() #TODO understand this line
        self.cont = True
        self.MyQueue = _queue
        self.internaddr = _internaddr
        self.interval = _interval
        self.arraysize = _arraysize
        self.bus = smbus.SMBus(_bus)

    def run(self):
        while self.cont:
            self.GetLatestReadings()
            #do we need to destroy the smbus or anything?

    def GetLatestReadings(self):
        try:
            allReadings = bus.read_i2c_block_data(self.internaddr,0,self.arraysize)
            self.MyQueue.put(allReadings)
        except IOError as e:
            break
            #TODO: hook up logging here. log "I/O error({0}): {1}".format(e.errno, e.strerror)
        #Recovery stuff? throw up some gradually-decaying fake readings?
        sleep(self.interval)


        