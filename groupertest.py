import uuid

class SimpleContour(object):
    """
        Simple deal for tracking what we need from opencv contours.
    """
    def __init__(self, _index):
        self.spatialindex = _index

def merge_up_clusters(previous, current, threshold):
    """
        Persist an attribute from one set of objects to another,
        based on similarity in another attribute.
    """
    for item in current:
        nearest = min(
            range(1, len(previous)),
            key=lambda i: abs(previous[i]['avg'] - current[item]['avg'])
            )
        if abs(previous[nearest]['avg'] - current[item]['avg']) < threshold:
            print("Persisting ID: {}".format(previous[nearest]['id']))
            current[item]['id'] = previous[nearest]['id']
        else:
            continue
            #merge color here or do a dict lookup for colors?

def cluster(iterable, threshhold):
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
                'id': uuid.uuid4().hex
            }
            yield group_obj
            group = [item]
        prev = item
    if group:
        group_avg = sum(c.spatialindex for c in group)/len(group)
        group_obj = {
            'cluster': group,
            'avg': group_avg,
            'id': uuid.uuid4().hex
        }
        yield group_obj

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

thresh = 14
def findContinuity():
    prev_clustered = dict(enumerate(cluster(prev_objects, thresh), 1))
    clustered = dict(enumerate(cluster(objects, thresh), 1))
    for key in clustered:
        print("Group {}:".format(key))
        print("Avg: {}".format(clustered[key]['avg']))
        for cnt in clustered[key]['cluster']:
            print("C at ", cnt.spatialindex) 
    merge_up_clusters(prev_clustered, clustered, thresh)

findContinuity()