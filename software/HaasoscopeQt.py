import numpy as np
import sys, time
import pyqtgraph as pg
from ftd2xx import DeviceError
from pyqtgraph.Qt import QtCore, QtWidgets, loadUiType

#################

from USB_FTX232H_FT60X import USB_FTX232H_FT60X_sync245mode # see USB_FTX232H_FT60X.py
usb = USB_FTX232H_FT60X_sync245mode(device_to_open_list=(('FTX232H','HaasoscopePro USB2'),('FT60X','Haasoscope USB3')))

def binprint(x):
    return bin(x)[2:].zfill(8)

def getbit(i, n):
    return (i >> n) & 1
def oldbytes():
    while True:
        olddata = usb.recv(10000000)
        print("Got",len(olddata),"old bytes")
        if len(olddata)==0: break
        print("Old byte0:",olddata[0])

def clkswitch():
    usb.send(bytes([1, 99, 99, 99, 100, 100, 100, 100]))
    tres = usb.recv(4)
    print("Clk switch: bad1 bad0, activeclk, switch", tres[3], tres[2], tres[1], tres[0])
def inttobytes(theint): #convert length number to a 4-byte byte array (with type of 'bytes')
    return [theint & 0xff, (theint >> 8) & 0xff, (theint >> 16) & 0xff, (theint >> 24) & 0xff]
def spicommand(name, first, second, third, read, show_bin=False, cs=0, nbyte=3):
    # first byte to send, start of address
    # second byte to send, rest of address
    # third byte to send, value to write, ignored during read
    # cs is which chip to select, adc 0 by default
    # nbyte is 2 or 3, second byte is ignored in case of 2 bytes
    if read: first = first + 0x80 #set the highest bit for read, i.e. add 0x80
    usb.send(bytes([3, cs, first, second, third, 100, 100, nbyte]))  # get SPI result from command
    spires = usb.recv(4)
    if read:
        if show_bin: print("SPI read:\t" + name, "(", hex(first), hex(second), ")", binprint(spires[0]))
        else: print("SPI read:\t"+name, "(",hex(first),hex(second),")",hex(spires[0]))
    else: print("SPI write:\t"+name, "(",hex(first),hex(second),")",hex(third))

def spicommand2(name,first,second,third,fourth,read, cs=0, nbyte=3):
    # first byte to send, start of address
    # second byte to send, rest of address
    # third byte to send, value to write, ignored during read, to address +1 (the higher 8 bits)
    # fourth byte to send, value to write, ignored during read
    # cs is which chip to select, adc 0 by default
    # nbyte is 2 or 3, second byte is ignored in case of 2 bytes
    if read: first = first + 0x80  # set the highest bit for read, i.e. add 0x80
    usb.send(bytes([3, cs, first, second, fourth, 100, 100, nbyte]))  # get SPI result from command
    spires = usb.recv(4)
    usb.send(bytes([3, cs, first, second+0x01, third, 100, 100, nbyte]))  # get SPI result from command for next byte
    spires2 = usb.recv(4)
    if read: print("SPI read:\t"+name, "(",hex(first),hex(second),")",hex(spires2[0]),hex(spires[0]))
    else: print("SPI write:\t"+name, "(",hex(first),hex(second),")",hex(fourth),hex(third))

#address 1 2, value 1 (2)
def board_setup(dopattern=False):
    spicommand2("VENDOR", 0x00, 0x0c, 0x00, 0x00, True)
    spicommand("LVDS_EN", 0x02, 0x00, 0x00, False)  # disable LVDS interface
    spicommand("CAL_EN", 0x00, 0x61, 0x00, False)  # disable calibration
    #spicommand("LMODE", 0x02, 0x01, 0x03, False)  # LVDS mode: aligned, demux, dual channel
    spicommand("LMODE", 0x02, 0x01, 0x07, False)  # LVDS mode: aligned, demux, single channel
    spicommand("LVDS_SWING", 0x00, 0x48, 0x00, False)  #high swing mode
    #spicommand("LVDS_SWING", 0x00, 0x48, 0x01, False)  #low swing mode

    spicommand("LCTRL",0x02,0x04,0x0a,False) # use LSYNC_N (software), 2's complement
    #spicommand("LCTRL", 0x02, 0x04, 0x08, False)  # use LSYNC_N (software), offset binary

    #spicommand("INPUT_MUX", 0x00, 0x60, 0x11, False)  # swap inputs
    spicommand("INPUT_MUX", 0x00, 0x60, 0x01, False)  # unswap inputs

    if dopattern:
        spicommand("PAT_SEL", 0x02, 0x05, 0x11, False)  # test pattern
        usrval = 0x00
        usrval3 = 0x0f;  usrval2 = 0xff
        spicommand2("UPAT0", 0x01, 0x80, usrval3, usrval2, False)  # set pattern sample 0
        spicommand2("UPAT1", 0x01, 0x82, usrval, usrval, False)  # set pattern sample 1
        spicommand2("UPAT2", 0x01, 0x84, usrval, usrval, False)  # set pattern sample 2
        spicommand2("UPAT3", 0x01, 0x86, usrval, usrval, False)  # set pattern sample 3
        spicommand2("UPAT4", 0x01, 0x88, usrval, usrval, False)  # set pattern sample 4
        spicommand2("UPAT5", 0x01, 0x8a, usrval, usrval, False)  # set pattern sample 5
        spicommand2("UPAT6", 0x01, 0x8c, usrval, usrval, False)  # set pattern sample 6
        spicommand2("UPAT7", 0x01, 0x8e, usrval, usrval, False)  # set pattern sample 7
        #spicommand("UPAT_CTRL", 0x01, 0x90, 0x0e, False)  # set lane pattern to user, invert a bit of B C D
        spicommand("UPAT_CTRL", 0x01, 0x90, 0x00, False)  # set lane pattern to user
    else:
        spicommand("PAT_SEL", 0x02, 0x05, 0x02, False)  # normal ADC data
        spicommand("UPAT_CTRL", 0x01, 0x90, 0x1e, False)  # set lane pattern to default

    spicommand("CAL_EN", 0x00, 0x61, 0x01, False)  # enable calibration
    spicommand("LVDS_EN", 0x02, 0x00, 0x01, False)  # enable LVDS interface
    spicommand("LSYNC_N", 0x02, 0x03, 0x00, False)  # assert ~sync signal
    spicommand("LSYNC_N", 0x02, 0x03, 0x01, False)  # deassert ~sync signal
    #spicommand("CAL_SOFT_TRIG", 0x00, 0x6c, 0x00, False)
    #spicommand("CAL_SOFT_TRIG", 0x00, 0x6c, 0x01, False)

    spicommand("Amp Rev ID", 0x00, 0x00, 0x00, True, cs=1, nbyte=2)
    spicommand("Amp Prod ID", 0x01, 0x00, 0x00, True, cs=1, nbyte=2)
    gain=0x20 #00 to 20 is 26 to -6 dB
    spicommand("Amp Gain", 0x02, 0x00, gain, False, cs=1, nbyte=2)
    spicommand("Amp Gain", 0x02, 0x00, 0x00, True, cs=1, nbyte=2)

#################

# Define main window class from template
WindowTemplate, TemplateBaseClass = loadUiType("Haasoscope.ui")
class MainWindow(TemplateBaseClass):
    debug = False
    dopattern = False
    debugprint = True
    showbinarydata = True
    debugstrobe = False
    xydata_overlapped=True
    total_rx_len = 0
    time_start = time.time()
    triggertype = 1  # 0 no trigger, 1 threshold trigger
    if dopattern: triggertype = 0
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
        self.ui.upposButton3.clicked.connect(self.uppos3)
        self.ui.downposButton3.clicked.connect(self.downpos3)
        self.ui.upposButton4.clicked.connect(self.uppos4)
        self.ui.downposButton4.clicked.connect(self.downpos4)
        self.ui.chanBox.valueChanged.connect(self.selectchannel)
        self.ui.acdcCheck.stateChanged.connect(self.setacdc)
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

    # for 3rd byte, 000:all 001:M 010:C0 011:C1 100:C2 101:C3 110:C4
    # for 4th byte, 1 is up, 0 is down
    def uppos(self):
        usb.send(bytes([6, 99, 3, 1, 100, 100, 100, 100])) #c1
        #usb.send(bytes([6, 99, 4, 1, 100, 100, 100, 100])) #c2
        print("phase up c1")
    def uppos3(self):
        usb.send(bytes([6, 99, 5, 1, 100, 100, 100, 100])) #c3
        print("phase up c3")
    def uppos4(self):
        usb.send(bytes([6, 99, 6, 1, 100, 100, 100, 100])) #c4
        print("phase up c4")
    def downpos(self):
        usb.send(bytes([6, 99, 3, 0, 100, 100, 100, 100])) #c1
        #usb.send(bytes([6, 99, 4, 0, 100, 100, 100, 100])) #c2
        print("phase down c1")
    def downpos3(self):
        usb.send(bytes([6, 99, 5, 0, 100, 100, 100, 100])) #c3
        print("phase down c3")

    def downpos4(self):
        usb.send(bytes([6, 99, 6, 0, 100, 100, 100, 100])) #c4
        print("phase down c4")


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
    min_y=-pow(2,12)
    max_y=pow(2,12)
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

    num_chan_per_board=4
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

    if xydata_overlapped:
        xydata = np.empty([int(num_chan_per_board * num_board), 2, num_samples], dtype=float)
    else:
        xydata = np.empty([int(num_chan_per_board * num_board), 2, 4*num_samples], dtype=float)

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
    nbadclkA = 0
    nbadclkB = 0
    nbadclkC = 0
    nbadclkD = 0

    def getchannels(self):
        nsubsamples = 10*4 + 8+2  # extra 4 for clk+str, and 2 dead beef

        expect_samples = 100
        usb.send(bytes([5, self.triggertype, 99, 99] + inttobytes(expect_samples+1)))  # length to take (last 4 bytes)

        expect_len = expect_samples * 2 * nsubsamples  # length to request: each adc bit is stored as 10 bits in 2 bytes
        usb.send(bytes([0, 99, 99, 99] + inttobytes(expect_len)))  # send the 4 bytes to usb
        data = usb.recv(expect_len)  # recv from usb
        rx_len = len(data)

        self.total_rx_len += rx_len
        if expect_len != rx_len:
            print('*** expect_len (%d) and rx_len (%d) mismatch' % (expect_len, rx_len))

        else:
            self.nbadclkA = 0
            self.nbadclkB = 0
            self.nbadclkC = 0
            self.nbadclkD = 0
            for s in range(0, int(expect_samples)):
                chan = -1
                for n in range(nsubsamples): # the subsample to get
                    pbyte = nsubsamples*2*s + 2*n
                    lowbits = data[pbyte + 0]
                    highbits = data[pbyte + 1]
                    if n<40 and getbit(highbits,3): highbits = (highbits - 16)*256
                    else: highbits = highbits*256
                    val = highbits + lowbits
                    if n % 10 == 0: chan = chan + 1

                    if n==40 and val&0x5555!=4369 and val&0x5555!=17476:
                        self.nbadclkA=self.nbadclkA+1
                    if n==41 and val&0x5555!=1 and val&0x5555!=4:
                        self.nbadclkA=self.nbadclkA+1
                    if n==42 and val&0x5555!=4369 and val&0x5555!=17476:
                        self.nbadclkB=self.nbadclkB+1
                    if n==43 and val&0x5555!=1 and val&0x5555!=4:
                        self.nbadclkB=self.nbadclkB+1
                    if n==44 and val&0x5555!=4369 and val&0x5555!=17476:
                        self.nbadclkC=self.nbadclkC+1
                    if n==45 and val&0x5555!=1 and val&0x5555!=4:
                        self.nbadclkC=self.nbadclkC+1
                    if n==46 and val&0x5555!=4369 and val&0x5555!=17476:
                        self.nbadclkD=self.nbadclkD+1
                    if n==47 and val&0x5555!=1 and val&0x5555!=4:
                        self.nbadclkD=self.nbadclkD+1
                    #if 40<=n<48 and self.nbadclkD:
                    #    print("s=", s, "n=", n, "pbyte=", pbyte, "chan=", chan, binprint(data[pbyte + 1]), binprint(data[pbyte + 0]), val)

                    if 40 <= n < 48 and self.debugstrobe:
                        strobe = val&0xaaaa
                        if strobe != 0:
                            print("s=",s,"n=",n,"str",binprint(strobe),strobe)

                    if self.debug and self.debugprint:
                        goodval=-1
                        if s<0 or (n<40 and val!=0 and val!=goodval):
                            if self.showbinarydata and n<40:
                                #if s<0 or chan!=3 or (chan==3 and val!=255 and val!=511 and val!=1023 and val!=2047):
                                if s<100:
                                    if lowbits>0 or highbits>0:
                                        print("s=",s,"n=",n, "pbyte=",pbyte, "chan=",chan, binprint(data[pbyte + 1]), binprint(data[pbyte + 0]), val)
                            elif n<40:
                                print("s=",s,"n=",n, "pbyte=",pbyte, "chan=",chan, hex(data[pbyte + 1]), hex(data[pbyte + 0]))
                    if n<40:
                        if self.xydata_overlapped:
                            self.xydata[chan][1][s*10+(9-(n%10))] = val
                        else:
                            self.xydata[0][1][chan+ 4*(s*10+(9-(n%10)))] = val

        if self.debug or self.debugstrobe:
            time.sleep(.5)
            #oldbytes()

        #self.xydata[chan][1] = np.random.random_sample(size = self.num_samples)
        return rx_len

    def chantext(self):
        return "nbadclks A B C D "+str(self.nbadclkA)+" "+str(self.nbadclkB)+" "+str(self.nbadclkC)+" "+str(self.nbadclkD)

    def setup_connections(self):
        print("Starting")
        oldbytes()

        usb.send(bytes([2, 99, 99, 99, 100, 100, 100, 100]))  # get version
        res = usb.recv(4)
        print("Version", res[3], res[2], res[1], res[0])

        #clkswitch()

        board_setup(self.dopattern)
        return 1

    def init(self):
        if self.xydata_overlapped:
            for c in range(self.num_chan_per_board):
                self.xydata[c][0] = np.array([range(0,1000)])
        else:
            self.xydata[0][0] = np.array([range(0, 4000)])
        return 1

    def cleanup(self):
        return 1

    def mainloop(self):
        if self.paused: time.sleep(.1)
        else:
            try:
                rx_len=self.getchannels()
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
                print(self.nevents,"events,",lastrate,"Hz",round(lastrate*rx_len/1e6,3),"MB/s")
                if lastrate>40: self.tinterval=500.
                else: self.tinterval=100.
                self.oldnevents=self.nevents

    def drawtext(self): # happens once per second
        self.ui.textBrowser.setText(self.chantext())
        self.ui.textBrowser.append("trigger threshold: " + str(round(self.hline,3)))


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
        if not win.setup_connections():
            print("Exiting now - failed setup_connections!")
            sys.exit(1)
        if not win.init():
            print("Exiting now - failed init!")
            win.cleanup()
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
