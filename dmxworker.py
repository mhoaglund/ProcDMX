import serial, sys, math, time, Queue, copy, multiprocessing, schedule
from threading import Thread

HAS_FRAMES = False
DMXOPEN = chr(126)
DMXCLOSE = chr(231)
DMXINTENSITY=chr(6)+chr(1)+chr(2)				
DMXINIT1= chr(03)+chr(02)+chr(0)+chr(0)+chr(0)
DMXINIT2= chr(10)+chr(02)+chr(0)+chr(0)+chr(0)
DMXFrame1 = [[1,0],[2,0],[3,0],[4,0]]
DMXFrame2 = [[1,255],[2,255],[3,255],[4,255]]
FRAMEDURATION = 2 #easing time from frame to frame, in seconds
EMPTY_FRAME = [0]*512
FPS = 30
frameQueue = Queue.Queue()

class DmxThread(Thread):
	def __init__(self, serialPort, _frameStack):
		super(DmxThread, self).__init__()
		print 'starting worker'
		try:
			self.serial=serial.Serial(serialPort, baudrate=57600)
		except:
			print "Error: could not open Serial Port"
			sys.exit(0)
		self.cont=True
		self.frameStack = _frameStack
		self.serial.write( DMXOPEN+DMXINIT1+DMXCLOSE)
		self.serial.write( DMXOPEN+DMXINIT2+DMXCLOSE)
		self.StopFrame = EMPTY_FRAME
		self.dmxData=[chr(0)]*513   #128 plus "spacer".

	def setChannel(self, chan, _intensity):
		intensity = int(_intensity)
		if chan > 512 : chan = 512
		if chan < 0 : chan = 0
		if intensity > 255 : intensity = 255
		if intensity < 0 : intensity = 0
		self.dmxData[chan] = chr(intensity)
		
	def blackout(self):
		for i in xrange (1, 512, 1):
			self.dmxData[i] = chr(0)
		
	def render(self):
		sdata=''.join(self.dmxData)
		self.serial.write(DMXOPEN+DMXINTENSITY+sdata+DMXCLOSE)

	def run(self):
		self.runFrameStack()

	def stop(self):
		self.frameStack = Queue.Queue() #the meaning and utility of this is debatable. why give the thread this power?
		self.cont = False

	def runFrameStack(self):
		while self.frameStack.empty() == False and self.cont:
			_nextFrame = self.frameStack.get()
			self.easeFrame(_nextFrame)
		self.blackout()
		self.render()

	def nextFrame(self):
		if self.frameStack.empty():
			_nextFrame = EMPTY_FRAME
			self.blackout()
			self.render()
			self.cont = False
                print 'closing serial'
                if self.serial.isOpen() == True:
                    self.serial.close()
		else:
			_nextFrame = self.frameStack.get()
			self.easeFrame(_nextFrame)

	def easeFrame(self, targetFrame):
		deltas = []
		channels = len(targetFrame)
		#get the difference between the starting state and target state
		for i in range(0, channels):
                    #val = (targetFrame[i] - self.StopFrame[i])/(FPS * FRAMEDURATION)
	            #deltas.append(val)
                        diff = (targetFrame[i] - self.StopFrame[i])
                        if abs(diff) > 0: 
                            rate = float(FPS*FRAMEDURATION)
			    val = (targetFrame[i] - self.StopFrame[i])/rate
			    deltas.append(val)
                        else:
                            deltas.append(0)
		x = 0
		sleeptime = 1.0/FPS
		while x<(FPS * FRAMEDURATION):
			for j in range(0, channels):
				frameValue = int(self.StopFrame[j] + (x*deltas[j]))
				#print("setting intensity", frameValue)
				self.setChannel(j+1, frameValue)
			self.render()
			time.sleep(sleeptime)
			x+=1
		self.StopFrame = targetFrame
