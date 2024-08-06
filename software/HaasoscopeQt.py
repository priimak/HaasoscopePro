# -*- coding: utf-8 -*-
"""
pyqtgraph widget with UI template created with Qt Designer
"""

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
        self.ui.actionRecord.triggered.connect(self.record)
        self.ui.verticalSlider.valueChanged.connect(self.triggerlevelchanged)
        self.ui.horizontalSlider.valueChanged.connect(self.triggerposchanged)
        self.ui.rollingButton.clicked.connect(self.rolling)
        self.ui.singleButton.clicked.connect(self.single)
        self.ui.timeslowButton.clicked.connect(self.timeslow)
        self.ui.timefastButton.clicked.connect(self.timefast)
        self.ui.risingedgeCheck.stateChanged.connect(self.risingfalling)
        self.ui.exttrigCheck.stateChanged.connect(self.exttrig)
        self.ui.totBox.valueChanged.connect(self.tot)
        self.ui.coinBox.valueChanged.connect(self.coin)
        self.ui.cointimeBox.valueChanged.connect(self.cointime)
        self.ui.autorearmCheck.stateChanged.connect(self.autorearm)
        self.ui.noselftrigCheck.stateChanged.connect(self.noselftrig)
        self.ui.avgCheck.stateChanged.connect(self.avg)
        self.ui.logicCheck.stateChanged.connect(self.logic)
        self.ui.highresCheck.stateChanged.connect(self.highres)
        self.ui.usb2Check.stateChanged.connect(self.usb2)
        self.ui.gridCheck.stateChanged.connect(self.grid)
        self.ui.markerCheck.stateChanged.connect(self.marker)
        self.ui.upposButton.clicked.connect(self.uppos)
        self.ui.downposButton.clicked.connect(self.downpos)
        self.ui.chanBox.valueChanged.connect(self.selectchannel)
        self.ui.dacBox.valueChanged.connect(self.setlevel)
        self.ui.minidisplayCheck.stateChanged.connect(self.minidisplay)
        self.ui.acdcCheck.stateChanged.connect(self.acdc)
        self.ui.gainCheck.stateChanged.connect(self.gain)
        self.ui.supergainCheck.stateChanged.connect(self.supergain)
        self.ui.actionRead_from_file.triggered.connect(self.actionRead_from_file)
        self.ui.actionStore_to_file.triggered.connect(self.actionStore_to_file)
        self.ui.actionOutput_clk_left.triggered.connect(self.actionOutput_clk_left)
        self.ui.actionAllow_same_chan_coin.triggered.connect(self.actionAllow_same_chan_coin)
        self.ui.actionDo_autocalibration.triggered.connect(self.actionDo_autocalibration)
        self.ui.chanonCheck.stateChanged.connect(self.chanon)
        self.ui.slowchanonCheck.stateChanged.connect(self.slowchanon)
        self.ui.trigchanonCheck.stateChanged.connect(self.trigchanon)
        self.ui.oversampCheck.clicked.connect(self.oversamp)
        self.ui.overoversampCheck.clicked.connect(self.overoversamp)
        self.ui.decodeCheck.clicked.connect(self.decode)
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

        if self.chanforscreen == self.selectedchannel:   self.ui.minidisplayCheck.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.minidisplayCheck.setCheckState(QtCore.Qt.Unchecked)
        if self.acdc[self.selectedchannel]:   self.ui.acdcCheck.setCheckState(QtCore.Qt.Unchecked)
        else:   self.ui.acdcCheck.setCheckState(QtCore.Qt.Checked)
        if self.gain[self.selectedchannel]:   self.ui.gainCheck.setCheckState(QtCore.Qt.Unchecked)
        else:   self.ui.gainCheck.setCheckState(QtCore.Qt.Checked)
        if self.supergain[self.selectedchannel]:   self.ui.supergainCheck.setCheckState(QtCore.Qt.Unchecked)
        else:   self.ui.supergainCheck.setCheckState(QtCore.Qt.Checked)
        if self.havereadswitchdata: self.ui.supergainCheck.setEnabled(False)

        chanonboard = self.selectedchannel%self.num_chan_per_board
        theboard = self.num_board-1-int(self.selectedchannel/self.num_chan_per_board)

        if self.havereadswitchdata:
            if self.testBit(self.switchpos[theboard],chanonboard):   self.ui.ohmCheck.setCheckState(QtCore.Qt.Unchecked)
            else:   self.ui.ohmCheck.setCheckState(QtCore.Qt.Checked)

        if self.dousb:   self.ui.usb2Check.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.usb2Check.setCheckState(QtCore.Qt.Unchecked)

        if len(self.lines)>0:
            if self.lines[self.selectedchannel].isVisible():   self.ui.chanonCheck.setCheckState(QtCore.Qt.Checked)
            else:   self.ui.chanonCheck.setCheckState(QtCore.Qt.Unchecked)
        if self.trigsactive[self.selectedchannel]:   self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.trigchanonCheck.setCheckState(QtCore.Qt.Unchecked)

        if self.dooversample[self.selectedchannel]>0:   self.ui.oversampCheck.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.oversampCheck.setCheckState(QtCore.Qt.Unchecked)
        if self.selectedchannel%self.num_chan_per_board>1:   self.ui.oversampCheck.setEnabled(False)
        else:  self.ui.oversampCheck.setEnabled(True)

        if self.dooversample[self.selectedchannel]>=9:   self.ui.overoversampCheck.setCheckState(QtCore.Qt.Checked)
        else:   self.ui.overoversampCheck.setCheckState(QtCore.Qt.Unchecked)
        if self.selectedchannel%self.num_chan_per_board>0:  self.ui.overoversampCheck.setEnabled(False)
        else:   self.ui.overoversampCheck.setEnabled(True)

    def oversamp(self):
        if self.oversamp(self.selectedchannel)>=0:
            self.prepareforsamplechange()
            self.timechanged()
            if self.dooversample[self.selectedchannel] > 0:
                #turn off chan+2
                self.lines[self.selectedchannel+2].setVisible(False)
                if self.trigsactive[self.selectedchannel+2]: self.toggletriggerchan(self.selectedchannel+2)
            else:
                # turn on chan+2
                self.lines[self.selectedchannel + 2].setVisible(True)
                if not self.trigsactive[self.selectedchannel + 2]: self.toggletriggerchan(self.selectedchannel + 2)

    def overoversamp(self):
        if self.overoversamp()>=0:
            self.prepareforsamplechange()
            self.timechanged()
            #turn off chan+1
            self.lines[self.selectedchannel+1].setVisible(False)
            if self.trigsactive[self.selectedchannel+1]: self.toggletriggerchan(self.selectedchannel+2)

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

    def slowchanon(self):
        maxchan=self.ui.slowchanBox.value()+self.num_chan_per_board*self.num_board
        if self.ui.slowchanonCheck.checkState() == QtCore.Qt.Checked:
            self.lines[maxchan].setVisible(True)
        else:
            self.lines[maxchan].setVisible(False)

    def acdc(self):
        if self.ui.acdcCheck.checkState() == QtCore.Qt.Checked: #ac coupled
            if self.acdc[self.selectedchannel]:
                self.setacdc()
        if self.ui.acdcCheck.checkState() == QtCore.Qt.Unchecked: #dc coupled
            if not self.acdc[self.selectedchannel]:
                self.setacdc()

    def gain(self):
        if self.ui.gainCheck.checkState() == QtCore.Qt.Checked: #x10
            if self.gain[self.selectedchannel]:
                self.tellswitchgain(self.selectedchannel)
        if self.ui.gainCheck.checkState() == QtCore.Qt.Unchecked: #x1
            if not self.gain[self.selectedchannel]:
                self.tellswitchgain(self.selectedchannel)

    def supergain(self):
        if self.ui.supergainCheck.checkState() == QtCore.Qt.Checked: #x100
            if self.supergain[self.selectedchannel]:
                self.togglesupergainchan(self.selectedchannel)
        if self.ui.supergainCheck.checkState() == QtCore.Qt.Unchecked: #x1
            if not self.supergain[self.selectedchannel]:
                self.togglesupergainchan(self.selectedchannel)

    def minidisplay(self):
        if self.ui.minidisplayCheck.checkState()==QtCore.Qt.Checked:
            if self.chanforscreen != self.selectedchannel:
                self.tellminidisplaychan(self.selectedchannel)

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

    def actionRead_from_file(self):
        self.readcalib()

    def actionStore_to_file(self):
        self.storecalib()

    def actionDo_autocalibration(self):
        print("starting autocalibration")
        self.autocalibchannel=0

    def actionOutput_clk_left(self):
        self.toggle_clk_last()

    def actionAllow_same_chan_coin(self):
        self.toggle_allow_same_chan_coin()

    def exttrig(self):
        self.toggleuseexttrig()

    def tot(self):
        self.triggertimethresh = self.ui.totBox.value()
        self.settriggertime(self.triggertimethresh)

    def coin(self):
        self.settrigcoin(self.ui.coinBox.value())
    def cointime(self):
        self.settrigcointime(self.ui.cointimeBox.value())

    def autorearm(self):
        self.toggleautorearm()

    def noselftrig(self):
        self.donoselftrig()

    def avg(self):
        self.average = not self.average
        print("average",self.average)

    def logic(self):
        self.togglelogicanalyzer()
        if self.dologicanalyzer:
            for li in np.arange(self.num_logic_inputs):
                c=(0,0,0)
                pen = pg.mkPen(color=c) # add linewidth=1.7, alpha=.65
                self.lines[self.logicline1+li].setPen(pen)
        else:
            for li in np.arange(self.num_logic_inputs):
                self.lines[self.logicline1+li].setPen(None)

    def highres(self):
        self.togglehighres()

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

    def decode(self):
        if self.ui.decodeCheck.checkState() != QtCore.Qt.Checked:
            # delete all previous labels
            for label in self.decodelabels:
                self.ui.plot.removeItem(label)

    def drawing(self):
        if self.ui.drawingCheck.checkState() == QtCore.Qt.Checked:
            self.dodrawing=True
            print("drawing now",self.dodrawing)
        else:
            self.dodrawing=False
            print("drawing now",self.dodrawing)

    def record(self):
        self.savetofile = not self.savetofile
        if self.savetofile:
            fname="Haasoscope_out_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
            self.outf = open(fname,"wt")
            self.ui.statusBar.showMessage("now recording to file: "+fname)
            self.ui.actionRecorself.setText("Stop recording")
        else:
            self.outf.close()
            self.ui.statusBar.showMessage("stopped recording to file")
            self.ui.actionRecord.setText("Record to file")

    def fastadclineclick(self, curve):
        for li in range(self.nlines):
            if curve is self.lines[li].curve:
                maxchan=li-self.num_chan_per_board*self.num_board
                if maxchan>=0: # these are the slow ADC channels
                    self.ui.slowchanBox.setValue(maxchan)
                    #print "selected slow curve", maxchan
                else:
                    self.ui.chanBox.setValue(li)
                    #print "selected curve", li
                    modifiers = app.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier:
                        self.ui.trigchanonCheck.toggle()
                    elif modifiers == QtCore.Qt.ControlModifier:
                        self.ui.chanonCheck.toggle()

    """ TODO:       
            elif event.key=="ctrl+r": 
                if self.ydatarefchan<0: self.ydatarefchan=self.selectedchannel
                else: self.ydatarefchan=-1
            elif event.key==">": self.refsinchan=self.selectedchannel; self.oldchanphase=-1.; self.reffreq=0;
            elif event.key=="Y": 
                if self.selectedchannel+1>=len(self.dooversample): print "can't do XY plot on last channel"
                else:
                    if self.dooversample[self.selectedchannel]==self.dooversample[self.selectedchannel+1]:
                        self.doxyplot=True; self.xychan=self.selectedchannel; print "doxyplot now",self.doxyplot,"for channel",self.xychan; return;
                    else: print "oversampling settings must match between channels for XY plotting"
    """

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
            maxchan=li-self.num_chan_per_board*self.num_board
            c=(0,0,0)
            if maxchan>=0: # these are the slow ADC channels
                if self.num_board>1:
                    board = int(self.num_board-1-self.max10adcchans[maxchan][0])
                    if board % 4 == 0: c = (255 - 0.2 * 255 * maxchan, 0, 0)
                    if board % 4 == 1: c = (0, 255 - 0.2 * 255 * maxchan, 0)
                    if board % 4 == 2: c = (0, 0, 255 - 0.2 * 255 * maxchan)
                    if board % 4 == 3: c = (255 - 0.2 * 255 * maxchan, 0, 255 - 0.2 * 255 * maxchan)
                else:
                    c=(0.1*(maxchan+1),0.1*(maxchan+1),0.1*(maxchan+1))
                pen = pg.mkPen(color=c) # add linewidth=0.5, alpha=.5
                line = self.ui.plot.plot(pen=pen,name="slowadc_"+str(self.max10adcchans[maxchan]))
            else: # these are the fast ADC channels
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

    decodelabels = []
    def updateplot(self):
        self.mainloop()
        if self.savetofile: self.dosavetofile()
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

    oldxscale=0
    def dosavetofile(self):
        time_s=str(time.time())
        if self.doh5:
            datatosave=self.xydata[:,1,:] # save all y data by default
            if self.xscale != self.oldxscale:
                datatosave=self.xydata # since the x scale changed (or is the first event), save all data for this event
                self.oldxscale=self.xscale
            h5ds = self.outf.create_dataset(str(self.nevents), data=datatosave, dtype='float32', compression="lzf") #compression="gzip", compression_opts=5)
            #about 3kB per event per board (4 channels) for 512 samples
            h5ds.attrs['time']=time_s
            h5ds.attrs['trigger_position']=str(self.vline*self.xscaling)
            h5ds.attrs['sample_period'] =str(2.*self.xscale/self.num_samples)
            h5ds.attrs['num_samples'] =str(self.num_samples)
            # see h5py_analyze_example.py for how to read in python
        else:
            for c in range(self.num_chan_per_board*self.num_board):
                if self.lines[c].isVisible(): # only save the data for visible channels
                    self.outf.write(str(self.nevents)+",") # start of each line is the event number
                    self.outf.write(time_s+",") # next column is the time in seconds of the current event
                    self.outf.write(str(c)+",") # next column is the channel number
                    self.outf.write(str(self.vline*self.xscaling)+",") # next column is the trigger time
                    self.outf.write(str(2.*self.xscale/self.num_samples)+",") # next column is the time between samples, in ns
                    self.outf.write(str(self.num_samples)+",") # next column is the number of samples
                    self.xydata[c][1].tofile(self.outf,",",format="%.3f") # save y data (1) from fast adc channel c
                    self.outf.write("\n") # newline

    nevents=0
    oldnevents=0
    tinterval=100.
    oldtime=time.time()
    def mainloop(self):
        if self.paused: time.sleep(.1)
        else:
            try:
                status=self.getchannels()
            except DeviceError:
                print("Device error")
                sys.exit(1)
            if status==2: self.selectchannel() #we updated the switch data
            if self.db: print(time.time()-self.oldtime,"done with evt",self.nevents)
            self.nevents += 1
            if self.nevents-self.oldnevents >= self.tinterval:
                now=time.time()
                elapsedtime=now-self.oldtime
                self.oldtime=now
                lastrate = round(self.tinterval/elapsedtime,2)
                if self.dologicanalyzer: nchan = self.num_chan_per_board + 1
                else: nchan = self.num_chan_per_board
                print(self.nevents,"events,",lastrate,"Hz",round(lastrate*self.num_board*self.num_samples*nchan/1e6,3),"MB/s")
                if lastrate>40: self.tinterval=500.
                else: self.tinterval=100.
                self.oldnevents=self.nevents

            if self.nevents%self.numrecordeventsperfile==0:
                if self.savetofile: # if writing, close and open new file
                    self.record()
                    if self.doh5: self.oldxscale=0 #to force writing the time header info in h5
                    self.record()
            if self.getone and not self.timedout: self.dostartstop()

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
