import re
from ctypes import create_string_buffer
import sdl2
from sdl2 import joystick as jy # as jy? jk?
from sdl2 import gamecontroller as gc
from sdl2 import error
from sdl2 import (
    SDL_InitSubSystem, SDL_WasInit, SDL_QuitSubSystem, 
    SDL_INIT_JOYSTICK, SDL_INIT_GAMECONTROLLER, SDL_FALSE, SDL_TRUE,
    SDL_JOYBUTTONDOWN, SDL_JOYBUTTONUP,
    SDL_CONTROLLERBUTTONDOWN, SDL_CONTROLLERBUTTONUP,
)
from sdl2.ext.common import raise_sdl_err
from sdl2.ext.compat import utf8, stringify, byteify, _is_text


# Define name maps for joystick types and states

POWER_MAP = {
    jy.SDL_JOYSTICK_POWER_UNKNOWN: "Unknown",
    jy.SDL_JOYSTICK_POWER_EMPTY: "Empty",   # pwr <= 5%
    jy.SDL_JOYSTICK_POWER_LOW: "Low",       # 5% < pwr <= 20%
    jy.SDL_JOYSTICK_POWER_MEDIUM: "Medium", # 20% < pwr <= 70%
    jy.SDL_JOYSTICK_POWER_FULL: "Full",     # 70% < pwr <= 100%
    jy.SDL_JOYSTICK_POWER_WIRED: "Wired",
}

STICK_TYPE_MAP = {
    jy.SDL_JOYSTICK_TYPE_UNKNOWN: "Unknown",
    jy.SDL_JOYSTICK_TYPE_GAMECONTROLLER: "Game Controller",
    jy.SDL_JOYSTICK_TYPE_WHEEL: "Wheel",
    jy.SDL_JOYSTICK_TYPE_ARCADE_STICK: "Arcade Stick",
    jy.SDL_JOYSTICK_TYPE_FLIGHT_STICK: "Flight Stick",
    jy.SDL_JOYSTICK_TYPE_DANCE_PAD: "Dance Pad",
    jy.SDL_JOYSTICK_TYPE_GUITAR: "Guitar",
    jy.SDL_JOYSTICK_TYPE_DRUM_KIT: "Drum Kit",
    jy.SDL_JOYSTICK_TYPE_ARCADE_PAD: "Arcade Pad",
    jy.SDL_JOYSTICK_TYPE_THROTTLE: "Throttle",
}



def _joystick_init():
    error.SDL_ClearError()
    if SDL_WasInit(SDL_INIT_JOYSTICK) == 0:
        if SDL_InitSubSystem(SDL_INIT_JOYSTICK) != 0:
            raise_sdl_err("initializing the joystick subsystem")

def gamepad_init():
    error.SDL_ClearError()
    if SDL_WasInit(SDL_INIT_GAMECONTROLLER) == 0:
        if SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) != 0:
            raise_sdl_err("initializing the gamepad subsystem")


def _validate_index(index):
    num_sticks = jy.SDL_NumJoysticks()
    if num_sticks == 0:
        e = "There are no recognized joystick devices connected to the system."
        raise RuntimeError(e)
    if not (0 <= index < num_sticks):
        valid = str(list(range(num_sticks)))
        e = "No joystick found at index '{0}'. Valid device indices are: {1}."
        raise ValueError(e.format(index, valid))

def _get_joystick_info(index):
    info = {}
    info_functions = {
        'name': jy.SDL_JoystickNameForIndex,
        'type': jy.SDL_JoystickGetDeviceType,
        'guid': jy.SDL_JoystickGetDeviceGUID,
        'vendor_id': jy.SDL_JoystickGetDeviceVendor,
        'product_id': jy.SDL_JoystickGetDeviceProduct,
        'product_version': jy.SDL_JoystickGetDeviceProductVersion,
    }
    for k, f in info_functions.items():
        error.SDL_ClearError()
        info[k] = f(index)
        if error.SDL_GetError() != b"":
            raise_sdl_err("fetching {0} info for joystick {1}".format(k, index))

    # Sanitize collected info
    buf = create_string_buffer(40)
    sdl2.SDL_JoystickGetGUIDString(info['guid'], buf, 40)
    info['guid'] = buf.value
    info['name'] = info['name'].decode('utf-8')
    return info

def _get_gamecontroller_info():
    pass

def get_joysticks():
    devices = []
    count = jy.SDL_NumJoysticks()
    for i in range(count):
        stick = Joystick(i)
        devices.append(stick)
    return devices

def get_controllers():
    devices = []
    count = jy.SDL_NumJoysticks()
    for i in range(count):
        if gc.SDL_IsGameController(i) == SDL_TRUE:
            pad = GameController(i)
            devices.append(pad)
    return devices

def _sanitize_mapping_name(name):
    sdlname = re.sub(r"[\w_-]", "", name).lower()
    b = gc.SDL_GameControllerGetButtonFromString(sdlname.encode('utf-8'))
    if b != gc.SDL_CONTROLLER_BUTTON_INVALID:
        return sdlname
    axis = gc.SDL_GameControllerGetAxisFromString(sdlname.encode('utf-8'))
    if axis != gc.SDL_CONTROLLER_AXIS_INVALID:
        return sdlname
    return None

def _axis_from_name(name):
    sdlname = re.sub(r"[\w_-]", "", name).lower()
    axis = gc.SDL_GameControllerGetAxisFromString(sdlname.encode('utf-8'))
    if axis == gc.SDL_CONTROLLER_AXIS_INVALID:
        raise ValueError("Invalid axis name '{0}'.".format(name))
    return axis

def _button_from_name(name):
    sdlname = re.sub(r"[\w_-]", "", name).lower()
    b = gc.SDL_GameControllerGetButtonFromString(sdlname.encode('utf-8'))
    if b == gc.SDL_CONTROLLER_BUTTON_INVALID:
        raise ValueError("Invalid button name '{0}'.".format(name))
    return b

def _create_controller_mapping(guid, name, buttonmap):
    # External-facing version should accept joystick as input, do validation
    mappings = []
    for control, value in buttonmap.items():
        sdlcontrol = _sanitize_mapping_name(control)
        if not sdlcontrol:
            e = "'{0}' is not a valid SDL2 game controller binding name."
            raise ValueError(e.format(control))
        mapstr.append("{0}:{1}".format(sdlcontrol, value))
    return "{0},{1},{2}".format(guid, name, ",".join(mappings))


class Joystick(object):

    def __init__(self, index, initialize=False):
        _validate_index(index)
        self._index = index
        self._stick = None
        self._instance_id = jy.SDL_JoystickGetDeviceInstanceID(index)

        self._info = {
            'name': None,
            'type': None,
            'guid': None,
            'vendor_id': None,
            'product_id': None,
            'product_version': None,
            'nbuttons': 0,
            'naxes': 0,
            'nhats': 0,
        }
        if initialize:
            self.initialize()

    def _get_info(self):
        info = {}
        info_functions = {
            'name': jy.SDL_JoystickNameForIndex,
            'type': jy.SDL_JoystickGetDeviceType,
            'guid': jy.SDL_JoystickGetDeviceGUID,
            'vendor_id': jy.SDL_JoystickGetDeviceVendor,
            'product_id': jy.SDL_JoystickGetDeviceProduct,
            'product_version': jy.SDL_JoystickGetDeviceProductVersion,
        }
        for k, f in info_functions.items():
            error.SDL_ClearError()
            info[k] = f(self._index)
            if error.SDL_GetError != b"":
                raise_sdl_err("fetching joystick info")

        # Sanitize collected info
        buf = create_string_buffer(40)
        sdl2.SDL_JoystickGetGUIDString(info['guid'], buf, 40)
        info['guid'] = buf.value
        info['name'] = info['name'].decode('utf-8')

        self._info.update(info)

    def initialize(self):
        # First, make sure stick isn't already open
        if self._stick:
            return None

        # Try opening the joystick
        error.SDL_ClearError()
        self._stick = jy.SDL_JoystickOpen(self._index)
        if error.SDL_GetError != b"":
            e = "opening joystick {0} ({1})".format(self._index, self._info['name'])
            raise_sdl_err(e)

        # Get additional info
        naxes = jy.SDL_JoystickNumAxes(self._stick)
        nbuttons = jy.SDL_JoystickNumButtons(self._stick)
        nhats = jy.SDL_JoystickNumHats(self._stick)
        nballs = jy.SDL_JoystickNumBalls(self._stick)
    
    def close(self):
        if self._stick:
            jy.SDL_JoystickClose(self._stick)
            self._stick = None

    @property
    def attached(self):
        if not self._stick:
            return False
        return jy.SDL_JoystickGetAttached(self._stick) == SDL_TRUE

    @property
    def power_level(self):
        pwr = jy.SDL_JOYSTICK_POWER_UNKNOWN
        if self._stick:
            pwr = jy.SDL_JoystickCurrentPowerLevel(self._stick)
        return POWER_MAP[pwr]



class GameController(object):

    def __init__(self, index, mapping=None):
        # NOTE: Should allow passing Joystick class as index?
        _validate_index(index)
        if not gc.SDL_IsGameController(index):
            if mapping == None:
                e = "Joystick at index '{0}' does not have a controller mapping, "
                e += "and no mapping was manually provided."
                raise RuntimeError(e.format(index))
        self._index = index
        self._info = _get_joystick_info(index)
        self._pad = None
        self._stick = None

    def initialize(self):
        # First, make sure pad isn't already open
        if self._pad:
            return None

        # Try opening the gamepad
        error.SDL_ClearError()
        self._pad = gc.SDL_GameControllerOpen(self._index)
        if not self._pad:
            e = "opening controller {0} ({1})".format(self._index, self._info['name'])
            raise_sdl_err(e)

        # Get additional info
        self._stick = gc.SDL_GameControllerGetJoystick(self._pad)
        naxes = jy.SDL_JoystickNumAxes(self._stick)
        nbuttons = jy.SDL_JoystickNumButtons(self._stick)
        nhats = jy.SDL_JoystickNumHats(self._stick)
        nballs = jy.SDL_JoystickNumBalls(self._stick)
    
    def close(self):
        if self._pad:
            gc.SDL_GameControllerClose(self._pad)
            self._pad = None
            self._stick = None

    def update(self):
        pass

    def _get_stick(self, xaxis, yaxis):
        error.SDL_ClearError()
        x = gc.SDL_GameControllerGetAxis(self._pad, xaxis)
        y = gc.SDL_GameControllerGetAxis(self._pad, yaxis)
        if error.SDL_GetError() != b"":
            e = "retrieving axis data from controller {0}".format(self._index)
            raise_sdl_err(e)
        return (x, y)

    def _get_trigger(self, loc):
        error.SDL_ClearError()
        val = gc.SDL_GameControllerGetAxis(self._pad, loc)
        if error.SDL_GetError() != b"":
            e = "retrieving trigger data from controller {0}".format(self._index)
            raise_sdl_err(e)
        return val

    def left_stick(self):
        return self._get_stick(
            gc.SDL_CONTROLLER_AXIS_LEFTX, gc.SDL_CONTROLLER_AXIS_LEFTY
        )

    def right_stick(self):
        return self._get_stick(
            gc.SDL_CONTROLLER_AXIS_RIGHTX, gc.SDL_CONTROLLER_AXIS_RIGHTY
        )

    def left_trigger(self):
        return self._get_trigger(gc.SDL_CONTROLLER_AXIS_TRIGGERLEFT)

    def right_trigger(self):
        return self._get_trigger(gc.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)

    def dpad(self):
        x, y = (0.0, 0.0)
        dpad = {
            'up': gc.SDL_CONTROLLER_BUTTON_DPAD_UP,
            'down': gc.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
            'left': gc.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
            'right': gc.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
        }
        if gc.SDL_GameControllerGetButton(self._pad, dpad['up']):
            y = -1.0
        elif gc.SDL_GameControllerGetButton(self._pad, dpad['down']):
            y = 1.0
        if gc.SDL_GameControllerGetButton(self._pad, dpad['left']):
            x = -1.0
        elif gc.SDL_GameControllerGetButton(self._pad, dpad['right']):
            x = 1.0
        return (x, y)

    def button_state(self, button):
        # NOTE: Can only tell you current state of button, not whether
        # any button presses have happened since you last checked the event
        # queue
        pass

    @property
    def name(self):
        return self._info["name"]



def button_pressed(events, button=None, device=None, on_release=False):
    button_events = [SDL_JOYBUTTONDOWN, SDL_CONTROLLERBUTTONDOWN]
    if on_release:
        button_events = [SDL_JOYBUTTONUP, SDL_CONTROLLERBUTTONUP]
    if button:
        if _is_text(button):
            # TODO: Validation of button strings?
            button_bytes = utf8(button).encode('utf-8')
            button = gc.SDL_GameControllerGetButtonFromString(button_bytes)
        button = int(button)
        # NOTE: Extra buttons added in SDL 2.0.14, should err if requesting newer button
        # with older lib
        if button >= gc.SDL_CONTROLLER_BUTTON_MAX:
            pass
    # TODO: If Joystick/GameController provided, ensure button is valid for device

    pressed = False
    for e in events:
        if e.type not in button_events:
            continue
        if device != None and e.which != device.instance_id:
            continue
        if button == None or e.button == button:
            pressed = True
            break
    
    return pressed

