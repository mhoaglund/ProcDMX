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
from playerutils import OpenCVPlayerSettings, ColorSettings, CVInputSettings, PlayerJob

#Context:
#This code spawns two opencv streaming processes which spit out contour data.
#This code spawns a single immediateplayer instance which wrangles a bunch of DMX lights.
#This file doesn't need to know anything about opencv or DMX. This file knows about utilites and real space.

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)

STREAM_PIDS = [0,1]

PROCESSES = []

STRIPES = []
CONTOURQUEUE = Queue()
JOBQUEUE = Queue()
RIVER_CONTOURQUEUE = Queue()
CITY_CONTOURQUEUE = Queue()
RIVER_JOBQUEUE = Queue()
CITY_JOBQUEUE = Queue()

UNI1 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
UNI2 = [23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 51, 52, 53, 54, 55, 56, 57, 58]
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
BACKFILL_COLOR = [125,15,175,75] #backfill for the 1ft fixtures
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]

PLAYER_SETTINGS = OpenCVPlayerSettings(
    [SERIAL_U1, SERIAL_U2],
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
    BACKFILL_COLOR,
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

STREAM_WIDTH = 685
STREAM_ACCUMULATION = 0.10
STREAM_THRESH = 35
STREAM_BLUR = 5
#Bottom left, top left, bottom right, top right. Makes perfect sense.
MASK_PTS_RIVER = [(0.0, 0.6), (0.0, 0.4), (1.0, 0.0), (1.0, 1.0)]
MASK_PTS_CITY = [(1.0, 0.4), (1.0, 0.6), (0.0, 1.0), (0.0, 0.0)]
OPENCV_STREAM_RIVER = CVInputSettings(
    "rtsp://10.254.239.7:554/11.cgi",
    STREAM_PIDS[0],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
    STREAM_ACCUMULATION,
    STREAM_BLUR,
    MASK_PTS_RIVER,
    RIVER_CONTOURQUEUE,
    RIVER_JOBQUEUE
)

#TODO reverse locations from this feed on the distmap
OPENCV_STREAM_CITY = CVInputSettings(
    "rtsp://10.254.239.6:554/11.cgi",
    STREAM_PIDS[1],
    STREAM_WIDTH,
    cv2.THRESH_BINARY,
    STREAM_THRESH,
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
            print "Locating ", _x, " at stripe ", st
            return st

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


def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in PROCESSES:
        print 'found worker'
        if proc.is_alive():
            print 'stopping worker'
            proc.terminate()

generatedistortionmap()
spinupcvstreams()
#spinupplayer()

try:
    while True:
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
        """Gathering readings from both processes"""
        riverlatest = []
        citylatest = []
        #TODO: location-based size culling
        if not RIVER_CONTOURQUEUE.empty():
            riverlatest = RIVER_CONTOURQUEUE.get()
            print 'Got something from river: ', len(riverlatest)
            if len(riverlatest) > 0:
                for cc in riverlatest:
                    cc.spatialindex = locate(cc.x) #assign real world x position
        if not CITY_CONTOURQUEUE.empty():
            citylatest = CITY_CONTOURQUEUE.get()
            print 'Got something from city: ', len(citylatest)
            if len(citylatest) > 0:
                for cc in citylatest:
                    #reversing the x indices for this stream
                    cc.x = STREAM_WIDTH - cc.x
                    cc.spatialindex = (FIXTURES/2) + locate(cc.x) #assign real world x position
        if len(riverlatest+citylatest) > 1:
            #print len(riverlatest+citylatest)
            CONTOURQUEUE.put(riverlatest+citylatest)

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
