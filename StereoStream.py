import logging
import os
import datetime
import time
from multiprocessing import Queue, Event
import schedule
import cv2
import imutils
import numpy as np
from immediateplayer import ImmediatePlayer
from CVstream import CVStream
from playerutils import OpenCVPlayerSettings, ColorSettings, CVInputSettings, PlayerJob, UniverseProfile

#Context:
#This code spawns two opencv streaming processes which spit out contour data.
#This code spawns a single immediateplayer instance which wrangles a bunch of DMX lights.
#This file doesn't need to know anything about opencv or DMX. This file knows about utilites and real space.

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)

STREAM_PIDS = ['River','City']

PROCESSES = []

STRIPES = []
CULL_MINIMUMS = []
CONTOURQUEUE = Queue()
JOBQUEUE = Queue()
RIVER_CONTOURQUEUE = Queue()
CITY_CONTOURQUEUE = Queue()
RIVER_JOBQUEUE = Queue()
CITY_JOBQUEUE = Queue()

#BACKFILL = [51, 52, 53, 54, 55, 56, 57, 58]

FIXTURES = 136
CHAN_PER_FIXTURE = 4
SERIAL_U1 = '/dev/ttyUSB0'
SERIAL_U2 = '/dev/ttyUSB1'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 5 #5am

PRIORITIZE_FASTEST = False
DEFAULT_COLOR = [70, 0, 255, 0]
REDUCED_DEFAULT = [0, 0, 90, 0]
THRESHOLD_COLOR = [255, 200, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
SPEED_COLORS = [[255, 255, 255, 255], [150, 200, 150, 150], [175, 175, 255, 175]]#default, walker, runner, biker (supposedly)
BACKFILL_COLOR_A = [240, 0, 180, 0] #backfill for the 1ft fixtures
BACKFILL_COLOR_B = [0, 0, 255, 0]
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]

UNI1 = UniverseProfile(
    SERIAL_U1,
    369,
    28
)
UNI2 = UniverseProfile(
    SERIAL_U2,
    513,
    0
)
PLAYER_SETTINGS = OpenCVPlayerSettings(
    [UNI1, UNI2],
    1,
    16,
    6,
    4,
    CHAN_PER_FIXTURE,
    CONTOURQUEUE,
    JOBQUEUE
)

COLOR_SETTINGS = ColorSettings(
    DEFAULT_COLOR,
    DEFAULT_COLOR,
    THRESHOLD_COLOR,
    SPEED_COLORS,
    [BACKFILL_COLOR_A, BACKFILL_COLOR_B],
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

STREAM_WIDTH = 685
STREAM_ACCUMULATION = 0.05
STREAM_THRESH = 50
STREAM_BLUR = 5
MASK_PTS_RIVER = [(0.0, 0.6), (0.0, 0.4), (0.75, 0.0), (1.0, 0.0), (1.0, 1.0), (0.75, 1.0),]
MASK_PTS_CITY = [(1.0, 0.4), (1.0, 0.6), (0.25, 1.0), (0.0, 1.0), (0.0, 0.0), (0.25, 0.0)]
OPENCV_STREAM_RIVER = CVInputSettings(
    "rivertest.mp4",
    STREAM_PIDS[0],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS_CITY,
    CITY_CONTOURQUEUE,
    RIVER_JOBQUEUE,
    [0.006592, -0.8578, 28.85],
    False
)

OPENCV_STREAM_CITY = CVInputSettings(
    "citytest.mp4",
    STREAM_PIDS[1],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS_CITY,
    RIVER_CONTOURQUEUE,
    CITY_JOBQUEUE,
    [0.006592, -0.8578, 28.85],
    False
)

def generatecullmap():
    global CULL_MINIMUMS
    _res = []
    _a = -0.05147
    _b = 7.0
    _c = 12 #tweaking this changes the outer reaches of the cull map
    for f in range(0, FIXTURES):
        minsize = (_a * (f * f)) + (_b * f) + _c
        _res.append(minsize)
    CULL_MINIMUMS = _res

def spinupplayer():
    """Activate the DMX player thread that does our lighting work"""
    if __name__ == '__main__':
        _playthread = ImmediatePlayer(PLAYER_SETTINGS, COLOR_SETTINGS)
        PROCESSES.append(_playthread)
        _playthread.start()

def spinupcvstreams():
    """Set up the two opencv stream processes"""
    global _riverprocess
    global _cityprocess
    if __name__ == "__main__":
        _riverprocess = CVStream(OPENCV_STREAM_RIVER)
        PROCESSES.append(_riverprocess)
        _cityprocess = CVStream(OPENCV_STREAM_CITY)
        PROCESSES.append(_cityprocess)
        _riverprocess.start()
        _cityprocess.start()

def contextualcull(cnts):
    """Cull calcdcontours based on size and index"""
    temp = []
    actualout = []
    indicesused = []
    for cnt in cnts:
        if cnt.area > CULL_MINIMUMS[cnt.spatialindex]:
            temp.append(cnt)
            if cnt.spatialindex not in indicesused:
                indicesused.append(cnt.spatialindex)
    if PRIORITIZE_FASTEST:
        for sindex in indicesused: #filter down to the fastest contour.
            _allatthisindex = [x for x in temp if x == sindex]
            highest = _allatthisindex.sort(key=lambda y: y.spd, reverse=False)[0]
            actualout.append(highest)
    else:
        actualout = temp
    print 'Contours after cull: ', len(actualout)
    return actualout

def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in PROCESSES:
        print 'found worker'
        proc.stop()
        proc.join()
        #if proc.is_alive():
        #    print 'stopping worker'
        #    proc.stop()

def reclaim_stream(_stream):
    """If a stream hasn't reported anything in a while, kill the process and start again."""
    #print 'A stream has stopped. Restarting it...'
    _stream.refresh()

generatecullmap()
spinupcvstreams()
spinupplayer()
RIVER_LATEST = []
CITY_LATEST = []
CITY_WATCHDOG = 0
RIVER_WATCHDOG = 0

try:
    while True:
        global _riverprocess
        global _cityprocess
        print RIVER_WATCHDOG
        print CITY_WATCHDOG
        #if RIVER_WATCHDOG > 20000:
            #reclaim_stream(_riverprocess)
        #if CITY_WATCHDOG > 20000:
            #reclaim_stream(_cityprocess)
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
        """Gathering readings from both processes"""
        if not RIVER_CONTOURQUEUE.empty():
            RIVER_LATEST = RIVER_CONTOURQUEUE.get()
            RIVER_WATCHDOG = 0
        if not CITY_CONTOURQUEUE.empty():
            CITY_LATEST = CITY_CONTOURQUEUE.get()
            for cc in CITY_LATEST:
                    #reversing the x indices for this stream
                    cc.spatialindex = (FIXTURES/2) + cc.spatialindex #assign real world x position
            CITY_WATCHDOG = 0
        ALL = RIVER_LATEST + CITY_LATEST
        #CONTOURQUEUE.put(contextualcull(_all))
        CONTOURQUEUE.put(ALL)
        RIVER_WATCHDOG += 1
        CITY_WATCHDOG += 1
        time.sleep(0.02)

except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    for spid in STREAM_PIDS:
        TERM_JOB = PlayerJob(
            spid,
            'TERM',
            None
            )
        JOBQUEUE.put(TERM_JOB)
    time.sleep(1)
    stopworkerthreads()
