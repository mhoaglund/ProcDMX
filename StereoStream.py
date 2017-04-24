import logging
import os
import datetime
import time
from multiprocessing import Queue
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

STREAM_PIDS = [0,1]

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

DEFAULT_COLOR = [0, 0, 90, 10]
REDUCED_DEFAULT = [0, 0, 90, 0]
THRESHOLD_COLOR = [255, 200, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
SPEED_COLORS = [[125, 50, 100, 100], [150, 75, 150, 150], [200, 75, 150, 150], [255, 125, 200, 200]]#default, walker, runner, biker (supposedly)
BACKFILL_COLOR = [175, 15, 225, 75] #backfill for the 1ft fixtures
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]

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
    25,
    4,
    CHAN_PER_FIXTURE,
    CONTOURQUEUE,
    JOBQUEUE
)

COLOR_SETTINGS = ColorSettings(
    DEFAULT_COLOR,
    REDUCED_DEFAULT,
    THRESHOLD_COLOR,
    SPEED_COLORS,
    BACKFILL_COLOR,
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

STREAM_WIDTH = 685
STREAM_ACCUMULATION = 0.10
STREAM_THRESH = 50
STREAM_BLUR = 5
MASK_PTS_RIVER = [(0.0, 0.6), (0.0, 0.4), (0.75, 0.0), (1.0, 0.0), (1.0, 1.0), (0.75, 1.0),]
MASK_PTS_CITY = [(1.0, 0.4), (1.0, 0.6), (0.25, 1.0), (0.0, 1.0), (0.0, 0.0), (0.25, 0.0)]
OPENCV_STREAM_RIVER = CVInputSettings(
    "rtsp://10.254.239.7:554/11.cgi",
    STREAM_PIDS[0],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS_RIVER,
    RIVER_CONTOURQUEUE,
    RIVER_JOBQUEUE
)

OPENCV_STREAM_CITY = CVInputSettings(
    "rtsp://10.254.239.6:554/11.cgi",
    STREAM_PIDS[1],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    24,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS_CITY,
    CITY_CONTOURQUEUE,
    CITY_JOBQUEUE
)

def generatedistortionmap():
    """
       Using a quadratic equation to build a list of pixel ranges
       which correspond to 1ft sections of flat ground captured
       in the camera's image.
    """
    _res = []
    _a = 0.005392
    _b = -0.7637
    _c = 28.00
    for f in range(0, FIXTURES/2):
        size = (_a * (f * f)) + (_b * f) + _c
        if size < 1:
            size = 1
        _res.append(int(size))
    print "Sum:", sum(_res) #This sum shouldn't exceed STREAM_WIDTH
    _running = 0
    for m in range(0, FIXTURES/2):
        _start = _running
        _end = _running+_res[m]
        _running += _res[m]
        STRIPES.append((_start, _end))
    print STRIPES

def locate(_x):
    """
       Given an x pixel value, find the appropriate stripe so the player can use that index to find a fixture.
    """
    for st in range(0, 68):
        if _x >= STRIPES[st][0] and _x < STRIPES[st][1]:
            return st

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
    if __name__ == "__main__":
        _riverprocess = CVStream(OPENCV_STREAM_RIVER)
        PROCESSES.append(_riverprocess)
        _cityprocess = CVStream(OPENCV_STREAM_CITY)
        PROCESSES.append(_cityprocess)
        _riverprocess.start()
        _cityprocess.start()

def contextualcull(cnts):
    """Cull contours based on size and index"""
    temp = []
    for cnt in cnts:
        if cnt.area > CULL_MINIMUMS[cnt.spatialindex]:
            temp.append(cnt)
    print len(temp), ' remain after cull'
    return temp

def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in PROCESSES:
        print 'found worker'
        proc.stop()
        proc.join()
        #if proc.is_alive():
        #    print 'stopping worker'
        #    proc.stop()

generatecullmap()
generatedistortionmap()
spinupcvstreams()
spinupplayer()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
        """Gathering readings from both processes"""
        riverlatest = []
        citylatest = []
        if not RIVER_CONTOURQUEUE.empty():
            riverlatest = RIVER_CONTOURQUEUE.get()
            if len(riverlatest) > 0:
                for cc in riverlatest:
                    cc.spatialindex = locate(cc.x) #assign real world x position
        if not CITY_CONTOURQUEUE.empty():
            citylatest = CITY_CONTOURQUEUE.get()
            if len(citylatest) > 0:
                for cc in citylatest:
                    #reversing the x indices for this stream
                    cc.x = STREAM_WIDTH - cc.x
                    cc.spatialindex = (FIXTURES/2) + locate(cc.x) #assign real world x position
        if len(riverlatest+citylatest) > 1:
            _all = riverlatest+citylatest
            CONTOURQUEUE.put(contextualcull(_all))
        if not RIVER_JOBQUEUE.empty():
            JOBQUEUE.put(RIVER_JOBQUEUE.get())
        if not CITY_JOBQUEUE.empty():
            JOBQUEUE.put(CITY_JOBQUEUE.get())
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
