import uuid
from random import randint

class SimpleContour(object):
    """
        Simple deal for tracking what we need from opencv contours.
    """
    def __init__(self, _index):
        self.spatialindex = _index

color_by_id = {}
def merge_up_clusters(previous, current, threshold, color_dict):
    """
        Persist an attribute from one set of objects to another in place,
        based on similarity in another attribute.
    """
    kept = {}
    contout = []
    for item in current:
        nearest = min(
            range(1, len(previous)),
            key=lambda i: abs(previous[i]['avg'] - current[item]['avg'])
            )
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

def color_cluster(iterable, threshhold, colors):
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
                'color': colors[randint(0, (len(colors)-1))]
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
            'color': colors[randint(0, (len(colors)-1))]
        }
        yield group_obj

def constructVariableInteractiveGoalFrame(_status, _cdcs):
    """Build an end-goal frame for the run loop to work toward"""
    _temp = colors.base*136
    _fixturehue = colors.activations[3]
    _startchannel = 0

    #For each fixture...
    for x in range(0, 136):
        #TODO grab a color for this fixture somehow.
        _color = _fixturehue
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

objects = [
    SimpleContour(22),
    SimpleContour(68),
    SimpleContour(74),
    SimpleContour(120),
    SimpleContour(12),
    SimpleContour(11),
    SimpleContour(119),
    SimpleContour(51),
    SimpleContour(60),
    SimpleContour(72),
    SimpleContour(84),
    SimpleContour(96)
]

prev_objects = [
    SimpleContour(11),
    SimpleContour(18),
    SimpleContour(30),
    SimpleContour(105),
    SimpleContour(115),
    SimpleContour(108),
    SimpleContour(60),
    SimpleContour(58),
    SimpleContour(90)
]

ACTIVATION_COLORS = [
    [130, 0, 255, 0],
    [225, 0, 0, 0],
    [150, 150, 0, 0],
    [0, 255, 0, 0],
    [0, 150, 150, 0],
    [0, 0, 255, 0],
    [0, 0, 150, 150],
    [0, 0, 0, 255],
    [150, 0, 0, 150]
    ]

thresh = 14
def findContinuity():
    prev_clustered = dict(enumerate(color_cluster(prev_objects, thresh, ACTIVATION_COLORS), 1))
    clustered = dict(enumerate(color_cluster(objects, thresh, ACTIVATION_COLORS), 1))
    for key in clustered:
        print("Group {}:".format(key))
        print("Avg: {}".format(clustered[key]['avg']))
        for cnt in clustered[key]['cluster']:
            print("C at {}".format(cnt.spatialindex)) 
    return merge_up_clusters(prev_clustered, clustered, thresh, self.color_by_id)

findContinuity()