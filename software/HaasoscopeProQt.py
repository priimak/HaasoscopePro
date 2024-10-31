import numpy as np
import sys, time
import pyqtgraph as pg
from ftd2xx import DeviceError
import ftd2xx

# noinspection PyUnresolvedReferences
from pyqtgraph.Qt import QtCore, QtWidgets, loadUiType

import warnings
from scipy.optimize import curve_fit

from USB_FT232H import UsbFt232hSync245mode

# https://github.com/drandyhaas/pyadf435x
from adf435x import calculate_regs, make_regs, DeviceType, MuxOut, ClkDivMode, BandSelectClockMode, FeedbackSelect, PDPolarity

usbs=[]
ftds=ftd2xx.listDevices()
print("Found devices:",ftds)
for ftdserial in ftds:
    #print("FTD serial:",ftdserial)
    usbdevice = UsbFt232hSync245mode('FTX232H', 'HaasoscopePro USB2', ftdserial)
    #print(usbdevice)
    if usbdevice.good:
        if usbdevice.serial==b"FT9LYZXP":
            usbs.append(usbdevice)
            print("Connected USB device",usbdevice.serial)
print("Connected",len(usbs),"devices")

def binprint(x):
    return bin(x)[2:].zfill(8)

#get bit n from byte i
def getbit(i, n):
    return (i >> n) & 1

def bytestoint(thebytes):
    return thebytes[0]+pow(2,8)*thebytes[1]+pow(2,16)*thebytes[2]+pow(2,24)*thebytes[3]

def oldbytes():
    for usb in usbs:
        olddata = usb.recv(10000000)
        print("Got",len(olddata),"old bytes")
        if len(olddata)==0: break
        print("Old byte0:",olddata[0])

def inttobytes(theint): #convert length number to a 4-byte byte array (with type of 'bytes')
    return [theint & 0xff, (theint >> 8) & 0xff, (theint >> 16) & 0xff, (theint >> 24) & 0xff]

def spicommand(usb, name, first, second, third, read, fourth=100, show_bin=False, cs=0, nbyte=3, quiet=False):
    # first byte to send, start of address
    # second byte to send, rest of address
    # third byte to send, value to write, ignored during read
    # cs is which chip to select, adc 0 by default
    # nbyte is 2 or 3, second byte is ignored in case of 2 bytes
    if read: first = first + 0x80 #set the highest bit for read, i.e. add 0x80
    usb.send(bytes([3, cs, first, second, third, fourth, 100, nbyte]))  # get SPI result from command
    spires = usb.recv(4)
    if read:
        if not quiet:
            if show_bin: print("SPI read:\t" + name, "(", hex(first), hex(second), ")", binprint(spires[1]), binprint(spires[0]))
            else: print("SPI read:\t"+name, "(",hex(first),hex(second),")",hex(spires[1]), hex(spires[0]))
        return spires
    else:
        if not quiet:
            if nbyte==4: print("SPI write:\t"+name, "(",hex(first),hex(second),")",hex(third),hex(fourth))
            else: print("SPI write:\t"+name, "(",hex(first),hex(second),")",hex(third))

def spicommand2(usb, name,first,second,third,fourth,read, cs=0, nbyte=3):
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

def adf4350(usb,freq, phase, r_counter=1, divided=FeedbackSelect.Divider, ref_doubler=False, ref_div2=True, themuxout=False):
    print('ADF4350 being set to %0.2f MHz' % freq)
    if themuxout:
        muxout=MuxOut.DGND
        print("muxout GND 0")
    else:
        muxout=MuxOut.DVdd
        print("muxout V 1")
    INT, MOD, FRAC, output_divider, band_select_clock_divider = (calculate_regs(
        device_type=DeviceType.ADF4350, freq=freq, ref_freq=50.0,
        band_select_clock_mode=BandSelectClockMode.Low,
        feedback_select=divided,
        r_counter=r_counter, # needed when using FeedbackSelect.Divider (needed for phase resync?!)
        ref_doubler=ref_doubler, ref_div2=ref_div2, enable_gcd=True))
    print("INT", INT, "MOD", MOD, "FRAC", FRAC, "outdiv", output_divider, "bandselclkdiv", band_select_clock_divider)
    regs = make_regs(
        INT=INT, MOD=MOD, FRAC=FRAC, output_divider=output_divider,
        band_select_clock_divider=band_select_clock_divider, r_counter=r_counter, ref_doubler=ref_doubler, ref_div_2=ref_div2,
        device_type=DeviceType.ADF4350, phase_value=phase, mux_out=muxout, charge_pump_current=2.50,
        feedback_select=divided, pd_polarity=PDPolarity.Positive, prescaler='4/5', band_select_clock_mode=BandSelectClockMode.Low,
        clk_div_mode=ClkDivMode.ResyncEnable, clock_divider_value=1000, csr=False,
        aux_output_enable=False, aux_output_power=-4.0, output_enable=True, output_power=-4.0) # (-4,-1,2,5)
    #values can also be computed using free Analog Devices ADF435x Software:
    #https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/eval-adf4351.html#eb-relatedsoftware
    spimode(usb,0)
    for r in reversed(range(len(regs))):
        #regs[2]=0x5004E42 #to override from ADF435x software
        print("adf4350 reg", r, binprint(regs[r]), hex(regs[r]))
        fourbytes = inttobytes(regs[r])
        # for i in range(4): print(binprint(fourbytes[i]))
        spicommand(usb,"ADF4350 Reg " + str(r), fourbytes[3], fourbytes[2], fourbytes[1], False, fourth=fourbytes[0], cs=3, nbyte=4) # was cs=2 on alpha board v1.11
    spimode(usb,0)

debugspi=False
def spimode(usb, mode): # set SPI mode (polarity of clk and data)
    usb.send(bytes([4, mode, 0, 0, 0, 0, 0, 0]))
    spires = usb.recv(4)
    if debugspi: print("SPI mode now",spires[0])

dooverrange=False
tad = 0
def board_setup(usb, dopattern, twochannel):
    spimode(usb,0)
    spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x00, False) # power up
    #spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x03, False) # power down
    spicommand2(usb, "VENDOR", 0x00, 0x0c, 0x00, 0x00, True)
    spicommand(usb, "LVDS_EN", 0x02, 0x00, 0x00, False)  # disable LVDS interface
    spicommand(usb, "CAL_EN", 0x00, 0x61, 0x00, False)  # disable calibration

    if twochannel:
        spicommand(usb, "LMODE", 0x02, 0x01, 0x03, False)  # LVDS mode: aligned, demux, dual channel, 12-bit
        # spicommand("LMODE", 0x02, 0x01, 0x01, False)  # LVDS mode: staggered, demux, dual channel, 12-bit
    else:
        spicommand(usb, "LMODE", 0x02, 0x01, 0x07, False)  # LVDS mode: aligned, demux, single channel, 12-bit
        #spicommand(usb, "LMODE", 0x02, 0x01, 0x37, False)  # LVDS mode: aligned, demux, single channel, 8-bit
        #spicommand(usb, "LMODE", 0x02, 0x01, 0x05, False)  # LVDS mode: staggered, demux, single channel, 12-bit

    spicommand(usb, "LVDS_SWING", 0x00, 0x48, 0x00, False)  #high swing mode
    #spicommand(usb, "LVDS_SWING", 0x00, 0x48, 0x01, False)  #low swing mode

    spicommand(usb, "LCTRL",0x02,0x04,0x0a,False) # use LSYNC_N (software), 2's complement
    #spicommand(usb, "LCTRL", 0x02, 0x04, 0x08, False)  # use LSYNC_N (software), offset binary

    spicommand(usb, "INPUT_MUX", 0x00, 0x60, 0x12, False)  # swap inputs
    #spicommand(usb, "INPUT_MUX", 0x00, 0x60, 0x01, False)  # unswap inputs

    #spicommand(usb, "TAD", 0x02, 0xB7, 0x01, False)  # invert clk
    spicommand(usb, "TAD", 0x02, 0xB7, 0x00, False) # don't invert clk

    spicommand(usb, "TAD", 0x02, 0xB6, tad, False) # adjust TAD (time of ADC relative to clk)

    if dooverrange:
        spicommand(usb, "OVR_CFG", 0x02, 0x13, 0x0f, False)  # overrange on
        spicommand(usb, "OVR_T0", 0x02, 0x11, 0xf2, False)  # overrange threshold 0
        spicommand(usb, "OVR_T1", 0x02, 0x12, 0xab, False)  # overrange threshold 1
    else:
        spicommand(usb, "OVR_CFG", 0x02, 0x13, 0x07, False)  # overrange off

    if dopattern:
        spicommand(usb, "PAT_SEL", 0x02, 0x05, 0x11, False)  # test pattern
        usrval = 0x00
        usrval3 = 0x0f;  usrval2 = 0xff
        spicommand2(usb, "UPAT0", 0x01, 0x80, usrval3, usrval2, False)  # set pattern sample 0
        spicommand2(usb, "UPAT1", 0x01, 0x82, usrval, usrval, False)  # set pattern sample 1
        spicommand2(usb, "UPAT2", 0x01, 0x84, usrval, usrval, False)  # set pattern sample 2
        spicommand2(usb, "UPAT3", 0x01, 0x86, usrval, usrval, False)  # set pattern sample 3
        spicommand2(usb, "UPAT4", 0x01, 0x88, usrval, usrval, False)  # set pattern sample 4
        spicommand2(usb, "UPAT5", 0x01, 0x8a, usrval, usrval, False)  # set pattern sample 5
        spicommand2(usb, "UPAT6", 0x01, 0x8c, usrval, usrval, False)  # set pattern sample 6
        spicommand2(usb, "UPAT7", 0x01, 0x8e, usrval, usrval, False)  # set pattern sample 7
        #spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x0e, False)  # set lane pattern to user, invert a bit of B C D
        spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x00, False)  # set lane pattern to user
    else:
        spicommand(usb, "PAT_SEL", 0x02, 0x05, 0x02, False)  # normal ADC data
        spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x1e, False)  # set lane pattern to default

    spicommand(usb, "CAL_EN", 0x00, 0x61, 0x01, False)  # enable calibration
    spicommand(usb, "LVDS_EN", 0x02, 0x00, 0x01, False)  # enable LVDS interface
    spicommand(usb, "LSYNC_N", 0x02, 0x03, 0x00, False)  # assert ~sync signal
    spicommand(usb, "LSYNC_N", 0x02, 0x03, 0x01, False)  # deassert ~sync signal
    #spicommand(usb, "CAL_SOFT_TRIG", 0x00, 0x6c, 0x00, False)
    #spicommand(usb, "CAL_SOFT_TRIG", 0x00, 0x6c, 0x01, False)

    spimode(usb,0)
    spicommand(usb, "Amp Rev ID", 0x00, 0x00, 0x00, True, cs=1, nbyte=2)
    spicommand(usb, "Amp Prod ID", 0x01, 0x00, 0x00, True, cs=1, nbyte=2)
    gain=0x1a #00 to 20 is 26 to -6 dB, 0x1a is no gain
    spicommand(usb, "Amp Gain", 0x02, 0x00, gain, False, cs=1, nbyte=2)
    spicommand(usb, "Amp Gain", 0x02, 0x00, 0x00, True, cs=1, nbyte=2)

    spimode(usb,1)
    spicommand(usb, "DAC ref on", 0x38, 0xff, 0xff, False, cs=4)
    spicommand(usb, "DAC gain 1", 0x02, 0xff, 0xff, False, cs=4)
    spimode(usb,0)
    dooffset(usb, 0,0)
    dooffset(usb, 1,0)

# Define main window class from template
WindowTemplate, TemplateBaseClass = loadUiType("HaasoscopePro.ui")

def setgain(usb, chan,value):
    spimode(usb, 0)
    # 00 to 20 is 26 to -6 dB, 0x1a is no gain
    if chan==1: spicommand(usb, "Amp Gain 0", 0x02, 0x00, 26-value, False, cs=1, nbyte=2)
    if chan==0: spicommand(usb, "Amp Gain 1", 0x02, 0x00, 26-value, False, cs=2, nbyte=2)

def dooffset(usb, chan, val): #val goes from -100% to 100%
    spimode(usb, 1)
    dacval = int((pow(2, 16) - 1) * (-val/2+50)/100)
    #print("dacval is", dacval)
    if chan==1: spicommand(usb, "DAC 1 value", 0x18, dacval >> 8, dacval % 256, False, cs=4, quiet=True)
    if chan==0: spicommand(usb, "DAC 2 value", 0x19, dacval >> 8, dacval % 256, False, cs=4, quiet=True)
    spimode(usb, 0)

def fit_rise(x, top, left, leftplus, bot):  # a function for fitting to find risetime
    val = bot + (x - left) * (top - bot) / leftplus
    inbottom = (x <= left)
    val[inbottom] = bot
    intop = (x >= (left+leftplus))
    val[intop] = top
    return val

def clockswitch(usb):
    usb.send(bytes([7, 0, 0, 0, 99, 99, 99, 99]))
    clockinfo = usb.recv(4)
    print("Clockinfo", binprint(clockinfo[1]), binprint(clockinfo[0]))

def setchanimpedance(usb, chan, onemeg):
    if chan==0: controlbit=0
    elif chan==1: controlbit=4
    else: return
    usb.send(bytes([10, controlbit, onemeg, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("1M for chan",chan,onemeg)

def setchanacdc(usb, chan, ac):
    if chan==0: controlbit=1
    elif chan==1: controlbit=5
    else: return
    usb.send(bytes([10, controlbit, ac, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("AC for chan",chan,ac)

def setchanatt(usb, chan, att):
    if chan==0: controlbit=2
    elif chan==1: controlbit=6
    else: return
    usb.send(bytes([10, controlbit, att, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("Att for chan",chan,att)

def setsplit(usb, split):
    controlbit=7
    usb.send(bytes([10, controlbit, split, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("Split",split)

def boardinbits(usb):
    usb.send(bytes([2, 1, 0, 100, 100, 100, 100, 100]))  # get board in
    res = usb.recv(4)
    print("Board in bits", res[0], binprint(res[0]))
    return res[0]

def cleanup(usb):
    spimode(usb, 0)
    spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x03, False)  # power down
    return 1

def getoverrange(usb):
    if dooverrange:
        usb.send(bytes([2, 2, 0, 100, 100, 100, 100, 100]))  # get overrange 0
        res = usb.recv(4)
        print("Overrange0", res[3], res[2], res[1], res[0])

def gettemps(usb):
    spimode(usb, 0)
    spicommand(usb, "SlowDAC1", 0x00, 0x00, 0x00, True, cs=6, nbyte=2,quiet=True) # first conversion may be for old input
    slowdac1 = spicommand(usb, "SlowDAC1", 0x00, 0x00, 0x00, True, cs=6, nbyte=2,quiet=True)
    slowdac1amp = 4.0
    slowdac1V = (256*slowdac1[1]+slowdac1[0])*3300/pow(2,12)/slowdac1amp
    spicommand(usb, "SlowDAC2", 0x08, 0x00, 0x00, True, cs=6, nbyte=2,quiet=True) # first conversion may be for old input
    slowdac2 = spicommand(usb, "SlowDAC2", 0x08, 0x00, 0x00, True, cs=6, nbyte=2,quiet=True)
    slowdac2amp=2.0 # 1.1 in new board
    slowdac2V = (256*slowdac2[1]+slowdac2[0])*3300/pow(2,12)/slowdac2amp
    return "Temp voltages (ADC Board): " + str(round(slowdac1V,2)) + " " + str(round(slowdac2V,2))


class MainWindow(TemplateBaseClass):
    expect_samples = 100
    samplerate= 3.2 # freq in GHz
    nsunits=1
    num_chan_per_board = 2
    num_board = len(usbs)
    num_logic_inputs = 0
    debug = False
    dopattern = False
    debugprint = True
    showbinarydata = True
    debugstrobe = False
    dofast = False
    data_overlapped=False
    data_twochannel=False
    total_rx_len = 0
    time_start = time.time()
    triggertype = 1  # 0 no trigger, 1 threshold trigger rising, 2 threshold trigger falling, ...
    if dopattern: triggertype = 0
    selectedchannel=0
    activeusb = usbs[0]
    def __init__(self):
        TemplateBaseClass.__init__(self)
        
        # Create the main window
        self.ui = WindowTemplate()
        self.ui.setupUi(self)
        self.ui.runButton.clicked.connect(self.dostartstop)
        self.ui.threshold.valueChanged.connect(self.triggerlevelchanged)
        self.ui.thresholdDelta.valueChanged.connect(self.triggerdeltachanged)
        self.ui.thresholdPos.valueChanged.connect(self.triggerposchanged)
        self.ui.rollingButton.clicked.connect(self.rolling)
        self.ui.singleButton.clicked.connect(self.single)
        self.ui.timeslowButton.clicked.connect(self.timeslow)
        self.ui.timefastButton.clicked.connect(self.timefast)
        self.ui.risingedgeCheck.stateChanged.connect(self.risingfalling)
        self.ui.exttrigCheck.stateChanged.connect(self.exttrig)
        self.ui.totBox.valueChanged.connect(self.tot)
        self.ui.triggerChanBox.valueChanged.connect(self.triggerchanchanged)
        self.ui.gridCheck.stateChanged.connect(self.grid)
        self.ui.markerCheck.stateChanged.connect(self.marker)
        self.ui.highresCheck.stateChanged.connect(self.highres)
        self.ui.pllresetButton.clicked.connect(self.pllreset)
        self.ui.adfresetButton.clicked.connect(self.adfreset)
        self.ui.upposButton0.clicked.connect(self.uppos)
        self.ui.downposButton0.clicked.connect(self.downpos)
        self.ui.upposButton1.clicked.connect(self.uppos1)
        self.ui.downposButton1.clicked.connect(self.downpos1)
        self.ui.upposButton2.clicked.connect(self.uppos2)
        self.ui.downposButton2.clicked.connect(self.downpos2)
        self.ui.upposButton3.clicked.connect(self.uppos3)
        self.ui.downposButton3.clicked.connect(self.downpos3)
        self.ui.upposButton4.clicked.connect(self.uppos4)
        self.ui.downposButton4.clicked.connect(self.downpos4)
        self.ui.chanBox.valueChanged.connect(self.selectchannel)
        self.ui.gainBox.valueChanged.connect(self.changegain)
        self.ui.offsetBox.valueChanged.connect(self.changeoffset)
        self.ui.acdcCheck.stateChanged.connect(self.setacdc)
        self.ui.ohmCheck.stateChanged.connect(self.setohm)
        self.ui.oversampCheck.stateChanged.connect(self.setoversamp)
        self.ui.attCheck.stateChanged.connect(self.setatt)
        self.ui.actionOutput_clk_left.triggered.connect(self.actionOutput_clk_left)
        self.ui.chanonCheck.stateChanged.connect(self.chanon)
        self.ui.drawingCheck.clicked.connect(self.drawing)
        self.ui.fwfBox.valueChanged.connect(self.fwf)
        self.ui.tadBox.valueChanged.connect(self.setTAD)
        self.db=False
        self.lastTime = time.time()
        self.fps = None
        self.lines = []
        self.otherlines = []
        self.savetofile=False # save scope data to file
        self.doh5=False # use the h5 binary file format
        self.numrecordeventsperfile=1000 # number of events in each file to record before opening new file
        self.timer = QtCore.QTimer()
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.updateplot)
        self.timer2 = QtCore.QTimer()
        # noinspection PyUnresolvedReferences
        self.timer2.timeout.connect(self.drawtext)
        self.ui.statusBar.showMessage("Hello!")
        self.ui.plot.setBackground('w')
        self.show()

    def selectchannel(self):
        self.selectedchannel=self.ui.chanBox.value()
        if len(self.lines)>0:
            if self.lines[self.selectedchannel].isVisible(): self.ui.chanonCheck.setCheckState(QtCore.Qt.Checked)
            else:   self.ui.chanonCheck.setCheckState(QtCore.Qt.Unchecked)

    def changeoffset(self):
        dooffset(self.activeusb, self.selectedchannel, self.ui.offsetBox.value())

    def changegain(self):
        setgain(self.activeusb, self.selectedchannel, self.ui.gainBox.value())

    def fwf(self):
        self.fitwidthfraction=self.ui.fwfBox.value()/100.
        print("fwf now",self.fitwidthfraction)

    def setTAD(self):
        self.tad = self.ui.tadBox.value()
        spicommand(self.activeusb, "TAD", 0x02, 0xB6, self.tad, False)

    themuxoutV = True
    def adfreset(self):
        self.themuxoutV = not self.themuxoutV
        #adf4350(150.0, None, 10) # need larger rcounter for low freq
        adf4350(self.activeusb, self.samplerate*1000/2, None, themuxout=self.themuxoutV)
        time.sleep(0.1)
        res= boardinbits(self.activeusb)
        if not getbit(res,0): print("Pll not locked?") # should be 1 if locked
        if getbit(res,1) == self.themuxoutV: print("Pll not setup?") # should be 1 for MuxOut.DVdd

    def chanon(self):
        if self.ui.chanonCheck.checkState() == QtCore.Qt.Checked:
            self.lines[self.selectedchannel].setVisible(True)
        else:
            self.lines[self.selectedchannel].setVisible(False)

    def setacdc(self):
        setchanacdc(self.activeusb, self.selectedchannel,self.ui.acdcCheck.checkState() == QtCore.Qt.Checked) # will be True for AC, False for DC

    def setohm(self):
        setchanimpedance(self.activeusb, self.selectedchannel,self.ui.ohmCheck.checkState() == QtCore.Qt.Checked) # will be True for 1M ohm, False for 50 ohm

    def setatt(self):
        setchanatt(self.activeusb, self.selectedchannel,self.ui.attCheck.checkState() == QtCore.Qt.Checked) # will be True for attenuation on

    def setoversamp(self):
        setsplit(self.activeusb, self.ui.oversampCheck.checkState() == QtCore.Qt.Checked) # will be True for oversampling, False otherwise

    phasec = [ [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0] ]
    # for 3rd byte, 000:all 001:M 010=2:C0 011=3:C1 100=4:C2 101=5:C3 110=6:C4
    # for 4th byte, 1 is up, 0 is down
    def dophase(self,plloutnum,updown,pllnum=None,quiet=False):
        if pllnum is None: pllnum = int(self.ui.pllBox.value())
        self.activeusb.send(bytes([6,pllnum, int(plloutnum+2), updown, 100, 100, 100, 100]))
        if updown: self.phasec[pllnum][plloutnum] = self.phasec[pllnum][plloutnum]+1
        else: self.phasec[pllnum][plloutnum] = self.phasec[pllnum][plloutnum]-1
        if not quiet: print("phase for pllnum",pllnum,"plloutnum",plloutnum,"now",self.phasec[pllnum][plloutnum])
    def uppos(self): self.dophase(plloutnum=0,updown=1)
    def uppos1(self): self.dophase(plloutnum=1,updown=1)
    def uppos2(self): self.dophase(plloutnum=2,updown=1)
    def uppos3(self): self.dophase(plloutnum=3,updown=1)
    def uppos4(self): self.dophase(plloutnum=4,updown=1)
    def downpos(self): self.dophase(plloutnum=0,updown=0)
    def downpos1(self): self.dophase(plloutnum=1,updown=0)
    def downpos2(self): self.dophase(plloutnum=2,updown=0)
    def downpos3(self): self.dophase(plloutnum=3,updown=0)
    def downpos4(self): self.dophase(plloutnum=4,updown=0)

    def pllreset(self):
        usb = self.activeusb
        usb.send(bytes([5, 99, 99, 99, 100, 100, 100, 100]))
        tres = usb.recv(4)
        print("pllreset sent, got back:", tres[3], tres[2], tres[1], tres[0])
        self.phasec = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]] # reset counters
        #adjust other phases
        n = -1 # amount to adjust (+ or -)
        for i in range(abs(n)): self.dophase(2, n > 0, pllnum=0, quiet=(i != abs(n) - 1))  # adjust phase of c2, clkout
        n = -1  # amount to adjust (+ or -)
        for i in range(abs(n)): self.dophase(3, n > 0, pllnum=0, quiet=(i != abs(n) - 1))  # adjust phase of c3
        n = 0  # amount to adjust (+ or -)
        for i in range(abs(n)): self.dophase(4, n > 0, pllnum=0, quiet=(i != abs(n) - 1))  # adjust phase of c4

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

    downsample=0
    downsamplefactor=1
    highresval=1
    xscale=1
    xscaling=1
    yscale=16.
    min_y=-pow(2,11)
    max_y=pow(2,11)
    min_x=0
    max_x=4*10*expect_samples*downsamplefactor/nsunits/samplerate
    triggerlevel = 127
    triggerdelta = 4
    triggerpos = int(expect_samples * 128/256)
    triggertimethresh = 0
    triggerchan = 0
    def triggerlevelchanged(self,value):
        if value+self.triggerdelta < 256 and value-self.triggerdelta > 0:
            self.triggerlevel = value
            for usb in usbs: self.sendtriggerinfo(usb)
            self.drawtriggerlines()
    def triggerdeltachanged(self, value):
        if value+self.triggerlevel < 256 and self.triggerlevel-value > 0:
            self.triggerdelta=value
            for usb in usbs: self.sendtriggerinfo(usb)
    def triggerposchanged(self,value):
        self.triggerpos = int(self.expect_samples * value/256)
        for usb in usbs: self.sendtriggerinfo(usb)
        self.drawtriggerlines()
    def triggerchanchanged(self):
        self.triggerchan = self.ui.triggerChanBox.value()
        for usb in usbs: self.sendtriggerinfo(usb)
    def sendtriggerinfo(self,usb):
        usb.send(bytes([8, self.triggerlevel+1, self.triggerdelta, int(self.triggerpos/256), self.triggerpos%256, self.triggertimethresh, self.triggerchan, 100]))
        usb.recv(4)
    def drawtriggerlines(self):
        self.hline = (self.triggerlevel -127)* self.yscale
        self.otherlines[1].setData([self.min_x, self.max_x],[self.hline, self.hline])  # horizontal line showing trigger threshold
        point = self.triggerpos + 1.25
        self.vline = 2 * 10 * point * (self.downsamplefactor / self.nsunits / self.samplerate)
        if not self.data_twochannel: self.vline = self.vline * 2
        self.otherlines[0].setData([self.vline, self.vline], [max(self.hline + self.min_y / 2, self.min_y),min(self.hline + self.max_y / 2,self.max_y)])  # vertical line showing trigger time

    def tot(self):
        self.triggertimethresh = self.ui.totBox.value()
        for usb in usbs: self.sendtriggerinfo(usb)

    def rolling(self):
        if self.triggertype>0:
            self.oldtriggertype=self.triggertype
            self.triggertype=0
            self.ui.risingedgeCheck.setEnabled(False)
        else:
            self.triggertype=self.oldtriggertype
        if self.triggertype==1 or self.triggertype==2: self.ui.risingedgeCheck.setEnabled(True)
        self.ui.rollingButton.setChecked(self.triggertype>0)
        if self.triggertype>0: self.ui.rollingButton.setText("Normal")
        else: self.ui.rollingButton.setText("Auto")

    getone=False
    def single(self):
        self.getone = not self.getone
        self.ui.singleButton.setChecked(self.getone)

    downsamplemerging=1
    def highres(self,value):
        self.highresval=value>0
        #print("highres",self.highresval)
        self.telldownsample(self.activeusb, self.downsample)
    def telldownsample(self,usb,ds):
        if (ds-5)>31:
            print("downsample too large!")
            return
        self.downsample=ds
        if ds<0: ds=0
        if ds==0:
            ds=0
            self.downsamplemerging=1
        if ds==1:
            ds=0
            self.downsamplemerging=2
        if ds==2:
            ds=0
            self.downsamplemerging=4
        if ds==3:
            ds=0
            if not self.data_twochannel:
                self.downsamplemerging=8
            else:
                self.downsamplemerging=10
        if ds==4:
            ds=0
            self.downsamplemerging=20
        if not self.data_twochannel:
            if ds==5:
                ds=0
                self.downsamplemerging=40
            if ds>5:
                ds=ds-5
                self.downsamplemerging=40
        else:
            if ds>4:
                ds=ds-4
                self.downsamplemerging=20
        self.downsamplefactor = self.downsamplemerging*pow(2,ds)
        #print("ds, dsm, dsf",ds,self.downsamplemerging,self.downsamplefactor)
        usb.send(bytes([9, ds, self.highresval, self.downsamplemerging, 100, 100, 100, 100]))
        usb.recv(4)

    def timefast(self):
        amount=1
        modifiers = app.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            amount*=5
        self.telldownsample(self.activeusb, self.downsample-amount)
        self.timechanged()

    def timeslow(self):
        amount=1
        modifiers = app.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            amount*=5
        self.telldownsample(self.activeusb, self.downsample+amount)
        self.timechanged()

    units = "ns"
    def timechanged(self):
        self.max_x = 4 * 10 * self.expect_samples * (self.downsamplefactor / self.nsunits / self.samplerate)
        baremaxx = 4 * 10 * self.expect_samples * self.downsamplefactor / self.samplerate
        if baremaxx>5:
            self.nsunits = 1
            self.max_x = 4 * 10 * self.expect_samples * (self.downsamplefactor / self.nsunits / self.samplerate)
            self.units="ns"
        if baremaxx>5000:
            self.nsunits = 1000
            self.max_x = 4 * 10 * self.expect_samples * (self.downsamplefactor / self.nsunits / self.samplerate)
            self.units = "us"
        if baremaxx>5000000:
            self.nsunits = 1000000
            self.max_x = 4 * 10 * self.expect_samples * (self.downsamplefactor / self.nsunits / self.samplerate)
            self.units = "ms"
        if baremaxx>5000000000:
            self.nsunits = 1000000000
            self.max_x = 4 * 10 * self.expect_samples * (self.downsamplefactor / self.nsunits / self.samplerate)
            self.units = "s"
        self.ui.plot.setLabel('bottom', "Time ("+self.units+")")
        if self.data_overlapped:
            self.max_x = self.max_x/4
            for c in range(4):
                self.xydata[c][0] = np.array([range(0,10*self.expect_samples)])*(self.downsamplefactor / self.nsunits / self.samplerate)
        elif self.data_twochannel:
            self.max_x = self.max_x/2
            for c in range(self.num_chan_per_board*self.num_board):
                self.xydata[c][0] = np.array([range(0,2*10*self.expect_samples)])*(self.downsamplefactor / self.nsunits / self.samplerate)
        else:
            for c in range(self.num_board):
                self.xydata[0][0] = np.array([range(0, 4*10*self.expect_samples)])*(self.downsamplefactor / self.nsunits / self.samplerate)
        self.ui.plot.setRange(xRange=(self.min_x, self.max_x), padding=0.00)
        self.ui.plot.setRange(yRange=(self.min_y, self.max_y), padding=0.01)
        self.drawtriggerlines()
        self.ui.timebaseBox.setText("downsample "+str(self.downsample))

    def risingfalling(self):
        self.fallingedge=not self.ui.risingedgeCheck.checkState()
        if self.triggertype==1:
            if self.fallingedge: self.triggertype=2
        if self.triggertype==2:
            if not self.fallingedge: self.triggertype = 1

    dodrawing=True
    def drawing(self):
        if self.ui.drawingCheck.checkState() == QtCore.Qt.Checked:
            self.dodrawing=True
            #print("drawing now",self.dodrawing)
        else:
            self.dodrawing=False
            #print("drawing now",self.dodrawing)

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

        #other stuff
        self.ui.plot.setLabel('bottom',"Time (ns)")
        self.ui.plot.setLabel('left', "Voltage (ADC sample value)")
        self.ui.plot.setRange(yRange=(self.min_y,self.max_y),padding=0.01)
        for usb in usbs: self.telldownsample(usb, 0)
        self.timechanged()
        self.ui.plot.showGrid(x=True, y=True)

    def closeEvent(self, event):
        print("Handling closeEvent",event)
        self.timer.stop()
        self.timer2.stop()
        for usb in usbs: cleanup(usb)

    if data_overlapped:
        xydata = np.empty([int(num_chan_per_board * num_board), 2, 10*expect_samples], dtype=float)
    elif data_twochannel:
        xydata = np.empty([int(num_chan_per_board * num_board), 2, 2*10*expect_samples], dtype=float)
    else:
        xydata = np.empty([int(num_chan_per_board * num_board), 2, 4*10*expect_samples], dtype=float)

    statuscounter=0
    def updateplot(self):
        self.mainloop()
        self.statuscounter=self.statuscounter+1
        now = time.time()
        dt = now - self.lastTime + 0.00001
        self.lastTime = now
        if self.fps is None:
            self.fps = 1.0/dt
        else:
            s = np.clip(dt*3., 0, 1)
            self.fps = self.fps * (1-s) + (1.0/dt) * s
        if self.statuscounter%20==0: self.ui.statusBar.showMessage("%0.2f fps, %d events, %0.2f Hz, %0.2f MB/s"%(self.fps,self.nevents,self.lastrate,self.lastrate*self.lastsize/1e6))
        if not self.dodrawing: return
        #self.ui.plot.setTitle("%0.2f fps, %d events, %0.2f Hz, %0.2f MB/s"%(self.fps,self.nevents,self.lastrate,self.lastrate*self.lastsize/1e6))
        for li in range(self.nlines): self.lines[li].setData(self.xydata[li][0],self.xydata[li][1])
        app.processEvents()

    nevents=0
    oldnevents=0
    tinterval=100.
    oldtime=time.time()
    nbadclkA = 0
    nbadclkB = 0
    nbadclkC = 0
    nbadclkD = 0
    nbadstr = 0
    eventcounter=[]
    for n in range(num_board): eventcounter.append(0)

    def getchannels(self,usb,board):
        nsubsamples = 10*4 + 8+2  # extra 4 for clk+str, and 2 dead beef
        usb.send(bytes([1, self.triggertype, self.data_twochannel, 99] + inttobytes(self.expect_samples - self.triggerpos + 1)))  # length to take after trigger (last 4 bytes)
        triggercounter = usb.recv(4)  # get the 4 bytes
        #print("Got triggercounter", triggercounter[3], triggercounter[2], triggercounter[1], triggercounter[0])
        eventcountertemp = triggercounter[3]
        sample_triggered = 256+triggercounter[2]+triggercounter[1]
        print("sample triggered", binprint(triggercounter[2]), binprint(triggercounter[1]))
        acqstate = triggercounter[0]
        if acqstate == 251:  # an event is ready to be read out
            if eventcountertemp != self.eventcounter[board] + 1 and eventcountertemp != 0: #check event count, but account for rollover
                print("Event counter not incremented by 1?", eventcountertemp, self.eventcounter[board]," for board",board)
            self.eventcounter[board] = eventcountertemp

            expect_len = self.expect_samples * 2 * nsubsamples  # length to request: each adc bit is stored as 10 bits in 2 bytes
            usb.send(bytes([0, 99, 99, 99] + inttobytes(expect_len)))  # send the 4 bytes to usb
            data = usb.recv(expect_len)  # recv from usb
            rx_len = len(data)
        else:
            return 0

        self.total_rx_len += rx_len
        if expect_len != rx_len:
            print('*** expect_len (%d) and rx_len (%d) mismatch' % (expect_len, rx_len))

        else:
            if self.dofast: return rx_len
            self.nbadclkA = 0
            self.nbadclkB = 0
            self.nbadclkC = 0
            self.nbadclkD = 0
            self.nbadstr = 0
            for s in range(0, self.expect_samples):
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

                    if 40 <= n < 48:
                        strobe = val&0xaaaa
                        if strobe != 0:
                            if strobe!=8 and strobe!=128 and strobe!=2048 and strobe!=32768:
                                if strobe*4!=8 and strobe*4!=128 and strobe*4!=2048 and strobe*4!=32768:
                                    if self.debugstrobe: print("s=",s,"n=",n,"str",binprint(strobe),strobe)
                                    self.nbadstr=self.nbadstr+1

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
                        val = -val
                        if self.downsamplemerging==1:
                            samp = s * 10 + (9 - (n % 10)) # bits come out last to first in lvds receiver group of 10
                            #if s<(self.expect_samples-1): samp = samp + sample_triggered
                            if self.data_overlapped:
                                self.xydata[chan][1][samp] = val
                            elif self.data_twochannel:
                                if chan%2==0: chani=int(chan/2)
                                else: chani=int((chan-1)/2)
                                self.xydata[chan%2][1][chani+ 2*samp] = val
                            else:
                                self.xydata[0][1][chan+ 4*samp] = val
                        else:
                            if self.data_overlapped:
                                print("downsampling not supported in overlap mode yet")
                            elif self.data_twochannel:
                                samp = s * 20 + chan*10+9 - n
                                if n<20: samp = samp + 10
                                #if s < (self.expect_samples - 1): samp = samp + int(2*sample_triggered/self.downsamplefactor)
                                self.xydata[chan%2][1][samp] = val
                            else:
                                samp = s * 40 +39 - n
                                #if s < (self.expect_samples - 1): samp = samp + int(4*sample_triggered/self.downsamplefactor)
                                self.xydata[0][1][samp] = val
        if self.debug:
            time.sleep(.5)
            #oldbytes()
        if ((self.nbadclkA == 2*self.expect_samples or self.nbadclkB == 2*self.expect_samples or self.nbadclkC == 2*self.expect_samples or self.nbadclkD == 2*self.expect_samples)
                and self.phasec[0][2]<12): # adjust phase by 90 deg
            n = 6  # amount to adjust clkout (positive)
            for i in range(n): self.dophase(2, 1, pllnum=0, quiet=(i != n - 1))  # adjust phase of clkout
        return rx_len

    fitwidthfraction=0.2
    def drawtext(self): # happens once per second
        thestr = "Nbadclks A B C D "+str(self.nbadclkA)+" "+str(self.nbadclkB)+" "+str(self.nbadclkC)+" "+str(self.nbadclkD)
        thestr +="\n"+"Nbadstrobes "+str(self.nbadstr)
        thestr +="\n"+"Trigger threshold " + str(round(self.hline,3))
        thestr +="\n"+"Mean "+str(np.mean(self.xydata[0][1]).round(2))
        thestr +="\n"+"RMS "+str(np.std(self.xydata[0][1]).round(2))

        if not self.data_overlapped:
            p0 = [max(self.xydata[0][1]), self.vline-10, 20, min(self.xydata[0][1])]  # this is an initial guess
            fitwidth = (self.max_x - self.min_x)* self.fitwidthfraction
            x2 = self.xydata[0][0][(self.xydata[0][0] > self.vline-fitwidth) & (self.xydata[0][0] < self.vline+fitwidth)]  # only fit in range
            y2 = self.xydata[0][1][(self.xydata[0][0] > self.vline-fitwidth) & (self.xydata[0][0] < self.vline+fitwidth)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                popt, pcov = curve_fit(fit_rise, x2, y2, p0)
                perr = np.sqrt(np.diag(pcov))
            risetime=0.8 * popt[2]
            risetimeerr = perr[2]
            #print(popt)
            thestr +="\n"+"Rise time "+str(risetime.round(2))+"+-"+str(risetimeerr.round(2))+" "+self.units

        thestr += "\n" + gettemps(self.activeusb)

        self.ui.textBrowser.setText(thestr)

    def setup_connections(self,usb):
        print("Starting")
        oldbytes()

        usb.send(bytes([2, 0, 100, 100, 100, 100, 100, 100]))  # get version
        res = usb.recv(4)
        print("Version", res[3], res[2], res[1], res[0])

        board_setup(usb, self.dopattern, self.data_twochannel)
        return 1

    def init(self):
        oldactiveusb = self.activeusb
        for usb in usbs:
            self.activeusb = usb
            self.pllreset()
            self.adfreset()
        self.activeusb = oldactiveusb
        if self.data_overlapped:
            for c in range(self.num_chan_per_board):
                self.xydata[c][0] = np.array([range(0, 10*self.expect_samples)]) / self.nsunits / self.samplerate
        elif self.data_twochannel:
            for c in range(int(self.num_chan_per_board/2)):
                self.xydata[c][0] = np.array([range(0, 2*10*self.expect_samples)]) / self.nsunits / self.samplerate
        else:
            self.xydata[0][0] = np.array([range(0, 4*10*self.expect_samples)]) / self.nsunits /self.samplerate
        return 1

    lastrate=0
    lastsize=0
    def mainloop(self):
        if self.paused: time.sleep(.1)
        else:
            rx_len=0
            try:
                for board in range(self.num_board):
                    rx_len = rx_len + self.getchannels(usbs[board],board)
                if self.getone and rx_len>0:
                    self.dostartstop()
                    self.drawtext()
            except DeviceError:
                print("Device error")
                sys.exit(1)
            if self.db: print(time.time()-self.oldtime,"done with evt",self.nevents)
            if rx_len>0: self.nevents += 1
            if self.nevents-self.oldnevents >= self.tinterval:
                now=time.time()
                elapsedtime=now-self.oldtime
                self.oldtime=now
                self.lastrate = round(self.tinterval/elapsedtime,2)
                self.lastsize = rx_len
                if not self.dodrawing: print(self.nevents,"events,",self.lastrate,"Hz",round(self.lastrate*self.lastsize/1e6,3),"MB/s")
                if self.lastrate>40: self.tinterval=500.
                else: self.tinterval=100.
                self.oldnevents=self.nevents

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
        for usbi in usbs:
            if not win.setup_connections(usbi):
                print("Exiting now - failed setup_connections!")
                cleanup(usbi)
                sys.exit(1)
        if not win.init():
            print("Exiting now - failed init!")
            for usbi in usbs: cleanup(usbi)
            sys.exit()
        win.launch()
        for usbi in usbs: win.sendtriggerinfo(usbi)
        win.dostartstop()
    except DeviceError:
        print("device com failed!")
    if standalone:
        rv=app.exec_()
        sys.exit(rv)
    else:
        print("Done, but Qt window still active")
