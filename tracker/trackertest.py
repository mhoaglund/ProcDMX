import time
import MultiTrack

isMTSMrunning = False
mtsm = MultiTrack.MultiTrackStereoManager("rtsp://10.254.239.9:554/11.cgi","rtsp://10.254.239.8:554/11.cgi")
print(mtsm.init())

try:
    while True:
        if isMTSMrunning is not True:
            thing = mtsm.run()
            isMTSMrunning = False
except (KeyboardInterrupt, SystemExit):
    print 'stopping...'
    mtsm.stop_capture()
