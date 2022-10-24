import struct
from collections import namedtuple

from .constants import *


# Structure for representing parsed input packets from the controller
InputPacket = namedtuple(
    'InputPacket',
    ['buttons', 'lt', 'rt', 'lx', 'ly', 'rx', 'ry']
)

ButtonEvent = namedtuple('Button', ['name', 'state'])
AxisEvent = namedtuple('Axis', ['name', 'value'])


# Parses an input packet from the controller into useful values
def parse_data_packet(raw):
    parsed = struct.unpack(PACKET_STRUCT, raw[2:14])
    return InputPacket(*parsed)


def parse_buttons(buttonmask):
    pressed = []
    for b in ALL_BUTTONS:
        bit = 0x1 << b
        if buttonmask & bit:
            pressed.append(b)
    return pressed


def get_events(old, new):
    events = []

    #for axis in ALL_AXES:
    #    i = axis + 1
    #    if old[i] != new[i]:
    #        events.append(AxisEvent(axis, new[i]))

    if old.buttons != new.buttons:
        for b in ALL_BUTTONS:
            bit = 0x1 << b
            previous_state = old.buttons & bit
            current_state = new.buttons & bit
            if previous_state != current_state:
                pressed = int(current_state > 0)
                events.append(ButtonEvent(b, pressed))

    return events
