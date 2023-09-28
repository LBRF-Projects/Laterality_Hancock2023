# Functions that should be added to PySDL eventually
from ctypes import c_int, byref
import sdl2


def get_key_state(key):
    """Checks the current state (pressed or released) of a given keyboard key.

    This function checks whether a given key on the keyboard is currently
    pressed or released. Although keypress handling in SDL is usually done by
    checking for keydown and keyup events in the event queue, there are cases
    where it's imporant to check what the state of a key is *right now* instead
    of waiting for an event. 

    Args:
        key (int or str): The name (or SDL scancode) of the key to check.

    Returns:
        int: 1 if the key is currently pressed, otherwise 0.

    """
    # If key given as string, get the corresponding scancode
    if isinstance(key, str):
        scancode = sdl2.SDL_GetScancodeFromName(key.encode("utf-8"))
        if scancode == sdl2.SDL_SCANCODE_UNKNOWN:
            e = "'{0}' is not a valid name for an SDL scancode."
            raise ValueError(e.format(key))
    else:
        scancode = key
    # Check for and return the current key state
    sdl2.SDL_PumpEvents()
    numkeys = c_int(0)
    keys = sdl2.SDL_GetKeyboardState(byref(numkeys))
    if scancode <= numkeys.value:
        return keys[scancode]
    return 0
