# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
import numpy as np
import argparse
import imutils
import cv2

STREAM_HOST = "rtsp://192.168.0.29"
PORT = "554"
STREAM_SELECT = "12"
STREAM_ADDRESS = STREAM_HOST + ":" + PORT + "/" + STREAM_SELECT

vcap = cv2.VideoCapture(STREAM_ADDRESS)
# initialize the HOG descriptor/person detector
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

try:
    while True:
        (grabbed, frame) = vcap.read()
        if not grabbed:
            break

        image = imutils.resize(frame, width=min(400, image.shape[1]))
        orig = image.copy()

        # detect people in the image
        (rects, weights) = hog.detectMultiScale(image, winStride=(4, 4),
            padding=(8, 8), scale=1.05)

        # draw the original bounding boxes
        for (x, y, w, h) in rects:
            cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # show the output images
        cv2.imshow("HOG", orig)
        cv2.waitKey(1)
