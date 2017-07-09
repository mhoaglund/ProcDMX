import sys
import serial
import time
import logging
import math
import uuid
import random
from multiprocessing import Process, Queue
from random import randint
from operator import add

DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY = chr(6)+chr(1)+chr(2)
DMXINIT1 = chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2 = chr(10)+chr(02)+chr(0)+chr(0)+chr(0)

class ImmediatePlayer(Process):
    """A Process which catches packets of contour data from OpenCV and associates their locations to DMX output channels.
        Args:
            Player Settings (playerutils.OpenCVPlayerSettings),
            Color Settings (playerutils.ColorSettings)
    """
    def __init__(self, _playersettings, _colorsettings):
        super(ImmediatePlayer, self).__init__()
        print 'starting worker'
        self.isHardwareConnected = True #debug flag for working without the dmx harness
        self.dmxData = []
        self.cont = True
        self.universes = _playersettings.universes
        self.dmxDataOne = [chr(0)]* 513
        self.dmxDataTwo = [chr(0)]* 513
        try:
            self.serialOne = serial.Serial('/dev/ttyUSB0', baudrate=57600)
            self.serialTwo = serial.Serial('/dev/ttyUSB1', baudrate=57600)
        except:
            print "Error: could not open Serial port"
            logging.info("An issue has occurred with one of the Serial Ports. Running in dummy mode with no serial output.")
            self.isHardwareConnected = False
            try:
                from DMXgui import Emulator
                from Tkinter import Tk
                self.root = Tk()
                self.gui = Emulator(self.root)
            except ImportError:
			    print "Missing GUI library..."
			    logging.info("Tkinter is missing...")
			    self.cont = False

        self.current_active_color = 0
        self.quietframes = 0
        self.maxquietframes = 140
        self.shouldUpdateColor = False
        self.verbose = True
        self.dataqueue = _playersettings.dataqueue
        self.jobqueue = _playersettings.jobqueue
        self.colors = _colorsettings
        self.channelsinuse = _playersettings.lights * _playersettings.channelsperlight
        self.lightsinuse = _playersettings.lights
        self.settings = _playersettings

        self.baseframe = self.colors.base*_playersettings.lights
        self.dimframe = self.colors.dimmed*_playersettings.lights
        self.peakframe = self.colors.peak*_playersettings.lights
        self.busyframe = self.colors.busy*_playersettings.lights
        self.nightframe = self.colors.night*_playersettings.lights

        self.increment = self.colors.increment
        self.decrement = self.colors.decrement

        self.cont_limit = 12
        self.spacing_limit = 250
        self.color_by_id = {}
        w, h = 4, 136
        self.color_memory = [[0 for x in range(w)] for y in range(h)]
        for arr in self.color_memory:
            arr[0] = self.colors.base[0]
            arr[1] = self.colors.base[1]
            arr[2] = self.colors.base[2]
            arr[3] = self.colors.base[3]
        #Prev Frame and Goal Frame are containers for data pertaining to ALL interactive channels.
        #They get split up for rendering and don't have anything to do with DMX packets.
        self.prev_contours = []
        self.status = [0]*136
        self.prev_frame = self.colors.base*136
        self.goal_frame = self.colors.base*136
        self.heats = [0]*136
        self.sustain = _playersettings.sustain
        self.backfills = self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]+ self.colors.backfill[1]+ self.colors.backfill[0]+ self.colors.backfill[0]
        self.updateActiveColor()
        self.playTowardLatest()

    def setchannelOnOne(self, chan, _intensity):
        """Set intensity on channel"""
        intensity = int(_intensity)
        if chan > 512:
            chan = 512
        if chan < 0:
            chan = 0
        if intensity > 255:
            intensity = 255
        if intensity < 0:
            intensity = 0
        self.dmxDataOne[chan] = chr(intensity)

    def setchannelOnTwo(self, chan, _intensity):
        """Set intensity on channel"""
        intensity = int(_intensity)
        if chan > 512:
            chan = 512
        if chan < 0:
            chan = 0
        if intensity > 255:
            intensity = 255
        if intensity < 0:
            intensity = 0
        self.dmxDataTwo[chan] = chr(intensity)


    def render(self, _payloadOne, _payloadTwo):
        if self.isHardwareConnected:
            sdata = ''.join(self.dmxDataOne)
            self.serialOne.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)
            sdata2 = ''.join(self.dmxDataTwo)
            self.serialTwo.write(DMXOPEN+DMXINTENSITY+sdata2+DMXCLOSE)
        else:
            _payloadTwo.pop(0)
            _payloadTwo.append(chr(0))
            _all = _payloadOne + _payloadTwo
            _all.pop(0)
            self.gui.renderDMX(_all)
            self.root.update()

    def updateActiveColor(self):
        """If we have a period of inactivity, switch the activation color."""
        print "cycling active color"
        if self.current_active_color == len(self.colors.activations)-1:
            self.current_active_color = 0
        else:
            self.current_active_color += 1
        #clearing plastic color memory
        for arr in self.color_memory:
            arr[0] = self.colors.activations[self.current_active_color][0]
            arr[1] = self.colors.activations[self.current_active_color][1]
            arr[2] = self.colors.activations[self.current_active_color][2]
            arr[3] = self.colors.activations[self.current_active_color][3]
        self.shouldUpdateColor = False

    def constructInteractiveGoalFrame(self, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        #we have 132 interactive lights (4 per fixture) and some that aren't.
        #each light has 4 channels, so we have a total of 544 channels.
        #building more than one universe worth here, to be divided up later.
        _temp = self.colors.base*136
        _fixturehue = self.colors.activations[self.current_active_color]
        _startchannel = 0
        #for channelheat in range(0,136): #cool all the channels
        #    self.heats[channelheat] -= 1
        for x in range(0, 136):
            if _cdcs[x] > 1:
                #hot spot
                if x > 0:
                    _startchannel = x * 4
                if _startchannel > 4: #conditionally brighten the previous fixture
                    for ch in range(-4, 0):
                        _temp[_startchannel + ch] = _fixturehue[ch+4]
                for ch in range(0, 4):
                    _temp[_startchannel + ch] = _fixturehue[ch]
                if _startchannel + 7 < 544:  #conditionally brighten the next fixture
                    for ch in range(4, 8):
                        _temp[_startchannel + ch] = _fixturehue[ch-4]
        return _temp

    def constructVariableInteractiveGoalFrame(self, _status, _cdcs):
        """Build an end-goal frame for the run loop to work toward"""
        _temp = self.colors.base*136
        _fixturehue = self.colors.activations[self.current_active_color]
        _startchannel = 0

        #For each fixture...
        for x in range(0, 136):
            _color = _fixturehue
            contours_at_this_fixture = [cnt for cnt in _cdcs if cnt['spatialindex'] == x]
            if len(contours_at_this_fixture) > 0:
                _tempcolor = [0, 0, 0, 0]
                for c in contours_at_this_fixture:
                    for channel in range(0, len(c['color'])):
                        if c['color'][channel] > _tempcolor[channel]:
                            _tempcolor[channel] = c['color'][channel]
                _color = _tempcolor
                #self.color_memory[x][0] = _tempcolor[0]
                #self.color_memory[x][1] = _tempcolor[1]
                #self.color_memory[x][2] = _tempcolor[2]
                #self.color_memory[x][3] = _tempcolor[3]

            if _status[x] > 1:
                if x > 0:
                    _startchannel = x * 4
                if _startchannel > 4: #conditionally brighten the previous fixture
                    for ch in range(-4, 0):
                        _temp[_startchannel + ch] = _color[ch+4]
                for ch in range(0, 4):
                    _temp[_startchannel + ch] = _color[ch]
                if _startchannel + 7 < 544:  #conditionally brighten the next fixture
                    for ch in range(4, 8):
                        _temp[_startchannel + ch] = _color[ch-4]

        return _temp


    def run(self):
        while self.cont:
            if not self.dataqueue.empty():
                Contours = self.dataqueue.get()
                self.compileLatestContours(Contours)
                if len(Contours) < 2:
                    if self.quietframes > self.maxquietframes:
                        if self.shouldUpdateColor:
                            self.updateActiveColor()
                        self.quietframes = 0
                    else:
                        self.quietframes += 1
                else:
                    self.quietframes = 0
                    self.shouldUpdateColor = True
            self.playTowardLatest()

    #TODO figure out if this spacing_limit is reasonable.
    #Narrative:
    #When a new contour appears, check for any close-by contours in the previous frame.
    #The idea is those contours might have been created by the same object in space.
    #If there are previous-frame neighbors, that means the current contour is part of a group.
    #When the current contour is added to the group, it checks for any existing color held by
    #Associated contours in that group. It prioritizes finding a color from an associated contour,
    #as opposed to an unassociated one.
    #TODO: assign IDs to groups of contours and just color the IDs. Generate new color
    #for new ID.
    def findContinuity(self, contours):
        """
            Given a set of new contours, compare to previous set and
            try to identify nearest neighbors.
        """
        if len(contours) > 0:
            indices = len(contours)
            for cnt in range(0, indices):
                _thisnew = contours[cnt]
                _thisnew.color = self.colors.activations[
                    randint(0, (len(self.colors.activations)-1))]
                if not _thisnew.isassociated:
                #look up contours in previous frame which were reasonably close.
                    _prev_indices = [i for i in range(len(self.prev_contours)) if (
                        abs(self.prev_contours[i].spatialindex - _thisnew.spatialindex) < self.cont_limit)]
                    _curr_neighbor_indices = [i for i in range(len(contours)) if(
                        abs(contours[i].spatialindex - _thisnew.spatialindex) < self.cont_limit)]
                    if len(_prev_indices) > 0:
                        _thisnew.isassociated = True
                        for prev_neighbor in _prev_indices:
                            _thisnew.color = self.prev_contours[prev_neighbor].color
                            #try to get an associated color from last frame
                            if self.prev_contours[prev_neighbor].isassociated:
                                for current_neighbor in _curr_neighbor_indices:
                                    contours[current_neighbor].color = self.prev_contours[prev_neighbor].color
                                    contours[current_neighbor].isassociated = True
                                continue
                    else:
                        if len(_curr_neighbor_indices) > 0:
                            for current_neighbor in _curr_neighbor_indices:
                                contours[current_neighbor].color = _thisnew.color
                else: #this is weird, maybe not quite right
                    _thisnew.color = self.color_memory[cnt]

        self.prev_contours = contours

    def merge_up_clusters(self, previous, current, threshold, color_dict):
        """
            Persist an attribute from one set of objects to another in place,
            based on similarity in another attribute.
        """
        kept = {}
        contout = []
        for item in current:
            try:
                nearest = min(
                    range(1, len(previous)+1),
                    key=lambda i: abs(previous[i]['avg'] - current[item]['avg'])
                    )
            except ValueError:
                continue
            if abs(previous[nearest]['avg'] - current[item]['avg']) < threshold:
                print "Persisting ID: {}".format(previous[nearest]['id'])
                current[item]['id'] = previous[nearest]['id']
                try:
                    current[item]['color'] = color_dict[current[item]['id']]
                except KeyError:
                    current[item]['color'] = previous[nearest]['color']
                    kept[previous[nearest]['id']] = previous[nearest]['color']
            for contour in current[item]['cluster']:
                contout.append(
                    {'spatialindex':contour.spatialindex,
                    'color': current[item]['color']}
                    )

        color_dict = kept
        return contout

    def color_cluster(self, iterable, threshhold):
        """
            Given a set of contours, cluster them into groups using a distance threshold.
        """
        prev = None
        group = []
        for item in iterable:
            if not prev or abs(item.spatialindex - prev.spatialindex) <= threshhold:
                group.append(item)
            else:
                group_avg = sum(c.spatialindex for c in group)/len(group)
                group_obj = {
                    'cluster': group,
                    'avg': group_avg,
                    'id': uuid.uuid4().hex,
                    'color': self.colors.activations[randint(0, (len(self.colors.activations)-1))]
                }
                yield group_obj
                group = [item]
            prev = item
        if group:
            group_avg = sum(c.spatialindex for c in group)/len(group)
            group_obj = {
                'cluster': group,
                'avg': group_avg,
                'id': uuid.uuid4().hex,
                'color': self.colors.activations[randint(0, (len(self.colors.activations)-1))]
            }
            yield group_obj
 
    def stop(self):
        print 'Terminating...'
        self.cont = False
        super(ImmediatePlayer, self).terminate()

    def compileLatestContours(self, _contours):
        """When a set of contours comes in, build a goal frame out of it."""
        for y in range(0, 136):
            self.status[y] -= 1
        for x in range(0, len(_contours)):
            self.status[_contours[x].spatialindex] = 100
        self.status[0] = self.status[6]
        self.status[1] = self.status[6]
        self.status[2] = self.status[7]
        self.status[3] = self.status[8]
        #self.goal_frame = self.constructInteractiveGoalFrame(self.status)
        self.goal_frame = self.constructVariableInteractiveGoalFrame(
            self.status,
            self.merge_up_clusters(
                dict(enumerate(self.color_cluster(self.prev_contours, self.cont_limit), 1)),
                dict(enumerate(self.color_cluster(_contours, self.cont_limit), 1)),
                self.cont_limit,
                self.color_by_id)
            )
        self.prev_contours = _contours

    def playTowardLatest(self):
        """Always pushing every channel toward where it needs to go
           Loop over active channels, seeing which way we need to change the intensity
        """
        _actual = self.prev_frame
        for index in range(0, 544):
            _thiscurr = self.prev_frame[index]
            _thisdesired = self.goal_frame[index]
            if _thiscurr == _thisdesired:
                continue
            new = 0
            if _thiscurr > _thisdesired:
                if _thiscurr - self.settings.decay < _thisdesired:
                    new = _thisdesired
                else:
                    new = _thiscurr - self.settings.decay
            if _thiscurr < _thisdesired:
                if _thiscurr + self.settings.attack > _thisdesired:
                    new = _thisdesired
                else:
                    new = _thiscurr + self.settings.attack
            _actual[index] = new

        uni1channels = _actual[:368]
        uni1channels = uni1channels + self.backfills
        for x in range(1, len(uni1channels), 1):
            self.setchannelOnOne(x, uni1channels[x-1])

        uni2channels = _actual[368:]
        uni2channels.append(135)
        for y in range(1, len(uni2channels), 1):
            self.setchannelOnTwo(y, uni2channels[y-1])

        self.prev_frame = _actual
        self.render(self.dmxDataOne, self.dmxDataTwo)
        time.sleep(0.01) #100fps is probably good
