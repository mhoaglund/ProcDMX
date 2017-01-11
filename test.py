#Create some fake choreography to flash through the lights.
import logging
import os
import datetime
from multiprocessing import Queue
import RPi.GPIO as gpio
import schedule
from synchronousplayer import SyncPlayer
from playerutils import PlayerSettings
from playerutils import ColorSettings 

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)
JOBQUEUE = Queue()

SENSORS = 18
COLLECTION_SPEED = 0.025
SERIALPORT = '/dev/ttyUSB0'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 19 #7pm

PROCESSES = []

CHAN_PER_FIXTURE = 4
RENDERMAP = {
    1: [x+1 for x in range(CHAN_PER_FIXTURE * 1)],
    2: [x+1 for x in range(CHAN_PER_FIXTURE * 1, CHAN_PER_FIXTURE * 2)],
    3: [x+1 for x in range(CHAN_PER_FIXTURE * 2, CHAN_PER_FIXTURE * 4)],
    4: [x+1 for x in range(CHAN_PER_FIXTURE * 4, CHAN_PER_FIXTURE * 6)],
    5: [x+1 for x in range(CHAN_PER_FIXTURE * 6, CHAN_PER_FIXTURE * 8)],
    6: [x+1 for x in range(CHAN_PER_FIXTURE * 8, CHAN_PER_FIXTURE * 10)],
    7: [x+1 for x in range(CHAN_PER_FIXTURE * 10, CHAN_PER_FIXTURE * 12)],
    8: [x+1 for x in range(CHAN_PER_FIXTURE * 12, CHAN_PER_FIXTURE * 14)],
    9: [x+1 for x in range(CHAN_PER_FIXTURE * 14, CHAN_PER_FIXTURE * 16)],
    10: [x+1 for x in range(CHAN_PER_FIXTURE * 16, CHAN_PER_FIXTURE * 18)],
    11: [x+1 for x in range(CHAN_PER_FIXTURE * 18, CHAN_PER_FIXTURE * 20)],
    12: [x+1 for x in range(CHAN_PER_FIXTURE * 20, CHAN_PER_FIXTURE * 22)],
    13: [x+1 for x in range(CHAN_PER_FIXTURE * 22, CHAN_PER_FIXTURE * 24)],
    14: [x+1 for x in range(CHAN_PER_FIXTURE * 24, CHAN_PER_FIXTURE * 26)],
    15: [x+1 for x in range(CHAN_PER_FIXTURE * 26, CHAN_PER_FIXTURE * 28)],
    16: [x+1 for x in range(CHAN_PER_FIXTURE * 28, CHAN_PER_FIXTURE * 30)],
    17: [x+1 for x in range(CHAN_PER_FIXTURE * 30, CHAN_PER_FIXTURE * 31)],
    18: [x+1 for x in range(CHAN_PER_FIXTURE * 31, CHAN_PER_FIXTURE * 32)]
}

DEFAULT_COLOR = [100, 0, 180, 0]
REDUCED_DEFAULT = [50, 0, 90, 0]
THRESHOLD_COLOR = [125, 50, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [4, 2, 6, 2] #the core aesthetic
DECREMENT = [-2, -1, -2, -2]
ALTDECREMENT = [-8, -1, -6, -1]

EDGE_GATES = [17, 16, 15, 2, 1, 0]

PLAY_SETTINGS = PlayerSettings(
    SERIALPORT,
    COLLECTION_SPEED,
    EDGE_GATES,
    8,
    SENSORS,
    150,
    32,
    CHAN_PER_FIXTURE,
    RENDERMAP
)

COLOR_SETTINGS = ColorSettings(
    DEFAULT_COLOR,
    REDUCED_DEFAULT,
    THRESHOLD_COLOR,
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT,
    ALTDECREMENT #TODO refactor this out and just double the main DECREMENT
)

def spinupworker():
    """Activate the worker thread that does our lighting work"""
    if __name__ == '__main__':
        _playthread = SyncPlayer(PLAY_SETTINGS, COLOR_SETTINGS, JOBQUEUE)
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
