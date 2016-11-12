#Create some fake choreography to flash through the lights.
from i2cmgmt import i2cManager
from dmxworker import DmxThread
from synchronousplayer import syncPlayer

import logging
import time
import datetime
import threading
import schedule
import atexit
import os
import Queue
import math
import sys
import RPi.GPIO as gpio

logging.basicConfig(format='%(asctime)s %(message)s',filename='logs.log',level=logging.WARNING)
_readingsQueue = Queue.Queue()

SENSORS = 10
COLLECTION_SPEED = 1/50
serialport = '/dev/ttyUSB0'

IS_HARDWARE_CONNECTED = False #glorified debug flag

#TODO: update this for process-based implementation
def SpinUpWorker():
    if __name__ == '__main__':
        global _playthread
        _playthread = syncPlayer(serialport, _readingsQueue, COLLECTION_SPEED, 8, 1, SENSORS)
        _playthread.start()

def StopWorkerThread():
    if '_playthread' in globals():
        print 'found i2c worker'
        if _playthread.isAlive():
            print 'stopping i2c worker'
            _playthread.stop()
            _playthread.join()

def CleanReboot():
    schedule.clear()
    StopWorkerThread()
    if IS_HARDWARE_CONNECTED == True:
        gpio.cleanup()
    os.system('sudo reboot now')

schedule.every().day.at("23:50").do(CleanReboot)
SpinUpWorker()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    StopWorkerThread()