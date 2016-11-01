#Create some fake choreography to flash through the lights.
from i2cmgmt import i2cManager
from dmxworker import DmxThread

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

SENSORS = 2
COLLECTION_SPEED = 50

IS_HARDWARE_CONNECTED = False #glorified debug flag

def SpinUpi2c():
    if __name__ == '__main__':
        global _i2cthread
        _i2cthread = i2cManager(_readingsQueue, COLLECTION_SPEED, 8, 1, SENSORS)
        _i2cthread.start()

def Stopi2cThread():
    if '_i2cthread' in globals():
        print 'found i2c worker'
        if _i2cthread.isAlive():
            print 'stopping i2c worker'
            _i2cthread.stop()
            _i2cthread.join()

def CleanReboot():
    schedule.clear()
    Stopi2cThread()
    if IS_HARDWARE_CONNECTED == True:
        gpio.cleanup()
    os.system('sudo reboot now')

schedule.every().day.at("23:50").do(CleanReboot)

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    Stopi2cThread()