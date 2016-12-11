#Create some fake choreography to flash through the lights.
import logging
import os
import datetime
from multiprocessing import Queue
import RPi.GPIO as gpio
import schedule
from synchronousplayer import syncPlayer

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)
JOBQUEUE = Queue()

SENSORS = 18
COLLECTION_SPEED = 0.025
SERIALPORT = '/dev/ttyUSB0'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 21 #9pm

IS_HARDWARE_CONNECTED = False #glorified debug flag
Processes = []

#TODO: update this for process-based implementation
def spinupworker():
    """Activate the worker thread that does our lighting work"""
    if __name__ == '__main__':
        global _playthread
        _playthread = syncPlayer(SERIALPORT, JOBQUEUE, COLLECTION_SPEED, 8, 1, SENSORS)
        Processes.append(_playthread)
        _playthread.start()

def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in Processes:
        print 'found worker'
        if proc.is_alive():
            print 'stopping worker'
            proc.stop()
            proc.join()

def cleanreboot():
    """Superstitious daily restart"""
    schedule.clear()
    stopworkerthreads()
    if IS_HARDWARE_CONNECTED is True:
        gpio.cleanup()
    os.system('sudo reboot now')

def queuenightjob():
    """Queue a message to the worker process to switch over to night"""
    JOBQUEUE.put("NIGHT")

def queuemorningjob():
    """Queue a message to the worker process to resume normal function"""
    JOBQUEUE.put("MORNING")

def startuptimecheck():
    """On startup, figure out what mode to be in. Couldve been shut down at a weird time."""
    print 'Starting!'
    now = datetime.datetime.now()
    todaystart = now.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
    todayend = now.replace(hour=DAY_END_HOUR, minute=0, second=0, microsecond=0)
    if now >= todaystart and now <= todayend:
        print 'Day Mode'
        queuemorningjob()
    else:
        print 'Night Mode'
        queuenightjob()

schedule.every().day.at("21:30").do(queuenightjob)
schedule.every().day.at("6:00").do(queuemorningjob)
schedule.every().day.at("5:50").do(cleanreboot)
spinupworker()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    stopworkerthreads()
