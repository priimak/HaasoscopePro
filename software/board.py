import time
from spi import *
from utils import *
from adf435x_core import *

def adf4350(usb, freq, phase, r_counter=1, divided=FeedbackSelect.Divider, ref_doubler=False, ref_div2=True, themuxout=False):
    print('ADF4350 being set to %0.2f MHz' % freq)
    if not themuxout:
        print("muxout GND 0")
    else:
        print("muxout VCC 1")
    INT, MOD, FRAC, output_divider, band_select_clock_divider = (calculate_regs(
        device_type=DeviceType.ADF4350, freq=freq, ref_freq=50.0,
        band_select_clock_mode=BandSelectClockMode.Low,
        feedback_select=divided,
        r_counter=r_counter,  # needed when using FeedbackSelect.Divider (needed for phase resync?!)
        ref_doubler=ref_doubler, ref_div2=ref_div2, enable_gcd=True))
    print("INT", INT, "MOD", MOD, "FRAC", FRAC, "outdiv", output_divider, "bandselclkdiv", band_select_clock_divider)
    regs = make_regs(
        INT=INT, MOD=MOD, FRAC=FRAC, output_divider=output_divider,
        band_select_clock_divider=band_select_clock_divider, r_counter=r_counter, ref_doubler=ref_doubler,
        ref_div_2=ref_div2,
        device_type=DeviceType.ADF4350, phase_value=phase, mux_out=themuxout, charge_pump_current=2.50,
        feedback_select=divided, pd_polarity=PDPolarity.Positive, prescaler='4/5',
        band_select_clock_mode=BandSelectClockMode.Low,
        clk_div_mode=ClkDivMode.ResyncEnable, clock_divider_value=1000, csr=False,
        aux_output_enable=False, aux_output_power=-4.0, output_enable=True, output_power=-4.0)  # (-4,-1,2,5)
    # values can also be computed using free Analog Devices ADF435x Software:
    # https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/eval-adf4351.html#eb-relatedsoftware
    spimode(usb, 0)
    for r in reversed(range(len(regs))):
        # regs[2]=0x5004E42 #to override from ADF435x software
        print("adf4350 reg", r, binprint(regs[r]), hex(regs[r]))
        fourbytes = inttobytes(regs[r])
        # for i in range(4): print(binprint(fourbytes[i]))
        spicommand(usb, "ADF4350 Reg " + str(r), fourbytes[3], fourbytes[2], fourbytes[1], False, fourth=fourbytes[0],
                   cs=3, nbyte=4)  # was cs=2 on alpha board v1.11
    spimode(usb, 0)

def board_setup(usb, dopattern, twochannel, dooverrange):
    setfan(usb, True)

    spimode(usb, 0)
    spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x00, False)  # power up
    # spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x03, False) # power down
    spicommand2(usb, "VENDOR", 0x00, 0x0c, 0x00, 0x00, True)
    spicommand(usb, "LVDS_EN", 0x02, 0x00, 0x00, False)  # disable LVDS interface
    spicommand(usb, "CAL_EN", 0x00, 0x61, 0x00, False)  # disable calibration

    if twochannel:
        spicommand(usb, "LMODE", 0x02, 0x01, 0x03, False)  # LVDS mode: aligned, demux, dual channel, 12-bit
        # spicommand("LMODE", 0x02, 0x01, 0x01, False)  # LVDS mode: staggered, demux, dual channel, 12-bit
    else:
        spicommand(usb, "LMODE", 0x02, 0x01, 0x07, False)  # LVDS mode: aligned, demux, single channel, 12-bit
        # spicommand(usb, "LMODE", 0x02, 0x01, 0x37, False)  # LVDS mode: aligned, demux, single channel, 8-bit
        # spicommand(usb, "LMODE", 0x02, 0x01, 0x05, False)  # LVDS mode: staggered, demux, single channel, 12-bit

    spicommand(usb, "LVDS_SWING", 0x00, 0x48, 0x00, False)  # high swing mode
    # spicommand(usb, "LVDS_SWING", 0x00, 0x48, 0x01, False)  #low swing mode

    spicommand(usb, "LCTRL", 0x02, 0x04, 0x0a, False)  # use LSYNC_N (software), 2's complement
    # spicommand(usb, "LCTRL", 0x02, 0x04, 0x08, False)  # use LSYNC_N (software), offset binary

    spicommand(usb, "INPUT_MUX", 0x00, 0x60, 0x12, False)  # swap inputs
    # spicommand(usb, "INPUT_MUX", 0x00, 0x60, 0x01, False)  # unswap inputs

    # spicommand(usb, "TAD", 0x02, 0xB7, 0x01, False)  # invert clk
    spicommand(usb, "TAD", 0x02, 0xB7, 0x00, False)  # don't invert clk

    tad=0
    spicommand(usb, "TAD", 0x02, 0xB6, tad, False)  # adjust TAD (time of ADC relative to clk)

    if dooverrange:
        spicommand(usb, "OVR_CFG", 0x02, 0x13, 0x0f, False)  # overrange on
        spicommand(usb, "OVR_T0", 0x02, 0x11, 0xf2, False)  # overrange threshold 0
        spicommand(usb, "OVR_T1", 0x02, 0x12, 0xab, False)  # overrange threshold 1
    else:
        spicommand(usb, "OVR_CFG", 0x02, 0x13, 0x07, False)  # overrange off

    if dopattern:
        spicommand(usb, "PAT_SEL", 0x02, 0x05, 0x11, False)  # test pattern
        usrval = 0x00
        usrval3 = 0x0f
        usrval2 = 0xff
        spicommand2(usb, "UPAT0", 0x01, 0x80, usrval3, usrval2, False)  # set pattern sample 0
        spicommand2(usb, "UPAT1", 0x01, 0x82, usrval, usrval, False)  # set pattern sample 1
        spicommand2(usb, "UPAT2", 0x01, 0x84, usrval, usrval, False)  # set pattern sample 2
        spicommand2(usb, "UPAT3", 0x01, 0x86, usrval, usrval, False)  # set pattern sample 3
        spicommand2(usb, "UPAT4", 0x01, 0x88, usrval, usrval, False)  # set pattern sample 4
        spicommand2(usb, "UPAT5", 0x01, 0x8a, usrval, usrval, False)  # set pattern sample 5
        spicommand2(usb, "UPAT6", 0x01, 0x8c, usrval, usrval, False)  # set pattern sample 6
        spicommand2(usb, "UPAT7", 0x01, 0x8e, usrval, usrval, False)  # set pattern sample 7
        # spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x0e, False)  # set lane pattern to user, invert a bit of B C D
        spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x00, False)  # set lane pattern to user
    else:
        spicommand(usb, "PAT_SEL", 0x02, 0x05, 0x02, False)  # normal ADC data
        spicommand(usb, "UPAT_CTRL", 0x01, 0x90, 0x1e, False)  # set lane pattern to default

    spicommand(usb, "CAL_EN", 0x00, 0x61, 0x01, False)  # enable calibration
    spicommand(usb, "LVDS_EN", 0x02, 0x00, 0x01, False)  # enable LVDS interface
    spicommand(usb, "LSYNC_N", 0x02, 0x03, 0x00, False)  # assert ~sync signal
    spicommand(usb, "LSYNC_N", 0x02, 0x03, 0x01, False)  # deassert ~sync signal
    # spicommand(usb, "CAL_SOFT_TRIG", 0x00, 0x6c, 0x00, False)
    # spicommand(usb, "CAL_SOFT_TRIG", 0x00, 0x6c, 0x01, False)

    spimode(usb, 0)
    spicommand(usb, "Amp Rev ID", 0x00, 0x00, 0x00, True, cs=1, nbyte=2)
    spicommand(usb, "Amp Prod ID", 0x01, 0x00, 0x00, True, cs=1, nbyte=2)
    spicommand(usb, "Amp Rev ID", 0x00, 0x00, 0x00, True, cs=2, nbyte=2)
    spicommand(usb, "Amp Prod ID", 0x01, 0x00, 0x00, True, cs=2, nbyte=2)

    spimode(usb, 1)
    spicommand(usb, "DAC ref on", 0x38, 0xff, 0xff, False, cs=4)
    spicommand(usb, "DAC gain 1", 0x02, 0xff, 0xff, False, cs=4)
    spimode(usb, 0)
    dooffset(usb, 0, 0)
    dooffset(usb, 1, 0)
    setgain(usb, 0, 0)
    setgain(usb, 1, 0)

def setgain(usb, chan, value):
    spimode(usb, 0)
    # 00 to 20 is 26 to -6 dB, 0x1a is no gain
    if chan == 1: spicommand(usb, "Amp Gain 0", 0x02, 0x00, 26 - value, False, cs=2, nbyte=2)
    if chan == 0: spicommand(usb, "Amp Gain 1", 0x02, 0x00, 26 - value, False, cs=1, nbyte=2)

def dooffset(usb, chan, val):  # val goes from -100% to 100%
    spimode(usb, 1)
    dacval = int((pow(2, 16) - 1) * (val / 2 + 50) / 100)
    # print("dacval is", dacval)
    if chan == 0: spicommand(usb, "DAC 1 value", 0x18, dacval >> 8, dacval % 256, False, cs=4, quiet=True)
    if chan == 1: spicommand(usb, "DAC 2 value", 0x19, dacval >> 8, dacval % 256, False, cs=4, quiet=True)
    spimode(usb, 0)

def fit_rise(x, top, left, leftplus, bot):  # a function for fitting to find risetime
    val = bot + (x - left) * (top - bot) / leftplus
    inbottom = (x <= left)
    val[inbottom] = bot
    intop = (x >= (left + leftplus))
    val[intop] = top
    return val

def clockswitch(usb, board, quiet):
    usb.send(bytes([7, 0, 0, 0, 99, 99, 99, 99]))
    clockinfo = usb.recv(4)
    if quiet: return
    print("Clockinfo for board", board, binprint(clockinfo[1]), binprint(clockinfo[0]))
    if getbit(clockinfo[1], 1) and not getbit(clockinfo[1], 3):
        print("Board", board, "locked to ext board")
    else:
        print("Board", board, "locked to internal clock")

def setchanimpedance(usb, chan, onemeg):
    if chan == 1:
        controlbit = 0
    elif chan == 0:
        controlbit = 4
    else:
        return
    usb.send(bytes([10, controlbit, onemeg, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("1M for chan", chan, onemeg)

def setchanacdc(usb, chan, ac):
    if chan == 1:
        controlbit = 1
    elif chan == 0:
        controlbit = 5
    else:
        return
    usb.send(bytes([10, controlbit, not ac, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("AC for chan", chan, ac)

def setchanatt(usb, chan, att):
    if chan == 1:
        controlbit = 2
    elif chan == 0:
        controlbit = 6
    else:
        return
    usb.send(bytes([10, controlbit, att, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("Att for chan", chan, att)

def setsplit(usb, split):
    controlbit = 7
    usb.send(bytes([10, controlbit, split, 0, 0, 0, 0, 0]))
    usb.recv(4)
    print("Split", split)

def boardinbits(usb):
    usb.send(bytes([2, 1, 0, 100, 100, 100, 100, 100]))  # get board in
    res = usb.recv(4)
    print("Board in bits", res[0], binprint(res[0]))
    return res[0]

def setfan(usb,fanon):
    usb.send(bytes([2, 6, fanon, 100, 100, 100, 100, 100]))  # set / get fan status
    res = usb.recv(4)
    print("Set fan", fanon, "and it was",res[0])

def cleanup(usb):
    spimode(usb, 0)
    spicommand(usb, "DEVICE_CONFIG", 0x00, 0x02, 0x03, False)  # power down
    setfan(usb,False)
    return 1

def getoverrange(usb):
    if dooverrange:
        usb.send(bytes([2, 2, 0, 100, 100, 100, 100, 100]))  # get overrange 0
        res = usb.recv(4)
        print("Overrange0", res[3], res[2], res[1], res[0])

def gettemps(usb):
    spimode(usb, 0)
    spicommand(usb, "SlowDAC1", 0x00, 0x00, 0x00, True, cs=6, nbyte=2,
               quiet=True)  # first conversion may be for old input
    slowdac1 = spicommand(usb, "SlowDAC1", 0x00, 0x00, 0x00, True, cs=6, nbyte=2, quiet=True)
    slowdac1amp = 4.0
    slowdac1V = (256 * slowdac1[1] + slowdac1[0]) * 3300 / pow(2, 12) / slowdac1amp
    spicommand(usb, "SlowDAC2", 0x08, 0x00, 0x00, True, cs=6, nbyte=2,
               quiet=True)  # first conversion may be for old input
    slowdac2 = spicommand(usb, "SlowDAC2", 0x08, 0x00, 0x00, True, cs=6, nbyte=2, quiet=True)
    slowdac2amp = 2.0  # 1.1 in new board
    slowdac2V = (256 * slowdac2[1] + slowdac2[0]) * 3300 / pow(2, 12) / slowdac2amp
    return "Temp voltages (ADC Board): " + str(round(slowdac1V, 2)) + " " + str(round(slowdac2V, 2))

