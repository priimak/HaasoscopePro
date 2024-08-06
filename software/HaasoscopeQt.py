import numpy as np
import sys, time
import pyqtgraph as pg
from ftd2xx import DeviceError
from pyqtgraph.Qt import QtCore, QtWidgets, loadUiType

# Define main window class from template
WindowTemplate, TemplateBaseClass = loadUiType("Haasoscope.ui")
class MainWindow(TemplateBaseClass):
    def __init__(self):
        TemplateBaseClass.__init__(self)
        
        # Create the main window
        self.ui = WindowTemplate()
        self.ui.setupUi(self)
        self.ui.runButton.clicked.connect(self.dostartstop)
        self.ui.verticalSlider.valueChanged.connect(self.triggerlevelchanged)
        self.ui.horizontalSlider.valueChanged.connect(self.triggerposchanged)
        self.ui.rollingButton.clicked.connect(self.rolling)
        self.ui.singleButton.clicked.connect(self.single)
        self.ui.timeslowButton.clicked.connect(self.timeslow)
        self.ui.timefastButton.clicked.connect(self.timefast)
        self.ui.risingedgeCheck.stateChanged.connect(self.risingfalling)
        self.ui.exttrigCheck.stateChanged.connect(self.exttrig)
        self.ui.totBox.valueChanged.connect(self.tot)
        self.ui.gridCheck.stateChanged.connect(self.grid)
        self.ui.markerCheck.stateChanged.connect(self.marker)
        self.ui.upposButton.clicked.connect(self.uppos)
        self.ui.downposButton.clicked.connect(self.downpos)
        self.ui.chanBox.valueChanged.connect(self.selectchannel)
        self.ui.dacBox.valueChanged.connect(self.setlevel)
        self.ui.acdcCheck.stateChanged.connect(self.setacdc)
        self.ui.gainCheck.stateChanged.connect(self.setgain)
        self.ui.actionOutput_clk_left.triggered.connect(self.actionOutput_clk_left)
        self.ui.chanonCheck.stateChanged.connect(self.chanon)
        self.ui.trigchanonCheck.stateChanged.connect(self.trigchanon)
        self.ui.drawingCheck.clicked.connect(self.drawing)
        self.db=False
        self.lastTime = time.time()
        self.fps = None
        self.lines = []
        self.otherlines = []
        self.savetofile=False # save scope data to file
        self.doh5=False # use the h5 binary file format
        self.numrecordeventsperfile=1000 # number of events in each file to record before opening new file
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.updateplot)
        self.timer2 = QtCore.QTimer()
        self.timer2.timeout.connect(self.drawtext)
        self.ui.statusBar.showMessage("Hello!")
        self.ui.plot.setBackground('w')
        self.show()

    def selectchannel(self):
        self.selectedchannel=self.ui.chanBox.value()
        self.ui.dacBox.setValue(self.chanlevel[self.selectedchannel].astype(int))
        if self.acdc[self.selectedchannel]:   self.ui.acdcCheck.setCheckState(QtCore.Qt.Unchecked)
        else:   self.ui.acdcCheck.setCheckState(QtCore.Qt.Checked)
        if self.gain[self.selectedchannel]:   self.ui.gainCheck.setCheckState(QtCore.Qt.Unchecked)
        else:   self.ui.gainCheck.setCheckState(QtCore.Qt.Checked)
        if len(self.lines)>0:
            if self.lines[self.selectedchannel].isVisible():   self.ui.chanonCheck.setCheckState(QtCore.Qt.Checked)
            else:   self.ui.chanonCheck.setCheckState(QtCore.Qt.Unchecked)
        if self.trigsactive[self.selectedchannel]:   self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Unchecked)

    def chanon(self):
        if self.ui.chanonCheck.checkState() == QtCore.Qt.Checked:
            self.lines[self.selectedchannel].setVisible(True)
            self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Checked)
        else:
            self.lines[self.selectedchannel].setVisible(False)
            self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Unchecked)

    def trigchanon(self):
        if self.ui.trigchanonCheck.checkState() == QtCore.Qt.Checked:
            if not self.trigsactive[self.selectedchannel]: self.toggletriggerchan(self.selectedchannel)
        else:
            if self.trigsactive[self.selectedchannel]: self.toggletriggerchan(self.selectedchannel)

    def setacdc(self):
        if self.ui.acdcCheck.checkState() == QtCore.Qt.Checked: #ac coupled
            if self.acdc[self.selectedchannel]:
                self.setacdc()
        if self.ui.acdcCheck.checkState() == QtCore.Qt.Unchecked: #dc coupled
            if not self.acdc[self.selectedchannel]:
                self.setacdc()

    def setgain(self):
        if self.ui.gainCheck.checkState() == QtCore.Qt.Checked: #x10
            if self.gain[self.selectedchannel]:
                self.tellswitchgain(self.selectedchannel)
        if self.ui.gainCheck.checkState() == QtCore.Qt.Unchecked: #x1
            if not self.gain[self.selectedchannel]:
                self.tellswitchgain(self.selectedchannel)

    def posamount(self):
        amount=10
        modifiers = app.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            amount*=5
        elif modifiers == QtCore.Qt.ControlModifier:
            amount/=10
        return amount
    def uppos(self):
        self.adjustvertical(True,self.posamount())
        self.ui.dacBox.setValue(self.chanlevel[self.selectedchannel].astype(int))
    def downpos(self):
        self.adjustvertical(False,self.posamount())
        self.ui.dacBox.setValue(self.chanlevel[self.selectedchannel].astype(int))
    def setlevel(self):
        if self.chanlevel[self.selectedchannel] != self.ui.dacBox.value():
            self.chanlevel[self.selectedchannel] = self.ui.dacBox.value()
            self.rememberdacvalue()
            self.setdacvalue()

    def wheelEvent(self, event): #QWheelEvent
        if hasattr(event,"delta"):
            if event.delta()>0: self.uppos()
            else: self.downpos()
        elif hasattr(event,"angleDelta"):
            if event.angleDelta()>0: self.uppos()
            else: self.downpos()

    def keyPressEvent(self, event):
        if event.key()==QtCore.Qt.Key_Up: self.uppos()
        if event.key()==QtCore.Qt.Key_Down: self.downpos()
        if event.key()==QtCore.Qt.Key_Left: self.timefast()
        if event.key()==QtCore.Qt.Key_Right: self.timeslow()
        #modifiers = QtWidgets.QApplication.keyboardModifiers()

    def actionOutput_clk_left(self):
        self.toggle_clk_last()

    def exttrig(self):
        self.toggleuseexttrig()

    def tot(self):
        self.triggertimethresh = self.ui.totBox.value()
        self.settriggertime(self.triggertimethresh)

    def grid(self):
        if self.ui.gridCheck.isChecked():
            self.ui.plot.showGrid(x=True, y=True)
        else:
            self.ui.plot.showGrid(x=False, y=False)

    def marker(self):
        if self.ui.markerCheck.isChecked():
            for li in range(self.nlines):
                self.lines[li].setSymbol("o")
                self.lines[li].setSymbolSize(3)
                #self.lines[li].setSymbolPen("black")
                self.lines[li].setSymbolPen(self.linepens[li].color())
                self.lines[li].setSymbolBrush(self.linepens[li].color())
        else:
            for li in range(self.nlines):
                self.lines[li].setSymbol(None)

    paused=False
    def dostartstop(self):
        if self.paused:
            self.timer.start(0)
            self.timer2.start(1000)
            self.paused=False
            self.ui.runButton.setChecked(True)
        else:
            self.timer.stop()
            self.timer2.stop()
            self.paused=True
            self.ui.runButton.setChecked(False)

    def triggerlevelchanged(self,value):
        self.settriggerthresh(value)
        self.hline = (float(  value-128  )*self.yscale/256.)
        self.otherlines[1].setData( [self.min_x, self.max_x], [self.hline, self.hline] ) # horizontal line showing trigger threshold

    downsample=0
    xscale=1
    xscaling=1
    min_y=-5
    max_y=5
    def settriggerpoint(self,point):
        return
    def triggerposchanged(self,value):
        if value>253 or value<3: return
        offset=5.0 # trig to readout delay
        scal = self.num_samples/256.
        point = value*scal + offset/pow(2,self.downsample)
        if self.downsample<0: point = 128*scal + (point-128*scal)*pow(2,self.downsample)
        self.settriggerpoint(int(point))
        self.vline = float(  2*(value-128)/256. *self.xscale /self.xscaling)
        self.otherlines[0].setData( [self.vline, self.vline], [self.min_y, self.max_y] ) # vertical line showing trigger time

    rolltrigger=True
    def tellrolltrig(self, roll):
        return
    def rolling(self):
        self.rolltrigger = not self.rolltrigger
        self.tellrolltrig(self.rolltrigger)
        self.ui.rollingButton.setChecked(self.rolltrigger)
        if self.rolltrigger: self.ui.rollingButton.setText("Rolling/Auto")
        else: self.ui.rollingButton.setText("Normal")

    getone=False
    def single(self):
        self.getone = not self.getone
        self.ui.singleButton.setChecked(self.getone)

    def timefast(self):
        amount=1
        modifiers = app.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            amount*=5
        self.telldownsample(self.downsample-amount)
        self.timechanged()

    def timeslow(self):
        amount=1
        modifiers = app.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            amount*=5
        self.telldownsample(self.downsample+amount)
        self.timechanged()

    def timechanged(self):
        self.ui.plot.setRange(xRange=(self.min_x, self.max_x), yRange=(self.min_y, self.max_y))
        self.ui.plot.setMouseEnabled(x=False,y=False)
        self.ui.plot.setLabel('bottom', self.xlabel)
        self.ui.plot.setLabel('left', self.ylabel)
        self.triggerposchanged(self.ui.horizontalSlider.value())
        self.ui.timebaseBox.setText("downsample "+str(self.downsample))

    def risingfalling(self):
        self.fallingedge=not self.ui.risingedgeCheck.checkState()
        self.settriggertype(self.fallingedge)

    def drawing(self):
        if self.ui.drawingCheck.checkState() == QtCore.Qt.Checked:
            self.dodrawing=True
            print("drawing now",self.dodrawing)
        else:
            self.dodrawing=False
            print("drawing now",self.dodrawing)

    def fastadclineclick(self, curve):
        for li in range(self.nlines):
            if curve is self.lines[li].curve:
                self.ui.chanBox.setValue(li)
                #print "selected curve", li
                modifiers = app.keyboardModifiers()
                if modifiers == QtCore.Qt.ShiftModifier:
                    self.ui.trigchanonCheck.toggle()
                elif modifiers == QtCore.Qt.ControlModifier:
                    self.ui.chanonCheck.toggle()

    num_chan_per_board=1
    num_board=1
    num_logic_inputs=1
    num_samples=1000
    chtext=""
    linepens=[]
    def launch(self):
        self.nlines = self.num_chan_per_board*self.num_board
        if self.db: print("nlines=",self.nlines)
        for li in np.arange(self.nlines):
            c=(0,0,0)
            chan=li%4
            board=int(li/4)
            if self.db: print("chan =",chan,"and board =",board)
            if self.num_board>1:
                if board%4==0: c=(255-0.2*255*chan,0,0)
                if board%4==1: c=(0,255-0.2*255*chan,0)
                if board%4==2: c=(0,0,255-0.2*255*chan)
                if board%4==3: c=(255-0.2*255*chan,0,255-0.2*255*chan)
            else:
                if chan==0: c="r"
                if chan==1: c="g"
                if chan==2: c="b"
                if chan==3: c="m"
            pen = pg.mkPen(color=c) # add linewidth=1.0, alpha=.9
            line = self.ui.plot.plot(pen=pen,name=self.chtext+str(li))
            line.curve.setClickable(True)
            line.curve.sigClicked.connect(self.fastadclineclick)
            self.lines.append(line)
            self.linepens.append(pen)
        self.ui.chanBox.setMaximum(self.num_chan_per_board*self.num_board-1)
        #for the logic analyzer
        for li in np.arange(self.num_logic_inputs):
            line = self.ui.plot.plot(pen=None,name="logic_"+str(li)) # not drawn by default
            self.lines.append(line)
            if li==0: self.logicline1=len(self.lines)-1 # remember index where this first logic line is
        #trigger lines
        self.vline=0.0
        pen = pg.mkPen(color="k",width=1.0,style=QtCore.Qt.DashLine)
        line = self.ui.plot.plot([self.vline, self.vline], [-2.0, 2.0], pen=pen,name="trigger time vert")
        self.otherlines.append(line)
        self.hline = 0.0
        pen = pg.mkPen(color="k",width=1.0,style=QtCore.Qt.DashLine)
        line = self.ui.plot.plot( [-2.0, 2.0], [self.hline, self.hline], pen=pen,name="trigger thresh horiz")
        self.otherlines.append(line)
        self.hline2 = 0.0
        pen = pg.mkPen(color="b",width=1.0,style=QtCore.Qt.DashLine)
        line = self.ui.plot.plot( [-2.0, 2.0], [self.hline2, self.hline2], pen=pen,name="trigger thresh2 horiz") # not drawn by default
        line.setVisible(False)
        self.otherlines.append(line)
        #other stuff
        #self.setxaxis()
        #self.setyaxis()
        #self.timechanged()
        self.ui.totBox.setMaximum(self.num_samples)
        self.ui.plot.showGrid(x=True, y=True)

    def closeEvent(self, event):
        print("Handling closeEvent",event)
        self.timer.stop()
        self.timer2.stop()

    xydata = np.empty([int(num_chan_per_board * num_board), 2, num_samples], dtype=float)

    def updateplot(self):
        self.mainloop()
        if not self.ui.drawingCheck.checkState() == QtCore.Qt.Checked: return
        for li in range(self.nlines):
            self.lines[li].setData(self.xydata[li][0],self.xydata[li][1])
        now = time.time()
        dt = now - self.lastTime + 0.00001
        self.lastTime = now
        if self.fps is None:
            self.fps = 1.0/dt
        else:
            s = np.clip(dt*3., 0, 1)
            self.fps = self.fps * (1-s) + (1.0/dt) * s
        self.ui.plot.setTitle('%0.2f fps' % self.fps)
        app.processEvents()

    nevents=0
    oldnevents=0
    tinterval=100.
    oldtime=time.time()

    def getchannels(self):
        chan=0
        self.xydata[chan][0]=np.array([range(0,1000)])
        self.xydata[chan][1]=np.random.random_sample(size = self.num_samples)

    def chantext(self):
        return "some texttttt"

    def mainloop(self):
        if self.paused: time.sleep(.1)
        else:
            try:
                self.getchannels()
            except DeviceError:
                print("Device error")
                sys.exit(1)
            if self.db: print(time.time()-self.oldtime,"done with evt",self.nevents)
            self.nevents += 1
            if self.nevents-self.oldnevents >= self.tinterval:
                now=time.time()
                elapsedtime=now-self.oldtime
                self.oldtime=now
                lastrate = round(self.tinterval/elapsedtime,2)
                nchan = self.num_chan_per_board
                print(self.nevents,"events,",lastrate,"Hz",round(lastrate*self.num_board*self.num_samples*nchan/1e6,3),"MB/s")
                if lastrate>40: self.tinterval=500.
                else: self.tinterval=100.
                self.oldnevents=self.nevents

    def drawtext(self): # happens once per second
        self.ui.textBrowser.setText(self.chantext())
        self.ui.textBrowser.append("trigger threshold: " + str(round(self.hline,3)))

def setup_connections():
    return 1

def init():
    return 1

def cleanup():
    return 1

if __name__ == '__main__':
    print('Argument List:', str(sys.argv))
    for a in sys.argv:
        if a[0] == "-":
            print(a)
    print("Python version", sys.version)
    app = QtWidgets.QApplication.instance()
    standalone = app is None
    if standalone:
        #print('INSIDE STANDALONE')
        app = QtWidgets.QApplication(sys.argv)
    try:
        font = app.font()
        font.setPixelSize(11)
        app.setFont(font)
        win = MainWindow()
        win.setWindowTitle('Haasoscope Qt')
        if not setup_connections():
            print("Exiting now - failed setup_connections!")
            sys.exit(1)
        if not init():
            print("Exiting now - failed init!")
            cleanup()
            sys.exit()
        win.launch()
        win.triggerposchanged(128)  # center the trigger
        win.dostartstop()
    except DeviceError:
        print("device com failed!")
    if standalone:
        rv=app.exec_()
        sys.exit(rv)
    else:
        print("Done, but Qt window still active")
