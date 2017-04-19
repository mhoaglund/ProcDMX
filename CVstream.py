
import sys
import serial
import time
import logging
import cv2
import imutils
import numpy
import playerutils
from multiprocessing import Process, Queue
from random import randint
from operator import add

class ImmediatePlayer(Process):
    """Process to handle an individual opencv video stream.
        Args:
    """
    def __init__(self, _CVInputSettings):
        self.settings = _CVInputSettings
        self.vcap = cv2.VideoCapture(_CVInputSettings.stream_location)
        self.stream_id = _CVInputSettings.stream_id
        self.contour_queue = _CVInputSettings.contour_queue
        self.job_queue = _CVInputSettings.job_queue
        self.CAPTURE_W = self.vcap.get(3)
        self.CAPTURE_H = self.vcap.get(4)
        self.firstFrame = None
        self.avg = None
        self.IS_SHAPE_SET = False

    def run(self):
        while self.cont:
            (grabbed, frame) = self.vcap.read()
            if not grabbed:
                break

            frame = imutils.resize(frame, width=self.settings)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (self.settings.blur_radius, self.settings.blur_radius), 0)
            if self.avg == None:
                self.avg = numpy.float32(gray)
            cv2.accumulateWeighted(gray, self.avg, 0.05)
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
            for c in cnts:
                if cv2.contourArea(c) < 20:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                #CURR_CONTOURS.append((x, y, w, h))
                current_contours.append((x+(w/2), y+(h/2)))
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            if self.IS_SHAPE_SET is not True:
                SHAPE_SETUP = playerutils.PlayerJob(
                    self.stream_id,
                    'SET_SHAPE',
                    frame.shape
                )
                self.job_queue.put(SHAPE_SETUP)
                IS_SHAPE_SET = True

            self.contour_queue.put(current_contours)
            cv2.imshow('VIDEO', frame)
            cv2.waitKey(1)

    def terminate(self):
        print 'Terminating...'
        self.cont = False
        self.vcap.release()