#Create some fake choreography to flash through the lights.
import logging
import os
import datetime
from multiprocessing import Queue
import RPi.GPIO as gpio
import schedule
from synchronousplayer import SyncPlayer

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)
JOBQUEUE = Queue()

SENSORS = 18
COLLECTION_SPEED = 0.025
SERIALPORT = '/dev/ttyUSB0'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 19 #7pm

PROCESSES = []

def spinupworker():
    """Activate the worker thread that does our lighting work"""
    if __name__ == '__main__':
        _playthread = SyncPlayer(SERIALPORT, JOBQUEUE, COLLECTION_SPEED, 8, SENSORS, 150)
        PROCESSES.append(_playthread)
        _playthread.start()

def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in PROCESSES:
        print 'found worker'
        if proc.is_alive():
            print 'stopping worker'
            proc.terminate()

def cleanreboot():
    """Superstitious daily restart"""
    schedule.clear()
    stopworkerthreads()
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

schedule.every().day.at("19:00").do(queuenightjob)
schedule.every().day.at("6:00").do(queuemorningjob)
schedule.every().day.at("5:50").do(cleanreboot)
spinupworker()
startuptimecheck()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    stopworkerthreads()
