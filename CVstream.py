
import sys
import serial
import time
import logging
import cv2
import imutils
import numpy as np
import playerutils
import math
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
        self.shouldShow = False
        self.STRIPES = []
        self.stripe_count = 72 #each camera sees 72 feet of flat distance
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
                self.generatedistortionmap()
                self.vcap = cv2.VideoCapture(self.settings.stream_location)
                if self.shouldShow:
                    cv2.startWindowThread()
                    self.output = cv2.namedWindow(str(self.stream_id), cv2.CV_WINDOW_AUTOSIZE)
                self.hasStarted = True

            try:
                #throwaway = self.vcap.grab()
                (grabbed, frame) = self.vcap.read()
            except cv2.error as e:
                logging.error('Opencv: %s', e)
                continue

            if not grabbed or type(frame) is None:
                logging.info('Grab failed...')
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

            total_cntr_area = 0
            max_cntr_area = 200000 #this figure is a guess.
            for c in cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                _area = cv2.contourArea(c)
                total_cntr_area += _area
                #_rect = cv2.minAreaRect(c) can switch to this and get rotation if need be.
                if _area > self.settings.detectionMinimum and w > 2:
                    cdc = playerutils.CalcdContour(x, y, w, h, self.stream_id)
                    cdc.area = _area
                    if cdc.area > 150:
                        cdc.spatialindex = self.locate(cdc.center[0]) #assign real world x position
                        if cdc.spatialindex < 69:
                            current_contours.append(cdc)
                        if self.shouldShow:
                            cv2.rectangle(gray, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            if self.stream_id == 'River':
                                cv2.putText(
                                    gray,
                                    str(self.stripe_count + cdc.spatialindex),
                                    (x, y),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1,
                                    (255, 255, 255),
                                    2)
                            if self.stream_id == 'City':
                                cv2.putText(
                                    gray,
                                    str(self.stripe_count - cdc.spatialindex),
                                    (x, y),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1,
                                    (255, 255, 255),
                                    2)

            if self.shouldShow:
                for point in self.settings.waypoints:
                    cv2.rectangle(
                        gray,
                        (point[0], point[1]),
                        (point[0]+4, point[1]+4),
                        (255, 255, 255),
                        1)
                    cv2.putText(
                        gray,
                        str(point[2]),
                        (point[0], point[1]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (125, 125, 125),
                        2)
            if len(current_contours) > 80 or total_cntr_area > max_cntr_area:
                #camera must be changing exposure or there's feedback
                current_contours = []
            self.my_contour_queue.put(current_contours)
            if self.shouldShow:
                cv2.imshow(str(self.stream_id), gray)
            cv2.waitKey(20)
        self.vcap.release()
        print 'Released Capture: ', self.stream_id
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

    def generatedistortionmap(self):
        """
        Using a quadratic equation to build a list of pixel ranges
        which correspond to 1ft sections of flat ground captured
        in the camera's image.
        """
        _res = []
        _a = self.settings.quadratics[0]
        _b = self.settings.quadratics[2]
        _c = self.settings.quadratics[3]
        for f in range(0, self.stripe_count):
            size = (_a * (f * f)) + (_b * f) + _c
            if size < 1:
                size = 1
            _res.append(int(size))
        if self.stream_id == "City":
            _res[0] -=4
        _running = 0
        for m in range(0, self.stripe_count):
            _start = _running
            _end = _running+_res[m]
            _running += _res[m]
            self.STRIPES.append((_start, _end))

    @staticmethod
    def _pull_back(_input, _scalar, _base):
        """
            The location algorithms just need help being right.
        """
        _result = 0
        _salt = 1.0-((_base/_input)/_scalar)
        _result = _salt*_input
        return int(_result)

    @staticmethod
    def _pull_back_alt(_input, _mod, _base):
        """
            The location algorithms just need help being right.
        """
        _result = 0
        if _input > _mod:
            _input = _input + _mod
        distance_from_end = _base - _input
        _pepper = (1.0 - (distance_from_end/_base))
        _result = int( _input * _pepper)
        if _result > 685:
            _result = 685
        return _result

    def locate(self, _x):
        """
           Given an x pixel value, find the appropriate stripe so the player can use that index to find a fixture.
        """
        stripe = 99
        overlap_tweak = 0
        if self.stream_id == "River":
            _x = self._pull_back_alt(_x, 5, 667.0)
            overlap_tweak = 4
        else:
            _x = self._pull_back(_x, 0, 650.0)
        for st in range(0, self.stripe_count):
            if _x >= self.STRIPES[st][0] and _x < self.STRIPES[st][1]:
                stripe = st
        
        return stripe - overlap_tweak

    def stop(self):
        print 'Terminating...'
        self.cont = False
        self.exit_event.set()

    def refresh(self):
        logging.info('Experiencing a problem with stream %s, rebooting', self.stream_id)
        self.vcap.release()
        self.hasStarted = False