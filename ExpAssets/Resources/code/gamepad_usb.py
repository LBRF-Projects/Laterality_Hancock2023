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


class Virtual360Controller(GameController):
    """A GameController implementation for Xbox 360 controllers via pyusb.

    This class is an implementation of the SDL2-based GameController class that
    parses raw USB packets from Xbox 360 wired controllers and passes them to
    SDL2 as GameController events. This is necessary to use 360 controllers on
    modern macOS, which does not natively support 360 controllers and has broken
    compatibility with the popular 3rd-party driver.

    The key difference in functionality between this class and the regular
    GameController class is that `self.update()` needs to be called explicitly
    to pass controller events to SDL2 when processing input (e.g. waiting for a
    button press event), whereas this happens automatically in the background
    for controllers supported natively by SDL2.

    Both Windows & Linux have native support for wired 360 controllers in SDL2,
    so no need to use this class.

    """
    def __init__(self, usb_device):
        self._pad = None
        self._stick = None
        self._index = self._init_virtual()
        self._info = _get_joystick_info(self._index)

        self._usb_dev = usb_device
        self.usb_pad = None

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

    def close(self):
        self.usb_pad.disconnect()
        GameController.close(self)

    def update(self):
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
