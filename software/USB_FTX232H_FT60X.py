def open_ft_usb_device(device_type, device_name, port):
    b_device_name = bytes(device_name, encoding="ASCII")
    try:
        import ftd2xx  # import #
    except:
        return None, 'Failed to import ftd2xx'
    for i in range(16):
        try:
            usb = ftd2xx.open(i)
        except:
            continue
        if usb.description != b_device_name:
            usb.close()
            continue
        usb.setBitMode(0xff, 0x40)
        print(usb.getDeviceInfo())
        print(usb.getComPortNumber())
        if port==usb.getComPortNumber():
            return usb, 'Successfully opened %s USB device: %s %s' % (device_type, device_name, port)
    return None, 'Could not open %s USB device: %s %s' % (device_type, device_name, port)

class USB_FTX232H_sync245mode:

    def __init__(self, device_type, device_name, port):
        usb, message = open_ft_usb_device(device_type, device_name, port)
        print(message)
        if usb is not None:
            self.device_type = device_type
            self.device_name = device_name
            self.port = port
            self._usb = usb
            self._recv_timeout = 2000
            self._send_timeout = 2000
            self.set_recv_timeout(self._recv_timeout)
            self.set_send_timeout(self._send_timeout)
            self._chunk = 65536
            usb.setUSBParameters(self._chunk * 4, self._chunk * 4)
        else:
            raise Exception('Could not open USB device on port', port)

    def close(self):
        self._usb.close()
        self._usb = None

    def set_latencyt(self, latency):
        self._usb.setLatencyTimer(latency)

    def set_recv_timeout(self, timeout):
        self._recv_timeout = timeout
        self._usb.setTimeouts(self._recv_timeout, self._send_timeout)

    def set_send_timeout(self, timeout):
        self._send_timeout = timeout
        self._usb.setTimeouts(self._recv_timeout, self._send_timeout)

    def send(self, data):
        txlen = 0
        for si in range(0, len(data), self._chunk):
            ei = si + self._chunk
            ei = min(ei, len(data))
            chunk = data[si:ei]
            txlen_once = self._usb.write(chunk)
            txlen += txlen_once
            if txlen_once < len(chunk):
                break
        return txlen

    def recv(self, recv_len):
        data = b''
        for si in range(0, recv_len, self._chunk):
            ei = si + self._chunk
            ei = min(ei, recv_len)
            chunk_len = ei - si
            chunk = self._usb.read(chunk_len)
            data += chunk
            if len(chunk) < chunk_len:
                break
        return data
