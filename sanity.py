# STRIPES = []
# _res = []
# _a = 0.003170
# _b = -0.535
# _c = 23.43
# for f in range(0, 136/2):
#     size = (_a * (f * f)) + (_b * f) + _c
#     if size < 1:
#         size = 1
#     _res.append(int(size))
# print "Sum:", sum(_res) #This sum shouldn't exceed STREAM_WIDTH
# _running = 0
# for m in range(0, 136/2):
#     _start = _running
#     _end = _running+_res[m]
#     _running += _res[m]
#     STRIPES.append((_start, _end))
# print STRIPES

print '----'
newStripes = []
def gps(_start, _end, _a, _b, _c):
    """Given a desired set of fixtures and variables for a quadratic equation, generate a set of pixel segments"""
    _result = []
    _deltas = []
    _prev = 0
    for f in range(_start, _end):
        size = (_a * (f * f)) + (_b * f) + _c
        _result.append(int(size))
        if f > _start:
            if int(size) > _prev:
                _deltas.append(int(size) - _prev)
            if int(size) < _prev:
                _deltas.append(_prev - int(size))
            _prev = int(size)
        else:
            _prev = int(size)
    #print 'From ', _start, ' To ', _end, ': '
    #print _result
    #print _deltas
    #print len(_result)
    #print "Sum:", sum(_res) #This sum shouldn't exceed STREAM_WIDTH
    return _result

def printDeltas(_arr):
    _deltas = []
    _prev = 0
    for f in range(0, len(_arr)):
        if f > 0:
            if _arr[f] > _prev:
                _deltas.append(_arr[f] - _prev)
            if _arr[f] < _prev:
                _deltas.append(_prev - _arr[f])
            _prev = _arr[f]
        else:
            _prev = _arr[f]
    print _deltas

def lps(_start, _inc, _passes):
    """
        Given a starting point, subtract a number from it x times and return an array of those results
    """
    _result = []
    for x in range (1, _passes):
        _result.append(_start + (_inc * x))
    print _result
    return _result

def stripeify(_arr):
    """Loop over array, pairing up values"""
    _running = 0
    STRIPES = []
    for m in range(1, len(_arr)):
        STRIPES.append((_arr[m-1], _arr[m]))
    print 'Generated Stripes: ', STRIPES
    return STRIPES


#newStripes = gps(0,28, -0.0259, -1.026, 665.1) + gps(29, 68, -0.2014, 9.528, 507.1) + lps(241, -34, 8) + gps(74, 99, -0.3958, 81.33, -3600) + gps(100,136, -0.04051, 11.70, -189.8)
#print newStripes
#print len(newStripes)

# print 'CITY: ---'
# cityStripes = gps(0,28, -0.0259, -1.026, 665.1) + gps(29, 68, -0.2014, 9.528, 507.1) + lps(241, -30, 7) + [30, 0]
# print cityStripes
# cityStripes = stripeify(cityStripes[::-1])
# print len(cityStripes)
# print ''
# print 'RIVER: ---'
# riverStripes = [207] + gps(73, 99, -0.3958, 81.33, -3600) + gps(100,136, -0.04051, 11.70, -189.8)
# print riverStripes
# riverStripes = stripeify(riverStripes)
# print len(riverStripes)


def computeModifier(_input):
    """
        The location algorithms just need help being right.
    """
    _result = 0
    _salt = 1.0-((660.0/_input)/10)
    print _salt
    return _salt

computeModifier(685)
computeModifier(650)
computeModifier(600)
computeModifier(500)
computeModifier(200)
