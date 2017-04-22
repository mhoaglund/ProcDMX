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

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)

STREAM_PIDS = [222,111]

PROCESSES = []

CONTOURQUEUE = Queue()
JOBQUEUE = Queue()
RIVER_CONTOURQUEUE = Queue()
CITY_CONTOURQUEUE = Queue()
RIVER_JOBQUEUE = Queue()
CITY_JOBQUEUE = Queue()

CHAN_PER_FIXTURE = 4
SERIALPORT = '/dev/ttyUSB0'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 5 #5am

DEFAULT_COLOR = [0, 0, 90, 10]
REDUCED_DEFAULT = [0, 0, 90, 0]
THRESHOLD_COLOR = [255, 200, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]

PLAYER_SETTINGS = OpenCVPlayerSettings(
    SERIALPORT,
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
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

STREAM_WIDTH = 600
STREAM_ACCUMULATION = 0.10
STREAM_THRESH = 35
STREAM_BLUR = 5
#Bottom left, top left, bottom right, top right. Makes perfect sense.
MASK_PTS_RIVER = [(0.0, 0.6), (0.0, 0.4), (1.0, 0.0), (1.0, 1.0)]
MASK_PTS_CITY = [(1.0, 1.0), (1.0, 0.0), (0.0, 0.4), (0.0, 0.6)]
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

def spinupplayer():
    """Activate the DMX player thread that does our lighting work"""
    if __name__ == '__main__':
        _playthread = ImmediatePlayer(PLAYER_SETTINGS, COLOR_SETTINGS)
        PROCESSES.append(_playthread)
        _playthread.start()

def spinupCVstreams():
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

spinupCVstreams()
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
            if len(riverlatest) > 1:
                print 'Got something from river...'
        if not CITY_CONTOURQUEUE.empty():
            citylatest = CITY_CONTOURQUEUE.get()
            if len(citylatest) > 1:
                print 'Got something from city...'
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
