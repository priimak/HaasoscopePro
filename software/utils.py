def binprint(x):
    return bin(x)[2:].zfill(8)

# get bit n from byte i
def getbit(i, n):
    return (i >> n) & 1

def bytestoint(thebytes):
    return thebytes[0] + pow(2, 8) * thebytes[1] + pow(2, 16) * thebytes[2] + pow(2, 24) * thebytes[3]

def oldbytes(usbs):
    for usb in usbs:
        olddata = usb.recv(10000000)
        print("Got", len(olddata), "old bytes")
        if len(olddata) == 0: break
        print("Old byte0:", olddata[0])

def inttobytes(theint):  # convert length number to a 4-byte byte array (with type of 'bytes')
    return [theint & 0xff, (theint >> 8) & 0xff, (theint >> 16) & 0xff, (theint >> 24) & 0xff]

