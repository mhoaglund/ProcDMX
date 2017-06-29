"""Helper objects for configuring the player"""

#TODO: clean up the docstring, it's totally wrong
class ColorSettings(object):
    """
        Bucket for colors.
        Args:
        Base Color (int[4])
        Dimmed Color (int[4])
        Peak Color (int[4])
        Activation Colors ([int[4]])
        Backfill Color (int[4])
        Busy Color (int[4])
        Night Color (int[4])
        Increment (int[4])
        Decrement (int[4])
    """
    def __init__(self, _base, _dimmed, _peak, _activation_colors, _backfill, _busy, _night, _inc, _dec):
        self.base = _base
        self.dimmed = _dimmed
        self.peak = _peak
        self.activations = _activation_colors
        self.backfill = _backfill
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
        Universes [UniverseProfile]
        Decay (int, downward step for reducing intensity toward goal),
        Attack (int, upward step for reducing intensity toward goal),
        Light Count (int, number of lights in show),
        Channels per light (int, gen. 3 or 4),
        Data Queue (queue for contour locations from OpenCV),
        Job Queue (queue for any directives that aren't data)
    """
    def __init__(self, _universes, _decay, _attack, _sustain, _lightcount, _channelsper, _dataqueue, _jobqueue
                ):

        self.universes = _universes
        self.decay = _decay
        self.attack = _attack
        self.sustain = _sustain
        self.lights = _lightcount
        self.channelsperlight = _channelsper
        self.dataqueue = _dataqueue
        self.jobqueue = _jobqueue

class CVInputSettings(object):
    """
        Settings object for setting a stream and tracking motion.
        _stream_host (string, address of stream to open)
        _stream_id (internal distinction)
        _resize (target size for resizing frames)
        _thresh_sensitivity (threshold value for the delta that removes the background)
        _accumulation (float, alpha for background segmentation accumulation algo)
        _blur_radius (self exp)
        _maskc (mask coordinates, array of proportional coords expressed as tuples of floats)
        _contour_queue (Queue for outputting detected contours)
        _job_queue (Queue for responding to directives from the main process)
        _quadratics (the abc values for a parabola, used to map out the space the cam sees)
        _shouldflip (kind of a bullshit thing- should we reverse x vals in the stream?)
    """
    def __init__(self, _stream_location, _stream_id, _resize, _thresh_op, _thresh_sensitivity, _detectionMinimum, _accumulation, _blur_radius, _maskc, _contour_queue, _job_queue, _waypoints, _quadratics, _shouldflip):
        self.stream_location = _stream_location
        self.stream_id = _stream_id
        self.resize = _resize
        self.thresh_op = _thresh_op
        self.thresh_sensitivity = _thresh_sensitivity
        self.detectionMinimum = _detectionMinimum
        self.accumulation = _accumulation
        self.blur_radius = _blur_radius
        self.maskc = _maskc
        self.contour_queue = _contour_queue
        self.job_queue = _job_queue
        self.waypoints = _waypoints
        self.quadratics = _quadratics
        self.shouldflip = _shouldflip

class PlayerJob(object):
    """
        _job (string, ex. 'resize' or 'adjust' etc.)
        _data (payload pertaining to chosen job)
    """
    def __init__(self, _job, _payload, _frompid):
        self.frompid = _frompid
        self.job = _job
        self.payload = _payload

class CalcdContour(object):
    """
        Simple deal for tracking what we need from opencv contours.
    """
    def __init__(self, _x, _y, _h, _w, _from):
        self.x = _x
        self.detectedby = _from
        self.pos = (_x, _y)
        self.a_ratio = int(_w/_h) #remember, the camera is sideways. using the long resolution for tracking.
        self.spd = 0
        self.spatialindex = 0
        self.center = (_x+(_w/2), _y+(_h/2))
        self.area = 0
        self.isassociated = False
        self.color = [0,0,0,0] #sorry forever! this doesn't get used until we get to the player.
        if self.a_ratio <= 2:
            self.spd = 0
        if self.a_ratio > 2 and self.a_ratio <= 3:
            self.spd = 1
        if self.a_ratio > 3:
            self.spd = 2

class UniverseProfile(object):
    """Simple container to keep serial devices and universes straight"""
    def __init__(self, _serialport, _usingchannels, _backfillchannels):
        self.serialport = _serialport
        self.serial = ()
        self.myDMXdata = [chr(0)]*513
        self.interactivechannels = _usingchannels
        self.backfillchannels = _backfillchannels
