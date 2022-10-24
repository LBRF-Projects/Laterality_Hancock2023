import os

import usb
import usb.backend.libusb1
import libusb_package as usbdll

from .constants import *
from .parsing import InputPacket, parse_data_packet, get_events

    
# Configure pyusb to use binary from libusb-package
usb.backend.libusb1.get_backend(find_library=usbdll.find_library)



def get_controllers():
    gamepads = []
    devices = usb.core.find(find_all=True)
    for d in devices:
        usb_id = '{0}:{1}'.format(d.idVendor, d.idProduct)
        if usb_id in VALID_IDS.keys():
            gamepads.append(d)
    return gamepads



class Controller360(object):

    def __init__(self, usb_device):
        self._dev = usb_device
        usb_id = '{0}:{1}'.format(self._dev.idVendor, self._dev.idProduct)
        self.name = VALID_IDS[usb_id]
        
        self._data = []
        self._events = []
        self._last_data = InputPacket(0, 0, 0, 0, 0, 0, 0)

        usb.util.claim_interface(self._dev, 0)
        self._dev.set_configuration()
        self._pad_in = self._dev[PAD_CONFIG][CTRL_INTERFACE][0]
        self._pad_out = self._dev[PAD_CONFIG][CTRL_INTERFACE][1]

    def __del__(self):
        if self._dev is not None:
            try:
                self.disconnect()
            except:
                pass
        
    def _send_cmd(self, cmd):
        self._pad_out.write(cmd, timeout=0)

    def set_led(self, led_mode):
        self._send_cmd(b"\x01\x03" + led_mode)
        
    def set_rumble(self, left=0, right=0):
        cmd = b"\x00\x08\x00" + bytearray([left, right]) + b"\x00\x00\x00"
        self._send_cmd(cmd)
        
    def update(self):
        data = None
        while True:
            try:
                data = self._pad_in.read(32, timeout=5)
                break
            except usb.core.USBError:
                break
        if data is not None:
            new = bytearray(data)
            if new[:2] == b'\x00\x14':
                p = parse_data_packet(new)
                self._data.append(p)
                self._events += get_events(self._last_data, p)
                self._last_data = p

    def get_data(self):
        dat = self._data
        self._data = []
        return dat

    def get_button_events(self):
        events = self._events
        self._events = []
        return events

    def left_stick(self):
        return (self._last_data.lx, self._last_data.ly)

    def right_stick(self):
        return (self._last_data.rx, self._last_data.ry)

    def left_trigger(self):
        return self._last_data.lt

    def right_trigger(self):
        return self._last_data.rt

    def button_state(self, button):
        bit = 0x1 >> button
        return int(self._last_data.buttons & bit > 0)

    def disconnect(self):
        usb.util.release_interface(self._dev, 0)
        self._dev = None
