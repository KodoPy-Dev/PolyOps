########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from enum import Enum
from mathutils import Vector
from .screen import screen_factor

########################•########################
"""                 CONTROLS                  """
########################•########################

CONFIRM_EVENTS   = {'SPACE', 'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'}
CANCEL_EVENTS    = {'ESC', 'RIGHTMOUSE'}
MOUSE_EVENTS     = {'MOUSEMOVE', 'TRACKPADPAN'}
INCREMENT_EVENTS = {'WHEELUPMOUSE', 'NUMPAD_PLUS', 'EQUAL', 'UP_ARROW'}
DECREMENT_EVENTS = {'WHEELDOWNMOUSE', 'NUMPAD_MINUS', 'MINUS', 'DOWN_ARROW'}
NUMPAD_EVENTS    = {'NUMPAD_PERIOD', 'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9'}
MOUSE_BTN_EVENTS = {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MIDDLEMOUSE'}
MOD_KEYS         = {'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT'}


def LMB_press(event):
    return event.type == 'LEFTMOUSE' and event.value == 'PRESS'


def LMB_release(event):
    return event.type == 'LEFTMOUSE' and event.value == 'RELEASE'


def RMB_press(event):
    return event.type == 'RIGHTMOUSE' and event.value == 'PRESS'


def RMB_release(event):
    return event.type == 'RIGHTMOUSE' and event.value == 'RELEASE'


def mouse_offset(event):
    factor = screen_factor()
    delta_x = 0
    delta_y = 0
    if event.type in MOUSE_EVENTS:
        delta_x = (event.mouse_x - event.mouse_prev_x) * factor
        delta_y = (event.mouse_y - event.mouse_prev_y) * factor
        if event.shift:
            delta_x *= .25
            delta_y *= .25
    return Vector((delta_x, delta_y)).length


def mouse_scroll_direction(event):
    if event.value != 'PRESS':
        return 0
    if event.type == 'WHEELUPMOUSE':
        return 1
    if event.type == 'WHEELDOWNMOUSE':
        return -1
    return 0


def confirmed(event):
    return event.type in CONFIRM_EVENTS and event.value == 'PRESS'


def cancelled(event, value='RELEASE'):
    return event.type in CANCEL_EVENTS and event.value == value


def pass_through(event, with_scoll=False, with_numpad=False, with_shading=False):

    if event.value != 'PRESS':
        return False

    if event.type in {'MIDDLEMOUSE'}:
        return True

    if with_scoll and event.type in MOUSE_BTN_EVENTS:
        return True

    if with_numpad and event.type in NUMPAD_EVENTS:
        return True
    
    if with_shading:
        if event.shift and event.type == 'Z':
            return True

    return False


def increment_value(event):
    if event.type in INCREMENT_EVENTS and event.value == 'PRESS':
        return 1
    if event.type in DECREMENT_EVENTS and event.value == 'PRESS':
        return -1
    return 0


FACTOR = screen_factor()
THRESHOLD = round(4 * FACTOR)
DRAG_START_POS = None
DRAGGING = False

def is_mouse_dragging(event):
    global FACTOR, THRESHOLD, DRAG_START_POS, DRAGGING
    # Start
    if event.type in {'RIGHTMOUSE', 'LEFTMOUSE'} and event.value == 'PRESS':
        DRAG_START_POS = Vector((event.mouse_x, event.mouse_y))
        DRAGGING = False
        return False
    # End
    if event.type not in MOD_KEYS and event.value == 'RELEASE':
        DRAG_START_POS = None
        DRAGGING = False
        return False
    # Calc
    if DRAG_START_POS != None:
        if DRAGGING:
            return True
        current_loc = Vector((event.mouse_x, event.mouse_y))
        if round((current_loc - DRAG_START_POS).length * FACTOR) >= THRESHOLD:
            DRAGGING = True
            return True
    # Nothing
    DRAGGING = False
    return False


def reset_mouse_drag():
    global FACTOR, THRESHOLD, DRAG_START_POS, DRAGGING
    FACTOR = screen_factor()
    THRESHOLD = round(4 * FACTOR)
    DRAG_START_POS = None
    DRAGGING = False


