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

logging.basicConfig(format='%(asctime)s %(message)s',filename='logs.log',level=logging.DEBUG)
_readingsQueue = Queue.Queue()

SENSORS = 10
COLLECTION_SPEED = 1/50
serialport = '/dev/ttyUSB0'

IS_HARDWARE_CONNECTED = False #glorified debug flag
Processes = []

#TODO: update this for process-based implementation
def SpinUpWorker():
    if __name__ == '__main__':
        global _playthread
        _playthread = syncPlayer(serialport, _readingsQueue, COLLECTION_SPEED, 8, 1, SENSORS)
        Processes.append(_playthread)
        _playthread.start()

def StopWorkerThreads():
    for proc in Processes:
        print 'found worker'
        if proc.is_alive():
            print 'stopping i2c worker'
            proc.stop()
            proc.join()


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
    StopWorkerThreads()