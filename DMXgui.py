"""
ZetCode Tkinter tutorial

This script shows a simple window
on the screen.

Author: Jan Bodnar
Last modified: November 2015
Website: www.zetcode.com
"""

import time
from Tkinter import Tk, W, E
from Tkinter import *
from ttk import Entry
from random import *

class Example(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent
        self.cells = 136
        self.initUI()

    def initUI(self):
        self.parent.title("Simple")
        self.mylist = []
        for x in range(0, self.cells):
            cell = Frame(self, width=8, height=24, bg="red")
            self.mylist.append(cell)
            cell.grid(row=0, column=x)
        self.pack()

    def updateUI(self, framenumber):
        for _widget in self.mylist:
            mycolor = '#%02x%02x%02x' % (randint(1, 255), randint(1, 255), framenumber)  # set your favourite rgb color
            _widget.configure(bg = mycolor)
        self.pack()

root=Tk()
app = Example(root)
currframe = 0
if __name__ == '__main__':
    while True:
        app.updateUI(currframe)
        root.update()
        time.sleep(0.001)
        if currframe < 254:
            currframe += 1
        else:
            currframe = 0