
import logging
import os
import datetime
import time
from multiprocessing import Queue
from immediateplayer import ImmediatePlayer
from playerutils import OpenCVPlayerSettings, ColorSettings, CVInputSettings, PlayerJob, UniverseProfile

PROCESSES = []

SERIAL_U1 = '/dev/ttyUSB0'
SERIAL_U2 = '/dev/ttyUSB1'
CONTOURQUEUE = Queue()
JOBQUEUE = Queue()
FIXTURES = 136
CHAN_PER_FIXTURE = 4
DEFAULT_COLOR = [0, 0, 90, 10]
REDUCED_DEFAULT = [0, 0, 90, 0]
THRESHOLD_COLOR = [255, 200, 255, 125]
BUSY_THRESHOLD_COLOR = [150, 120, 255, 200]
SPEED_COLORS = [[125, 50, 100, 100], [150, 75, 150, 150], [200, 75, 150, 150], [255, 125, 200, 200]]#default, walker, runner, biker (supposedly)
BACKFILL_COLOR = [175, 15, 225, 75] #backfill for the 1ft fixtures
NIGHT_IDLE_COLOR = [125, 125, 0, 255]
INCREMENT = [5, 3, 7, 3] #the core aesthetic
DECREMENT = [-4, -2, -2, -4]

UNI1 = UniverseProfile(
    SERIAL_U1,
    368,
    28
)
UNI2 = UniverseProfile(
    SERIAL_U2,
    513,
    0
)
PLAYER_SETTINGS = OpenCVPlayerSettings(
    [UNI1, UNI2],
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
    SPEED_COLORS,
    BACKFILL_COLOR,
    BUSY_THRESHOLD_COLOR,
    NIGHT_IDLE_COLOR,
    INCREMENT,
    DECREMENT
)

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
        proc.stop()

spinupplayer()
COUNT = 0

try:
    while True:
        COUNT += 1
except (KeyboardInterrupt, SystemExit):
    print 'Interrupted!'
    time.sleep(1)
    stopworkerthreads()
