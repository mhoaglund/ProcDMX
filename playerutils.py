"""Helper objects for configuring the player"""

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
        AltDecrement (int[4])
    """
    def __init__(self, _base, _dimmed, _peak, _busy, _night, _inc, _dec, _altdec):
        self.base = _base
        self.dimmed = _dimmed
        self.peak = _peak
        self.busy = _busy
        self.night = _night
        self.increment = _inc
        self.decrement = _dec
        self.altdecrement = _altdec

class PlayerSettings(object):
    """
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
