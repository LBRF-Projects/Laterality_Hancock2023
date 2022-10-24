import threading

import sdl2
import sdl2.ext

import py360
from py360.constants import *

from gamepad import get_controllers, GameController, _get_joystick_info


BUTTON_MAP = {
    BUTTON_LB: sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
    BUTTON_RB: sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
    BUTTON_XBOX: sdl2.SDL_CONTROLLER_BUTTON_GUIDE,
    BUTTON_A: sdl2.SDL_CONTROLLER_BUTTON_A,
    BUTTON_B: sdl2.SDL_CONTROLLER_BUTTON_B,
    BUTTON_X: sdl2.SDL_CONTROLLER_BUTTON_X,
    BUTTON_Y: sdl2.SDL_CONTROLLER_BUTTON_Y,
    BUTTON_UP: sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,
    BUTTON_DOWN: sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
    BUTTON_LEFT: sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
    BUTTON_RIGHT: sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
    BUTTON_START: sdl2.SDL_CONTROLLER_BUTTON_START,
    BUTTON_BACK: sdl2.SDL_CONTROLLER_BUTTON_BACK,
    BUTTON_LEFTSTICK: sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,
    BUTTON_RIGHTSTICK: sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,
}

AXIS_MAP = {
    AXIS_LT: sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT, 
    AXIS_RT: sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
    AXIS_LEFTX: sdl2.SDL_CONTROLLER_AXIS_LEFTX,
    AXIS_LEFTY: sdl2.SDL_CONTROLLER_AXIS_LEFTY,
    AXIS_RIGHTX: sdl2.SDL_CONTROLLER_AXIS_RIGHTX,
    AXIS_RIGHTY: sdl2.SDL_CONTROLLER_AXIS_RIGHTY,
}


def get_all_controllers():
    # Try getting SDL2 controllers, fall back to PyUSB if available
    connected = get_controllers()
    if not len(connected):
        connected_usb = py360.get_controllers()
        if len(connected_usb):
            pad = Virtual360Controller(connected_usb[0])
            connected.append(pad)
    return connected


def update_thread(pad, vstick):
    while (pad._dev != None):
        pad.update()
        # Update button states
        events = pad.get_button_events()
        for e in events:
            b = BUTTON_MAP[e.name]
            sdl2.SDL_JoystickSetVirtualButton(vstick, b, e.state)
        # Update axis states
        data = pad.get_data()
        for d in data:
            for axis in ALL_AXES:
                a = AXIS_MAP[axis]
                value = d[axis + 1]
                if axis in [AXIS_LEFTY, AXIS_RIGHTY]:
                    value = -(value + 1)
                if axis in [AXIS_LT, AXIS_RT]:
                    value = int(value * 257) - 32768
                sdl2.SDL_JoystickSetVirtualAxis(vstick, a, value)


class Virtual360Controller(GameController):

    def __init__(self, usb_device):
        self._pad = None
        self._stick = None
        self._index = self._init_virtual()
        self._info = _get_joystick_info(self._index)

        self._usb_dev = usb_device
        self.usb_pad = None
        self._update_thread = None

    def _init_virtual(self):
        n_axes = 6
        n_buttons = 15
        n_hats = 0
        return sdl2.SDL_JoystickAttachVirtual(
            sdl2.SDL_JOYSTICK_TYPE_GAMECONTROLLER, n_axes, n_buttons, n_hats
        )

    def initialize(self):
        self.usb_pad = py360.Controller360(self._usb_dev)
        self.usb_pad.set_led(LED_OFF)
        GameController.initialize(self)
        #self._update_thread = threading.Thread(
        #    target=update_thread, args=(self.usb_pad, self._stick), daemon=True
        #)
        #self._update_thread.start()

    def close(self):
        self.usb_pad.disconnect()
        #self._update_thread.join()
        GameController.close(self)

    def update(self):
        #return None
        self.usb_pad.update()
        events = self.usb_pad.get_button_events()
        for e in events:
            b = BUTTON_MAP[e.name]
            sdl2.SDL_JoystickSetVirtualButton(self._stick, b, e.state)
        data = self.usb_pad.get_data()
        for d in data:
            for axis in ALL_AXES:
                a = AXIS_MAP[axis]
                value = d[axis + 1]
                if axis in [AXIS_LEFTY, AXIS_RIGHTY]:
                    value = -(value + 1)
                if axis in [AXIS_LT, AXIS_RT]:
                    value = int(value * 257) - 32768
                sdl2.SDL_JoystickSetVirtualAxis(self._stick, a, value)
