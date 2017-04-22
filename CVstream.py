
import sys
import serial
import time
import logging
import cv2
import imutils
import numpy as np
import playerutils
from multiprocessing import Process, Queue
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
        self.contour_queue = _CVInputSettings.contour_queue
        self.job_queue = _CVInputSettings.job_queue
        self.CAPTURE_W = 0
        self.CAPTURE_H = 0
        self.firstFrame = None
        self.avg = None
        self.IS_SHAPE_SET = False
        self.cont = True
        self.isnightmode = False
        self.hasStarted = False
        

    def run(self):
        if self.hasStarted is False:
            self.vcap = cv2.VideoCapture(self.settings.stream_location)
            cv2.startWindowThread()
            self.output = cv2.namedWindow(str(self.stream_id), cv2.WINDOW_NORMAL)
            self.CAPTURE_W = self.vcap.get(3)
            self.CAPTURE_H = self.vcap.get(4)
            self.shouldmask = self.GenerateMask(self.vcap.image)
            self.hasStarted = True
        while self.cont:
            if not self.job_queue.empty():
                currentjob = self.job_queue.get()
                if currentjob.job == "TERM":
                    self.cont = False
                    self.vcap.release()
                if currentjob.job == "NIGHT":
                    logging.info('Going into Night Mode')
                    self.isnightmode = True
                if currentjob.job == "MORNING":
                    logging.info('Activating for the day')
                    self.isnightmode = False

            (grabbed, frame) = self.vcap.read()
            if not grabbed:
                #self.cont = False
                self.vcap.release()
                self.hasStarted = False
                continue
                #break #TODO: reboot stream here

            frame = imutils.resize(frame, width=self.settings.resize)
            if self.shouldmask:
                frame = cv2.bitwise_and(frame, self.mask)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
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
            thresh = cv2.dilate(thresh, None, iterations=2)
            (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            current_contours = []
            toshow = thresh.copy()
            for c in cnts:
                #if cv2.contourArea(c) < 5:
                #    continue
                #TODO: location-based size culling
                #TODO: merging of small contours maybe? why would it matter?
                #TODO: calculate aspect ratio of boundingrect to use as speed
                (x, y, w, h) = cv2.boundingRect(c)
                current_contours.append((x+(w/2), y+(h/2)))
                cv2.rectangle(gray, (x, y), (x+w, y+h), (0, 255, 0), 2)
            if self.IS_SHAPE_SET is not True:
                SHAPE_SETUP = playerutils.PlayerJob(
                    self.stream_id,
                    'SET_SHAPE',
                    frame.shape
                )
                self.job_queue.put(SHAPE_SETUP)
                IS_SHAPE_SET = True

            self.contour_queue.put(current_contours)
            cv2.imshow(str(self.stream_id), gray)
            cv2.waitKey(1)

    def GenerateMask(self, opencv_image):
        """
           Generate a proper mask from the set of proportional coordinates passed in.
           This gets called once as a setup function.
        """
        self.mask = np.zeros(opencv_image, dtype=np.uint8)
        print opencv_image
        nonrels = []
        if len(self.settings.maskc) > 3:
            for relative_coordinate in self.settings.maskc:
                nonrels.append(
                    [relative_coordinate[0]*self.CAPTURE_W,
                     relative_coordinate[1]*self.CAPTURE_H]
                    )
            mask_points = np.array([nonrels], dtype=np.uint8)
            cv2.fillConvexPoly(self.mask, mask_points, 1)
            return True
        else:
            return False


    def terminate(self):
        print 'Terminating...'
        self.cont = False
        self.vcap.release()
