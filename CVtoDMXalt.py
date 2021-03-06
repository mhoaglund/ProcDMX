import logging
import os
import datetime
import time
from multiprocessing import Queue
import schedule
import cv2
import imutils
import numpy
from immediateplayer import ImmediatePlayer
from playerutils import OpenCVPlayerSettings, ColorSettings, CVInputSettings, PlayerJob

logging.basicConfig(format='%(asctime)s %(message)s', filename='logs.log', level=logging.DEBUG)

STREAM_HOST = "rtsp://10.254.239.8"
PORT = "554"
STREAM_SELECT = "11.cgi"
STREAM_ADDRESS = STREAM_HOST + ":" + PORT + "/" + STREAM_SELECT

CHAN_PER_FIXTURE = 4
SERIALPORT = '/dev/ttyUSB0'
DAY_START_HOUR = 6 #6am
DAY_END_HOUR = 19 #7pm

PROCESSES = []

CONTOURQUEUE = Queue()
JOBQUEUE = Queue()

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

OPENCV_SETTINGS = CVInputSettings(
    STREAM_ADDRESS,
    500,
    75,
    5
)

#TODO: determine if this needs to be in its own thread.
vcap = cv2.VideoCapture(STREAM_ADDRESS)
thing = vcap.get(8) 
print "Mode: ", thing

CAPTURE_W = vcap.get(3)
CAPTURE_H = vcap.get(4)
print CAPTURE_W
print CAPTURE_H
firstFrame = None

def spinupplayer():
    """Activate the DMX player thread that does our lighting work"""
    if __name__ == '__main__':
        _playthread = ImmediatePlayer(PLAYER_SETTINGS, COLOR_SETTINGS)
        PROCESSES.append(_playthread)
        _playthread.start()


def stopworkerthreads():
    """Stop any currently running threads"""
    for proc in PROCESSES:
        print 'found worker'
        if proc.is_alive():
            print 'stopping worker'
            proc.terminate()

#spinupplayer()
avg = None
IS_SHAPE_SET = False
try:
    while True:
        (grabbed, frame) = vcap.read()
        if not grabbed:
            break
    
        # resize the frame, convert it to grayscale, and blur it
        frame = imutils.resize(frame, width=OPENCV_SETTINGS.resize)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (OPENCV_SETTINGS.blur_radius, OPENCV_SETTINGS.blur_radius), 0)
        if avg == None:
            avg = numpy.float32(gray)
        cv2.accumulateWeighted(gray, avg, 0.05)
        # if the first frame is None, initialize it
        if firstFrame is None:
            firstFrame = gray
            continue
        avgres = cv2.convertScaleAbs(avg)
        FRAME_DELTA = cv2.absdiff(avgres, gray)
        THRESH = cv2.threshold(FRAME_DELTA,
                               OPENCV_SETTINGS.thresh_sensitivity,
                               255,
                               cv2.THRESH_BINARY)[1]
        THRESH = cv2.dilate(THRESH, None, iterations=2)
        (CNTS, _) = cv2.findContours(THRESH.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        CURR_CONTOURS = []
        for c in CNTS:
            if cv2.contourArea(c) < 20:
                continue
            (x, y, w, h) = cv2.boundingRect(c)
            #CURR_CONTOURS.append((x, y, w, h))
            CURR_CONTOURS.append((x+(w/2), y+(h/2))) #working with centers for now
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        if IS_SHAPE_SET is not True:
            SHAPE_SETUP = PlayerJob(
                'SET_SHAPE',
                frame.shape
            )
            JOBQUEUE.put(SHAPE_SETUP)
            IS_SHAPE_SET = True

        #if len(CURR_CONTOURS) > 0:
        CONTOURQUEUE.put(CURR_CONTOURS)
        cv2.imshow('VIDEO', frame)
        #cv2.imshow('GRAY', gray)
        #cv2.imshow('AVG', avgres)
        cv2.waitKey(1)
        if hasattr(schedule, 'run_pending'):
            schedule.run_pending()
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    TERM_JOB = PlayerJob(
                'TERM',
                None
            )
    JOBQUEUE.put(TERM_JOB)
    time.sleep(1)
    stopworkerthreads()
