# This program is a test of FPGA+FTDI USB chips (FT232H, FT600, or FT601)
# It sends 4 bytes to FTDI chip, and the FPGA will treat these 4 bytes as a length.
# Then the FPGA sends bytes of length to the computer, and the program should receive these bytes.

# The corresponding FPGA top-level design can be found in fpga_top_ft232h_tx_mass.v (if you are using FT232H or FT2232H chips)
# Or see fpga_top_ft600_rx_mass.v (if you are using an FT600 chip)

from USB_FTX232H_FT60X import USB_FTX232H_FT60X_sync245mode # see USB_FTX232H_FT60X.py
from random import randint
import time

def binprint(x):
    return bin(x)[2:].zfill(8)
def oldbytes():
    while True:
        olddata = usb.recv(10000000)
        print("Got",len(olddata),"old bytes")
        if len(olddata)==0: break
        print("Old byte0:",olddata[0])

def spicommand(name,first,second,third,read,bin=False):
    cs = 1  # which chip to select, ignored for now
    # first byte to send, start of address
    # second byte to send, rest of address
    # third byte to send, value to write, ignored during read
    if read: first = first + 0x80 #set the highest bit for read, i.e. add 0x80
    usb.send(bytes([3, cs, first, second, third, 100, 100, 100]))  # get SPI result from command
    spires = usb.recv(4)
    if read:
        if bin: print("SPI read:"+name, "(",hex(first),hex(second),")",binprint(spires[0]))
        else: print("SPI read:"+name, "(",hex(first),hex(second),")",hex(spires[0]))
    else: print("SPI write:"+name, "(",hex(first),hex(second),")",hex(third))

def spicommand2(name,first,second,third,fourth,read):
    cs = 1  # which chip to select, ignored for now
    # first byte to send, start of address
    # second byte to send, rest of address
    # third byte to send, value to write, ignored during read, to address +1 (the higher 8 bits)
    # fourth byte to send, value to write, ignored during read
    if read: first = first + 0x80  # set the highest bit for read, i.e. add 0x80
    usb.send(bytes([3, cs, first, second, fourth, 100, 100, 100]))  # get SPI result from command
    spires = usb.recv(4)
    usb.send(bytes([3, cs, first, second+0x01, third, 100, 100, 100]))  # get SPI result from command for next byte
    spires2 = usb.recv(4)
    if read: print("SPI read:"+name, "(",hex(first),hex(second),")",hex(spires2[0]),hex(spires[0]))
    else: print("SPI write:"+name, "(",hex(first),hex(second),")",hex(fourth),hex(third))

TEST_COUNT = 100000
if __name__ == '__main__':
    usb = USB_FTX232H_FT60X_sync245mode(device_to_open_list=
        (('FTX232H', 'Haasoscope USB2'),
         ('FTX232H', 'USB <-> Serial Converter'),           # firstly try to open FTX232H (FT232H or FT2232H) device named 'USB <-> Serial Converter'. Note that 'USB <-> Serial Converter' is the default name of FT232H or FT2232H chip unless the user has modified it. If the chip's name has been modified, you can use FT_Prog software to look up it.
         ('FT60X', 'FTDI SuperSpeed-FIFO Bridge'))           # secondly try to open FT60X (FT600 or FT601) device named 'FTDI SuperSpeed-FIFO Bridge'. Note that 'FTDI SuperSpeed-FIFO Bridge' is the default name of FT600 or FT601 chip unless the user has modified it.
    )

    print("Starting")
    oldbytes()

    usb.send(bytes([2, 99, 99, 99, 100, 100, 100, 100])) #get version
    res = usb.recv(4)
    print("Version",res[3],res[2],res[1],res[0])

    spicommand2("VENDOR", 0x00, 0x0c, 0x00, 0x00, True)
    spicommand("LVDS_EN", 0x02, 0x00, 0x00, False) #disable LVDS interface
    spicommand("CAL_EN", 0x00, 0x61, 0x00, False)  # disable calibration
    spicommand("LMODE",0x02,0x01,0x01,False) # LVDS mode

    #spicommand("SYNC_SEL",0x02,0x01,0x0a,False) # use LSYNC_N (software), 2's complement
    spicommand("SYNC_SEL",0x02,0x01,0x08,False) # use LSYNC_N (software), offset binary

    spicommand("SYNC_SEL", 0x00, 0x60, 0x11, False)  # swap inputs
    #spicommand("SYNC_SEL", 0x00, 0x60, 0x01, False)  # unswap inputs

    dotest=False
    if dotest:
        spicommand("PAT_SEL", 0x02, 0x05, 0x11, False)  # test pattern
        usrval=0x00
        spicommand2("UPAT0", 0x01, 0x80, usrval+0x0f, usrval+0xff,False)  # set pattern sample 0
        spicommand2("UPAT1", 0x01, 0x82, usrval+0x0f, usrval+0xff, False)  # set pattern sample 1
        spicommand2("UPAT2", 0x01, 0x84, usrval, usrval, False)  # set pattern sample 2
        spicommand2("UPAT3", 0x01, 0x86, usrval, usrval, False)  # set pattern sample 3
        spicommand2("UPAT4", 0x01, 0x88, usrval, usrval, False)  # set pattern sample 4
        spicommand2("UPAT5", 0x01, 0x8a, usrval, usrval, False)  # set pattern sample 5
        spicommand2("UPAT6", 0x01, 0x8c, usrval, usrval, False)  # set pattern sample 6
        spicommand2("UPAT7", 0x01, 0x8e, usrval, usrval, False)  # set pattern sample 7
        spicommand("UPAT_CTRL", 0x01, 0x90, 0x0e, False)  # set lane pattern to user
    else:
        spicommand("PAT_SEL", 0x02, 0x05, 0x02, False)  # normal ADC data
        spicommand("UPAT_CTRL", 0x01, 0x90, 0x1e, False)  # set lane pattern to default

    spicommand("CAL_EN", 0x00, 0x61, 0x01, False)  # enable calibration
    spicommand("LVDS_EN", 0x02, 0x00, 0x01, False)  # enable LVDS interface
    spicommand("LSYNC_N",0x02,0x03,0x00,False) #assert ~sync signal
    spicommand("LSYNC_N",0x02,0x03,0x01,False) #deassert ~sync signal
    #spicommand("CAL_SOFT_TRIG", 0x00, 0x6c, 0x00, False)
    #spicommand("CAL_SOFT_TRIG", 0x00, 0x6c, 0x01, False)

    debug=False
    total_rx_len = 0
    time_start = time.time()
    for i in range (TEST_COUNT):
        expect_len = 50000 # randint(1, 10000000) # length to request
        if debug: print(expect_len%256) # length in first byte
        txdata = bytes( [ 0,99,99,99,
            expect_len&0xff, (expect_len>>8)&0xff, (expect_len>>16)&0xff, (expect_len>>24)&0xff ] ) # convert length number to a 4-byte byte array (with type of 'bytes')
        usb.send(txdata) # send the 4 bytes to usb
        data = usb.recv(expect_len) # recv from usb
        rx_len = len(data)
        if debug:
            print(data[3],data[2],data[1],data[0])
        for p in range(1,1000):
            print(bin(data[4*p+3])[2:].zfill(8),binprint(data[4*p+2]),bin(data[4*p+1])[2:].zfill(8),bin(data[4*p+0])[2:].zfill(8))
        total_rx_len += rx_len
        time_total = time.time() - time_start
        data_rate = total_rx_len / (time_total + 0.001) / 1e3
        evt_rate = i / (time_total + 0.001)
        if i%2==0: print('[%d/%d]   rx_len=%d   total_rx_len=%d   avg_evt_rate=%f Hz   avg_data_rate=%.0f kB/s' % (i, TEST_COUNT, rx_len, total_rx_len, evt_rate, data_rate) )
        if expect_len != rx_len:
            print('*** expect_len (%d) and rx_len (%d) mismatch' % (expect_len, rx_len) )
            break
        time.sleep(1)

    usb.close()
