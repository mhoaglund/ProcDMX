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
DEFAULT_COLOR = [125, 125, 125, 125]
REDUCED_DEFAULT = [0, 0, 90, 0]
THRESHOLD_COLOR = [255, 200, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
ACTIVATION_COLORS = [[225, 0, 0, 0], [0, 255, 0, 0], [25, 25, 230, 25], [0, 0, 0, 255]]#default, walker, runner, biker (supposedly)
#ACTIVATION_COLORS = [[125,125,0,255], [0,0,255,0], [255,0,0,0]]
BACKFILL_COLOR_A = [240, 0, 180, 0] #backfill for the 1ft fixtures
BACKFILL_COLOR_B = [0, 0, 255, 0]
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]
CITY_WATCHDOG = 0
RIVER_WATCHDOG = 0

UNI1 = UniverseProfile(
    SERIAL_U1,
    368,
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
    2,
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
    ACTIVATION_COLORS,
    [BACKFILL_COLOR_A, BACKFILL_COLOR_B],
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

STREAM_WIDTH = 685
STREAM_ACCUMULATION = 0.03
STREAM_THRESH = 40
STREAM_BLUR = 5
MASK_PTS = [(1.0, 0.4), (1.0, 0.6), (0.25, 1.0), (0.0, 1.0), (0.0, 0.0), (0.25, 0.0)]
#studio setup: river cam is 10.254.239.7
#sibley setup: river cam is 10.254.239.9 
OPENCV_STREAM_RIVER = CVInputSettings(
    "rtsp://10.254.239.9:554/11.cgi",
    STREAM_PIDS[0],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS,
    RIVER_CONTOURQUEUE,
    RIVER_JOBQUEUE,
    [
        (652, 184, 136),
        (638, 234, 124),
        (613, 184, 112),
        (575, 234, 100),
        (492, 184, 88),
        (295, 234, 66)
    ],
    [0.003170, 2, -0.535, 23.43],
    False
)

#studio setup: city cam is 10.254.239.6
#sibley setup: city cam is 10.254.239.8
OPENCV_STREAM_CITY = CVInputSettings(
    "rtsp://10.254.239.8:554/11.cgi",
    STREAM_PIDS[1],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS,
    CITY_CONTOURQUEUE,
    CITY_JOBQUEUE,
    [
        (664, 200, 0),
        (642, 234, 16),
        (616, 200, 28),
        (566, 234, 40),
        (458, 200, 52),
        (231, 234, 64)
    ],
    [0.003170, 2, -0.535, 23.43],
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

CVPROCESSES = []
def spinupcvstreams():
    """Set up the two opencv stream processes"""
    global _riverprocess
    global _cityprocess
    if __name__ == "__main__":
        _riverprocess = CVStream(OPENCV_STREAM_RIVER)
        CVPROCESSES.append(_riverprocess)
        _cityprocess = CVStream(OPENCV_STREAM_CITY)
        CVPROCESSES.append(_cityprocess)
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
    for cvproc in CVPROCESSES:
        print 'opencv found worker'
        cvproc.stop()

def reclaim_stream(_stream):
    """If a stream hasn't reported anything in a while, kill the process and start again."""
    for proc in CVPROCESSES:
        print 'found worker'
        proc.stop()
    time.sleep(0.5)
    spinupcvstreams()

generatecullmap()
spinupcvstreams()
spinupplayer()
RIVER_LATEST = []
CITY_LATEST = []

try:
    while True:
        global _riverprocess
        global _cityprocess
        _new = False
        if RIVER_WATCHDOG > 8000 or CITY_WATCHDOG > 8000:
            reclaim_stream('river')
            print 'Problem! Reclaiming streams...'
            RIVER_WATCHDOG = 0
            CITY_WATCHDOG = 0
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
        """Gathering readings from both processes"""
        if not RIVER_CONTOURQUEUE.empty():
            _new = True
            RIVER_LATEST = RIVER_CONTOURQUEUE.get()
            for cc in RIVER_LATEST:
                    cc.spatialindex = 68 + cc.spatialindex
            RIVER_WATCHDOG = 0
        if not CITY_CONTOURQUEUE.empty():
            _new = True
            CITY_LATEST = CITY_CONTOURQUEUE.get()
            for cc in CITY_LATEST:
                    cc.spatialindex = 72 - cc.spatialindex
            CITY_WATCHDOG = 0
        if _new:
            ALL = RIVER_LATEST + CITY_LATEST
            #print len(ALL)
            CONTOURQUEUE.put(ALL)
        RIVER_WATCHDOG += 1
        CITY_WATCHDOG += 1
        time.sleep(0.002) #tentatively committed to this.

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
