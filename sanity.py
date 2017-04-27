STRIPES = []
_res = []
_a = 0.006592   
_b = -0.8578
_c = 28.85
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
#print STRIPES

print '----'

for x in range(-4, 0):
    print x
    print '...and', x+4
print '---'
for x in range(0, 4):
    print x
print '---'
for x in range(0, 136):
    print x
print '---'
y = 4
print y-4

if 0 -4 < 0:
    print 'yes'