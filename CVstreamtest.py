import cv2
import datetime
import imutils
import time
import argparse
print cv2.__version__

STREAM_HOST = "rtsp://192.168.0.29"
PORT = "554"
STREAM_SELECT = "11"
STREAM_ADDRESS = STREAM_HOST + ":" + PORT + "/" + STREAM_SELECT

ap = argparse.ArgumentParser()
vcap = cv2.VideoCapture(STREAM_ADDRESS)

firstFrame = None

while(1):
    (grabbed, frame) = vcap.read()
    if not grabbed:
        break
 
    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # if the first frame is None, initialize it
    if firstFrame is None:
        firstFrame = gray
        continue

    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations = 2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in cnts:
        if cv2.contourArea(c) < 20:
            continue
        (x,y,w,h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)

    #ret, frame = vcap.read()
    cv2.imshow('VIDEO', frame)
    cv2.waitKey(1)
