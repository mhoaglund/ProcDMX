import uuid

class SimpleContour(object):
    """
        Simple deal for tracking what we need from opencv contours.
    """
    def __init__(self, _index):
        self.spatialindex = _index

#Could call this "merge_down_IDs"
def cluster2d(previous, current, threshold):
    """
        Generator that kind of zips two iterables...
    """
    print("Merging...")
    for item in current:
        try:
            nearest = min(range(len(previous)), key=lambda i: abs(previous[i]['avg'] - current[item]['avg']) < threshold)
        except KeyError:
            print("Whoops")
            continue
        print("Group {}:".format(item))
        print("Avg: {}".format(current[item]['avg'])) 
        print("Prev Neighbor Avg: {}".format(nearest['avg']))

#TODO, include determination of average index across members of clusters
def cluster(iterable, threshhold):
    prev = None
    group = []
    for item in iterable:
        if not prev or abs(item.spatialindex - prev.spatialindex) <= threshhold:
            group.append(item)
        else:
            group_avg = sum(c.spatialindex for c in group)/len(group)
            #set an ID, set a color
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
        #set an ID, set a color
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
    SimpleContour(60)
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


#TODO: use the averages as keys to do the next dimension of clustering.
#TODO: make it iterable this time as a challenge
def findContinuity():
    prev_clustered = dict(enumerate(cluster(prev_objects, 9), 1))
    clustered = dict(enumerate(cluster(objects, 9), 1))
    cluster2d(prev_clustered, clustered, 10)
    # for key in clustered:
    #     print("Group {}:".format(key))
    #     print("Avg: {}".format(clustered[key]['avg']))
    #     for cnt in clustered[key]['cluster']:
    #         print("C at ", cnt.spatialindex)     

findContinuity()