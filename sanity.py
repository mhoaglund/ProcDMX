STRIPES = []
_res = []
_a = 0.003170
_b = -0.535
_c = 23.43
for f in range(0, 136/2):
    size = (_a * (f * f)) + (_b * f) + _c
    if size < 1:
        size = 1
    _res.append(int(size))
print "Sum:", sum(_res) #This sum shouldn't exceed STREAM_WIDTH
_running = 0
for m in range(0, 136/2):
    _start = _running
    _end = _running+_res[m]
    _running += _res[m]
    STRIPES.append((_start, _end))
print STRIPES

print '----'
