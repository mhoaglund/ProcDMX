"""Helper objects for configuring the player"""

#TODO: the player settings family of objects is indistinct in overall intent and use.
#Things that shouldnt be generalized are, and vice versa. Could use a refactor.
class ColorSettings(object):
    """
        Bucket for colors.
        Args:
        Base Color (int[4])
        Dimmed Color (int[4])
        Peak Color (int[4])
        Busy Color (int[4])
        Night Color (int[4])
        Increment (int[4])
        Decrement (int[4])
    """
    def __init__(self, _base, _dimmed, _peak, _busy, _night, _inc, _dec):
        self.base = _base
        self.dimmed = _dimmed
        self.peak = _peak
        self.busy = _busy
        self.night = _night
        self.increment = _inc
        self.decrement = _dec

class SensorArrayPlayerSettings(object):
    """
        Plays lighting choreography from an array of binary sensor data.
        Allows for edge gating and thresholds and warmup/cooldown times.
        Args:
        Serialport (string)
        Delay (double, portion of a second),
        Edge Gate Inputs (int[] sensor channels that open edge gates)
        InternAddress (int, IIC address of input device),
        ArraySize (int),
        Decay (int, minimum number of frames which run in response to a hit),
        Light Count (int, number of lights in show),
        Channels per light (int, gen. 3 or 4),
        Map (dictionary matching inputs to channel sets)
    """
    def __init__(self, _serialport, _delay, _gates, _internaddr,
                 _arraysize, _decay, _lightcount, _channelsper, _map
                ):

        self.serialport = _serialport
        self.delay = _delay
        self.edgegates = _gates
        self.internaddr = _internaddr
        self.arraysize = _arraysize
        self.decay = _decay
        self.lights = _lightcount
        self.channelsperlight = _channelsper
        self.rendermap = _map

class OpenCVPlayerSettings(object):
    """
        Light player that takes contour data from OpenCV and plays choreography dynamically from it.
        Args:
        Serialport (string),
        Decay (int, minimum number of frames which run in response to a hit),
        Light Count (int, number of lights in show),
        Channels per light (int, gen. 3 or 4),
        Data Queue (queue for contour locations from OpenCV),
        Job Queue (queue for any directives that aren't data)
    """
    def __init__(self, _serialport, _decay, _lightcount, _channelsper, _dataqueue, _jobqueue
                ):

        self.serialport = _serialport
        self.decay = _decay
        self.lights = _lightcount
        self.channelsperlight = _channelsper
        self.dataqueue = _dataqueue
        self.jobqueue = _jobqueue

class CVInputSettings(object):
    """
        Settings object for setting a stream and tracking motion.
        _stream_host (string, address of stream to open)
        _resize (target size for resizing frames)
        _thresh_sensitivity (threshold value for the delta that removes the background)
        _blur_radius (self exp)
    """
    def __init__(self, _stream_host, _resize, _thresh_sensitivity, _blur_radius):
        self.stream_host = _stream_host
        self.resize = _resize
        self.thresh_sensitivity = _thresh_sensitivity
        self.blur_radius = _blur_radius

class PlayerJob(object):
    """
        _job (string, ex. 'resize' or 'adjust' etc.)
        _data (payload pertaining to chosen job)
    """
    def __init__(self, _job, _payload):
        self.job = _job
        self.payload = _payload
