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
        self.lights = 256
        self.channels_per_light = 4
        self.initUI()

    def initUI(self):
        self.parent.title("DMX emulator display")
        self.widgets = []
        for x in range(0, self.lights):
            cell = Frame(self, width=6, height=24, bg="red")
            self.widgets.append(cell)
            cell.grid(row=0, column=x)
        self.pack()

    def clamped(self, value):
        if value > 255:
            return 255
        if value < 1:
            return 1
        else:
            return value

    def renderDMX(self, dmxPayload):
        """Take in arbitrarily sized dmx payload and render it on the emulator"""
        _light = 0
        #light_packets = [dmxPayload[i:i + self.channels_per_light] for i in range(0, len(dmxPayload), 1)]
        light_packets = zip(*(iter(dmxPayload),) * 4)
        for channelset in light_packets:
            #what do we do with amber?
            (amber_rmod, amber_gmod, amber_bmod) = ord(channelset[3])/4, ord(channelset[3])/8, ord(channelset[3])/16
            mycolor = '#%02x%02x%02x' % (
                self.clamped(ord(channelset[0])+amber_rmod),
                self.clamped(ord(channelset[1])+amber_gmod),
                self.clamped(ord(channelset[2])+amber_bmod)
                )
            if _light < len(self.widgets):
                self.widgets[_light].configure(bg=mycolor)
            _light += 1
        self.pack()

# root=Tk()
# app = Emulator(root)
# dmxframe = [125,125,125,125]*136
# if __name__ == '__main__':
#     while True:
#         app.renderDMX(dmxframe)
#         root.update()
#         time.sleep(0.001)