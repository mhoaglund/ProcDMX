
import sys
import serial
import time
import logging
import cv2
import imutils
import numpy as np
import playerutils
from multiprocessing import Process, Queue, Event
from random import randint
from operator import add

class CVStream(Process):
    """Process to handle an individual opencv video stream.
        Args:
    """
    def __init__(self, _CVInputSettings):
        super(CVStream, self).__init__()
        print 'Starting CVstream'
        self.settings = _CVInputSettings
        self.vcap = cv2.VideoCapture()
        self.stream_id = _CVInputSettings.stream_id
        self.my_contour_queue = _CVInputSettings.contour_queue
        self.job_queue = _CVInputSettings.job_queue
        self.firstFrame = None
        self.avg = None
        self.IS_SHAPE_SET = False
        self.cont = True
        self.isnightmode = False
        self.hasStarted = False
        self.mask = []
        self.hasMasked = False
        self.shouldmask = False
        self.shouldShow = True
        self.STRIPES = self.settings.stripes

        self.exit_event = Event()

    def run(self):
        while not self.exit_event.is_set():
            if not self.job_queue.empty():
                currentjob = self.job_queue.get()
                if currentjob.job == "REFRESH":
                    self.vcap.release()
                    cv2.waitKey(1)
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                    time.sleep(5)
                    self.vcap = cv2.VideoCapture()
                    self.hasStarted = False

            if self.hasStarted is False:
                print 'setting up', self.stream_id
                logging.info('Performing stream setup on %s', self.stream_id)
                self.vcap = cv2.VideoCapture(self.settings.stream_location)
                if self.shouldShow:
                    cv2.startWindowThread()
                    self.output = cv2.namedWindow(str(self.stream_id), cv2.CV_WINDOW_AUTOSIZE)
                self.hasStarted = True

            try:
                #throwaway = self.vcap.grab()
                (grabbed, frame) = self.vcap.read()
            except cv2.error as e:
                print e
                #self.vcap.release()
                #self.hasStarted = False
                logging.error('Stream error: %s', e)
                logging.info('Stream crash on %s. Attempting to restart stream...', self.stream_id)
                continue

            if not grabbed or type(frame) is None:
                print 'Stream problem! ', self.stream_id, 
                self.vcap.release()
                self.hasStarted = False
                if self.shouldShow:
                    cv2.waitKey(1)
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                logging.info('Stream crash on %s. Attempting to restart stream...', self.stream_id)
            #   print 'Crashed. Restarting stream...'
                continue

            frame = imutils.resize(frame, width=self.settings.resize)
            if not self.hasMasked:
                self.shouldmask = self.GenerateMask(frame)
                self.hasMasked = True
            if self.shouldmask:
                frame = cv2.bitwise_and(frame, frame, mask = self.mask)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            #gray = cv2.equalizeHist(gray)
            #gray = cv2.GaussianBlur(gray, (self.settings.blur_radius, self.settings.blur_radius), 0)
            
            if self.avg == None:
                self.avg = np.float32(gray)
            cv2.accumulateWeighted(gray, self.avg, self.settings.accumulation)
            if self.firstFrame is None:
                self.firstFrame = gray
                continue
            avgres = cv2.convertScaleAbs(self.avg)
            frame_delta = cv2.absdiff(avgres, gray)
            thresh = cv2.threshold(frame_delta,
                                   self.settings.thresh_sensitivity,
                                   255,
                                   cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=3)
            (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            current_contours = []
            toshow = thresh.copy()
            for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                #_rect = cv2.minAreaRect(c) can switch to this and get rotation if need be.
                if cv2.contourArea(c) > self.settings.detectionMinimum and w > 2:
                    cdc = playerutils.CalcdContour(x, y, w, h, self.stream_id)
                    cdc.area = cv2.contourArea(c)
                    if cdc.area > 150:
                        cdc.spatialindex = self.locate(cdc.center[0]) #assign real world x position
                        if cdc.spatialindex < 69:
                            current_contours.append(cdc)
                        if self.shouldShow:
                            cv2.rectangle(gray, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(gray, str(cdc.spatialindex),(x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            if self.shouldShow:
                cv2.rectangle(gray, (650, 190), (654, 194), (255,255,255), 2)
                cv2.rectangle(gray, (100, 190), (104, 194), (255,255,255), 2)
            if len(current_contours) > 80: #camera must be changing exposure
                current_contours = []
            self.my_contour_queue.put(current_contours)
            if self.shouldShow:
                cv2.imshow(str(self.stream_id), gray)
            cv2.waitKey(20)
        self.vcap.release()
        print 'Release Cap: ', self.stream_id
        if self.shouldShow:
            cv2.waitKey(1)
            cv2.destroyAllWindows()
            cv2.waitKey(1)

    def GenerateMask(self, _frame):
        """
           Generate a proper mask from the set of proportional coordinates passed in.
           This gets called once as a setup function.
        """
        self.mask = np.zeros(_frame.shape[:2], dtype=np.uint8)
        nonrels = []
        if len(self.settings.maskc) > 3:
            for relative_coordinate in self.settings.maskc:
                nonrels.append(
                    [int(relative_coordinate[0]*_frame.shape[1]),
                     int(relative_coordinate[1]*_frame.shape[0])]
                    )
            mask_points = np.array(nonrels, dtype=np.int32)
            cv2.fillConvexPoly(self.mask, mask_points, 1)
            return True
        else:
            return False

    def locate(self, _x):
        """
           Given an x pixel value, find the appropriate stripe so the player can use that index to find a fixture.
        """
        stripe = 99
        for st in range(0, len(self.STRIPES)):
            if _x >= self.STRIPES[st][0] and _x < self.STRIPES[st][1]:
                stripe = st
        return stripe

    def stop(self):
        print 'Terminating...'
        self.cont = False
        self.exit_event.set()
        super(CVStream, self).terminate()

    def refresh(self):
        logging.info('Experiencing a problem with stream %s, rebooting', self.stream_id)
        self.vcap.release()
        self.hasStarted = False
