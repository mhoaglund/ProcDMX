"""
ZetCode Tkinter tutorial

This script shows a simple window
on the screen.

Author: Jan Bodnar
Last modified: November 2015
Website: www.zetcode.com
"""

import time
from Tkinter import Tk, W, E, Frame
from random import randint

class Emulator(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        self.lights = 136
        self.channels_per_light = 4
        self.initUI()

    def initUI(self):
        self.parent.title("Simple")
        self.widgets = []
        for x in range(0, self.lights):
            cell = Frame(self, width=8, height=24, bg="red")
            self.widgets.append(cell)
            cell.grid(row=0, column=x)
        self.pack()

    def renderDMX(self, dmxPayload):
        """Take in arbitrarily sized dmx payload and render it on the emulator"""
        _light = 0
        light_packets = [dmxPayload[i:i + self.channels_per_light] for i in range(0, len(dmxPayload), self.channels_per_light)]
        for channelset in light_packets:
            #what do we do with amber?
            mycolor = '#%02x%02x%02x' % (channelset[0], channelset[1], channelset[2])
            self.widgets[_light].configure(bg=mycolor)
            _light += 1
        self.pack()

