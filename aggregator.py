import sys, math, time, Queue, copy, schedule
from threading import Thread
from operator import add
LastAggregatedFrameId = ''

#this object's job is to mind a queue of perpetually-renewed arrays, aggregating them into single one when they pile up.
#it's like tetris where every line wins
#this impo is dedicated entirely to situations where data arrives at its own pace, forcing us to work asynchronously with it
class AggregatorThread(Thread):
    def __init__(self,_queue):
        super(AggregatorThread, self).__init__() #TODO understand this line
        self.cont = True
        self.MyQueue = _queue

    def run(self):
        while self.cont:
            while self.MyQueue.empty() == False
                self.SquishModifierStack()
        #any parting stuff here if the thread exits?

    #there are some optimization tasks in here and possible race condition.
    #TODO add a maximum number of squishes to perform in case lots of stuff is coming in
    def SquishModifierStack(self):
        temp = []
        for layer in iter(self.MyQueue.get, None):
            if len(temp) < 1:
               temp.append(layer)
            else:
               new = map(add, temp, layer) #TODO update this to average instead of add
               temp = new
        self.MyQueue.put(temp)
        time.sleep(30)

        