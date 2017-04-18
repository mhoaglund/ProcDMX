import time
import MultiTrack

mtsm = MultiTrack.MultiTrackStereoManager("rtsp://10.254.239.9:554/11.cgi","rtsp://10.254.239.8:554/11.cgi")
print(mtsm.init())