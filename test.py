#Create some fake choreography to flash through the lights.
import logging
import os
from multiprocessing import Queue
import RPi.GPIO as gpio
import schedule
from synchronousplayer import syncPlayer

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)
JOBQUEUE = Queue()

SENSORS = 10
COLLECTION_SPEED = 0.025
serialport = '/dev/ttyUSB0'

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

schedule.every().day.at("21:30").do(queuenightjob)
schedule.every().day.at("6:00").do(queuemorningjob)
schedule.every().day.at("23:50").do(cleanreboot)
spinupworker()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    stopworkerthreads()
