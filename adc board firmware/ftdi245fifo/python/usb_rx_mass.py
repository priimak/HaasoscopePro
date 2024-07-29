# This program is a test of FPGA+FTDI USB chips (FT232H, FT600, or FT601)
# It sends 4 bytes to FTDI chip, and the FPGA will treat these 4 bytes as a length.
# Then the FPGA sends bytes of length to the computer, and the program should receive these bytes.

# The corresponding FPGA top-level design can be found in fpga_top_ft232h_tx_mass.v (if you are using FT232H or FT2232H chips)
# Or see fpga_top_ft600_rx_mass.v (if you are using an FT600 chip)

from USB_FTX232H_FT60X import USB_FTX232H_FT60X_sync245mode # see USB_FTX232H_FT60X.py
from random import randint
import time

def oldbytes():
    while True:
        olddata = usb.recv(10000000)
        print("got",len(olddata),"old bytes")
        if len(olddata)==0: break
        print("old byte0:",olddata[0])

TEST_COUNT = 10
if __name__ == '__main__':
    usb = USB_FTX232H_FT60X_sync245mode(device_to_open_list=
        (('FTX232H', 'Haasoscope USB2'),
         ('FTX232H', 'USB <-> Serial Converter'),           # firstly try to open FTX232H (FT232H or FT2232H) device named 'USB <-> Serial Converter'. Note that 'USB <-> Serial Converter' is the default name of FT232H or FT2232H chip unless the user has modified it. If the chip's name has been modified, you can use FT_Prog software to look up it.
         ('FT60X', 'FTDI SuperSpeed-FIFO Bridge'))           # secondly try to open FT60X (FT600 or FT601) device named 'FTDI SuperSpeed-FIFO Bridge'. Note that 'FTDI SuperSpeed-FIFO Bridge' is the default name of FT600 or FT601 chip unless the user has modified it.
    )

    print("starting")
    oldbytes()

    usb.send(bytes([2, 99, 99, 99, 100, 100, 100, 100])) #get version
    res = usb.recv(4)
    print("version",res[3],res[2],res[1],res[0])

    cs=1 #which chip to select, ignored for now
    first=0x80 #first byte to send
    second=0x0c #second byte to send (device id byte 0, should return "4", 0x0d should return "51")
    third=0 #third byte to send, ignored during read
    usb.send(bytes([3, cs, first, second, third, 100, 100, 100]))  # get SPI from command
    res = usb.recv(4)
    print("SPI read", res[3], res[2], res[1], res[0])

    debug=True
    total_rx_len = 0
    time_start = time.time()
    for i in range (TEST_COUNT):
        expect_len = randint(1, 10000000) # length to request
        if debug: print(expect_len%256) # length in first byte
        txdata = bytes( [ 0,99,99,99, expect_len&0xff, (expect_len>>8)&0xff, (expect_len>>16)&0xff, (expect_len>>24)&0xff ] )   # convert length number to a 4-byte byte array (with type of 'bytes')
        usb.send(txdata)                                                                                            # send the 4 bytes to usb
        data = usb.recv(expect_len)                                                                                 # recv from usb
        rx_len = len(data)
        if debug: print(data[0],data[1],data[2],data[3])
        total_rx_len += rx_len
        time_total = time.time() - time_start
        data_rate = total_rx_len / (time_total + 0.001) / 1e3
        evt_rate = i / (time_total + 0.001)
        if i%2==0: print('[%d/%d]   rx_len=%d   total_rx_len=%d   avg_evt_rate=%f Hz   avg_data_rate=%.0f kB/s' % (i, TEST_COUNT, rx_len, total_rx_len, evt_rate, data_rate) )
        if expect_len != rx_len:
            print('*** expect_len (%d) and rx_len (%d) mismatch' % (expect_len, rx_len) )
            break

    usb.close()
