########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
import time
from gpu import state
from math import cos, sin, pi, ceil, degrees, radians
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from mathutils.geometry import intersect_point_quad_2d
from bl_math import clamp, lerp
from .addon import user_prefs
from .event import pass_through, LMB_release, LMB_press, cancelled, is_mouse_dragging, mouse_scroll_direction, reset_mouse_drag, increment_value
from .graphics import text_dims, max_text_height, text_descender_height, draw_text, fitted_text_to_width, draw_label, label_dims, draw_line, draw_line_smooth_colors, TextMap, Rect2D, enable_scissor, disable_scissor, Label2D, copied_color
from .math3 import remap_value, rectangle_from_bounds_2d
from .modal_status import UX_STATUS
from .notifications import init as notify
from .screen import screen_factor

########################•########################
"""                 SHADERS                   """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')
POLYLINE_UNIFORM_COLOR = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')

########################•########################
"""               LIST-PICK-MENU              """
########################•########################

class ListPickButton:
    def __init__(self, label="", tip_label="", tip_msg=""):
        self.label = label
        self.tip_label = tip_label
        self.tip_msg = tip_msg
        # --- Build Driven --- #
        self.prefs = user_prefs().drawing
        self.label_pos = Vector((0,0))
        self.tip_pos = Vector((0,0))
        self.bl = Vector((0,0))
        self.br = Vector((0,0))
        self.tl = Vector((0,0))
        self.tr = Vector((0,0))
        self.poly_batch = None
        self.line_batch = None
        # --- Event Driven --- #
        self.non_selectable = False
        self.background_color = (0,0,0,1)
        self.font_color = (0,0,0,1)
        self.mouse_within_bounds = False
        self.mouse = Vector((0,0))


    def update(self, context, event):
        if self.non_selectable:
            self.mouse_within_bounds = False
            return
        self.mouse.x = event.mouse_region_x
        self.mouse.y = event.mouse_region_y
        self.mouse_within_bounds = intersect_point_quad_2d(self.mouse, self.bl, self.br, self.tr, self.tl)
        if self.mouse_within_bounds:
            self.background_color = self.prefs.background_highlight_color
            self.font_color = self.prefs.font_secondary_color
        else:
            self.font_color = self.prefs.font_primary_color
            self.background_color = self.prefs.background_color


    def draw(self):
        if not self.poly_batch or not self.line_batch or not self.label:
            return
        if self.poly_batch:
            state.blend_set('ALPHA')
            UNIFORM_COLOR.uniform_float("color", self.background_color)
            self.poly_batch.draw(UNIFORM_COLOR)
        if self.line_batch:
            state.blend_set('ALPHA')
            state.line_width_set(1)
            UNIFORM_COLOR.uniform_float("color", self.prefs.border_primary_color)
            self.line_batch.draw(UNIFORM_COLOR)
        if self.label:
            draw_text(self.label, x=self.label_pos.x, y=self.label_pos.y, size=self.prefs.font_size, color=self.font_color)
        if self.mouse_within_bounds:
            if self.tip_label or self.tip_msg:
                draw_label(messages=[(self.tip_label, self.tip_msg)], left_x=self.tip_pos.x, top_y=self.tip_pos.y)
        state.line_width_set(1)
        state.blend_set('NONE')


class ListPickMenu:
    def __init__(self, labels=[], call_back=None, action_key='TAB'):
        # Data
        self.status = UX_STATUS.INACTIVE
        self.buttons = []
        for label in labels:
            if isinstance(label, tuple) or isinstance(label, list):
                if len(label) == 3:
                    self.buttons.append(ListPickButton(label=label[0], tip_label=label[1], tip_msg=label[2]))
                if len(label) == 2:
                    self.buttons.append(ListPickButton(label=label[0], tip_label="Tip", tip_msg=label[1]))
            elif isinstance(label, str):
                self.buttons.append(ListPickButton(label=label))
        self.call_back = call_back
        self.action_key = action_key
        self.prefs = user_prefs().drawing
        factor = screen_factor()
        self.pad = self.prefs.padding * factor
        # Background
        self.poly_batch = None
        self.gradient_batch = None
        self.bl = Vector((0,0))
        self.br = Vector((0,0))
        self.tl = Vector((0,0))
        self.tr = Vector((0,0))
    

    def update(self, context, event, blocked_indexes=[]):

        # No buttons
        if not self.buttons:
            self.status = UX_STATUS.INACTIVE
            return

        # Open / Close
        if event.type == self.action_key and event.value == 'RELEASE':
            if self.status == UX_STATUS.ACTIVE:
                self.status = UX_STATUS.INACTIVE
                self.call_back(context, event, label="")
            else:
                self.__build_menu(context, event, blocked_indexes)
                self.status = UX_STATUS.ACTIVE
            return

        # Hold modal for the cancel event
        if cancelled(event):
            self.status = UX_STATUS.INACTIVE
            return

        # If closed exit
        if self.status == UX_STATUS.INACTIVE:
            return

        # Event Detection
        lmb_released = LMB_release(event)
        for button in self.buttons:
            button.update(context, event)
            if lmb_released and button.mouse_within_bounds:
                self.status = UX_STATUS.INACTIVE
                self.call_back(context, event, label=button.label)
                return


    def update_for_internal_menu(self, context, event, blocked_indexes=[], build=False):
        # Build
        if build:
            self.status = UX_STATUS.ACTIVE
            self.__build_menu(context, event, blocked_indexes)
        # Event Detection
        lmb_release = LMB_release(event)
        for button in self.buttons:
            button.update(context, event)
            if lmb_release and button.mouse_within_bounds:
                self.status = UX_STATUS.INACTIVE
                self.call_back(context, event, label=button.label)
                return
        # Didn't click button
        if lmb_release:
            self.status = UX_STATUS.INACTIVE
            self.call_back(context, event, label=None)


    def __build_menu(self, context, event, blocked_indexes=[]):
        # --- Totals --- #
        menu_h = 0
        menu_w = 0
        btn_h = 0
        max_text_h = max_text_height(self.prefs.font_size)
        for i, button in enumerate(self.buttons):
            button.non_selectable = False
            button.background_color = self.prefs.background_color
            button.font_color = self.prefs.font_primary_color
            button.border_color = self.prefs.border_primary_color

            if i in blocked_indexes:
                button.non_selectable = True
                button.font_color = self.prefs.font_tertiary_color

            text_w, text_h = text_dims(button.label, self.prefs.font_size)
            if text_w > menu_w:
                menu_w = text_w
            if text_h > btn_h:
                btn_h = text_h
                max_text_h = text_h
        menu_w += 4 * self.pad
        btn_h += 2 * self.pad
        count = len(self.buttons)
        menu_h = btn_h * count + (self.pad * (count + 1))
        # --- Screen --- #
        area_w = context.area.width
        area_h = context.area.height
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y
        # --- Top Left Corner --- #
        max_x = area_w - menu_w
        top_x = clamp(mouse_x, 0, max_x)
        top_y = clamp(mouse_y, menu_h + self.pad, area_h)
        # --- Tip Position --- #
        tip_x = top_x + menu_w / 2
        tip_y = (top_y - menu_h - self.pad) if (top_y - menu_h - btn_h - self.pad) > 0 else (top_y + btn_h + self.pad)
        # --- Assign button data --- #
        delta_y = top_y - self.pad
        text_x = top_x + 2 * self.pad
        btn_left_x = top_x + self.pad
        btn_right_x = top_x + menu_w - self.pad
        for button in self.buttons:
            button.label_pos = Vector((text_x, delta_y - max_text_h - self.pad))
            tip_string = f"{button.tip_label} {button.tip_msg}"
            tip_x_offset = text_dims(tip_string, self.prefs.font_size)[0]
            button.tip_pos = Vector((tip_x - tip_x_offset / 2, tip_y))
            button.bl = Vector((btn_left_x , delta_y - btn_h))
            button.br = Vector((btn_right_x, delta_y - btn_h))
            button.tl = Vector((btn_left_x , delta_y))
            button.tr = Vector((btn_right_x, delta_y))
            button.line_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": (button.bl, button.br, button.tr, button.tl, button.bl)})
            button.poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": (button.tl, button.bl, button.tr, button.br)}, indices=[(0, 1, 2), (1, 2, 3)])
            delta_y -= (btn_h + self.pad)
        # --- Background --- #
        self.bl = Vector((top_x, delta_y))
        self.br = Vector((top_x + menu_w, delta_y))
        self.tl = Vector((top_x, top_y))
        self.tr = Vector((top_x + menu_w, top_y))
        self.poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": (self.tl, self.bl, self.tr, self.br)}, indices=[(0, 1, 2), (1, 2, 3)])
        top = self.prefs.slider_positive_color
        bot = self.prefs.slider_negative_color
        self.gradient_batch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {"pos": (self.tl, self.bl, self.tr, self.br), "color": (top, bot, top, bot)}, indices=((0, 1, 2), (1, 2, 3)))


    def draw(self):
        # Dead
        if self.status == UX_STATUS.INACTIVE:
            return
        # Background
        if self.poly_batch:
            state.blend_set('ALPHA')
            self.gradient_batch.draw(SMOOTH_COLOR)
            UNIFORM_COLOR.uniform_float("color", self.prefs.background_color)
            self.poly_batch.draw(UNIFORM_COLOR)
            state.blend_set('NONE')
        draw_line_smooth_colors(p1=self.tl, p2=self.bl, width=2, color_1=self.prefs.border_primary_color, color_2=self.prefs.border_secondary_color)
        draw_line_smooth_colors(p1=self.tr, p2=self.br, width=2, color_1=self.prefs.border_primary_color, color_2=self.prefs.border_secondary_color)
        draw_line(p1=self.tl, p2=self.tr, width=2, color=self.prefs.border_primary_color)
        draw_line(p1=self.bl, p2=self.br, width=2, color=self.prefs.border_secondary_color)
        # Buttons
        for button in self.buttons:
            button.draw()

########################•########################
"""                INPUT TIMER                """
########################•########################

AREA = None
INTERVAL = 0.01
OSCILLATION = 0

def input_tag_for_redraw():
    global OSCILLATION
    OSCILLATION = (cos(time.time() * 5) + 1) / 2
    if AREA != None and hasattr(AREA, "tag_redraw"):
        AREA.tag_redraw()
        return INTERVAL
    return None


def set_manual_input_timer(context, register=True):
    global AREA
    AREA = None
    if bpy.app.timers.is_registered(input_tag_for_redraw):
        bpy.app.timers.unregister(input_tag_for_redraw)
    if register:
        AREA = context.area
        bpy.app.timers.register(input_tag_for_redraw, first_interval=INTERVAL)

########################•########################
"""                    MENU                   """
########################•########################

class MenuData:
    def __init__(self, context, event):
        self.prefs = user_prefs().drawing
        # Build
        self.factor = screen_factor()
        self.spad = round(self.prefs.screen_padding * self.factor)
        self.pad = round(self.prefs.padding * self.factor)
        self.font_s = self.prefs.font_size
        self.char_w = round(text_dims("W", self.font_s)[0])
        self.text_h = round(max_text_height(self.font_s))
        self.text_d = round(text_descender_height(self.font_s))
        self.vec_chars = ['X', 'Y', 'Z', 'W']
        self.box_h = round(self.text_h + self.pad * 2)
        self.scroll_bar_width = round(10 * self.factor)
        self.window_lx = 0
        self.window_rx = 0
        self.window_ty = 0
        self.window_by = 0
        self.window_h  = 0
        self.window_w  = 0
        # Event
        self.context = context
        self.event = event
        self.locked_item = None
        self.entry_mode_exit_item = None
        self.mouse = Vector((0,0))
        self.LMB_pressed = False
        self.LMB_released = False
        self.mouse_dragging = False
        self.visible_region_ty = 0
        self.visible_region_by = 0
        # Drawing
        self.scissor_on = False
        self.scissor_x = 0
        self.scissor_y = 0
        self.scissor_w = 0
        self.scissor_h = 0


    def update(self, context, event):
        self.context = context
        self.event = event
        self.mouse.x = event.mouse_region_x
        self.mouse.y = event.mouse_region_y
        self.LMB_pressed = LMB_press(event)
        self.LMB_released = LMB_release(event)
        self.mouse_dragging = is_mouse_dragging(event)


    def set_scissor_params(self, x=0, y=0, w=0, h=0):
        self.scissor_x = int(x)
        self.scissor_y = int(y)
        self.scissor_w = int(w)
        self.scissor_h = int(h)


    def turn_scissor_on(self):
        self.scissor_on = True
        enable_scissor(self.scissor_x, self.scissor_y, self.scissor_w, self.scissor_h)
    

    def turn_scissor_off(self):
        self.scissor_on = False
        disable_scissor()


class PropBox:
    def __init__(self, prop_map=None, attr_index=0):
        self.prop_map = prop_map
        self.attr_index = attr_index
        self.attr_map = TextMap()
        self.sub_map = TextMap()
        self.bounds = Rect2D()
        self.tip_loc = Vector((0,0))
        self.inner_width = 0
        self.pad = 0
        # Ref
        self.float_numeric = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '.'}
        self.int_numeric = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-'}
        self.prefs = user_prefs().drawing
        self.color_a = copied_color(self.prefs.border_primary_color)
        self.color_b = copied_color(self.prefs.border_secondary_color)
        # Pick Box
        self.list_pick_menu = None
        self.show_list_pick_menu = False
        if self.prop_map.list_items:
            self.list_pick_menu = ListPickMenu(labels=self.prop_map.list_items, call_back=self.__list_pick_callback)
        # Event
        self.show_extra_labels = False
        self.full_attr_text = ""
        self.used_drag = False
        self.max_chars = 25
        self.manual_entry_mode = False
        self.manual_entry_string = ""
        self.starting_text_on_manual_entry = ""
        self.delta_drag = Vector((0,0))


    def width(self, MD:MenuData):
        attr = self.prop_map.get_attribute()
        width = MD.char_w * self.prop_map.box_len
        if type(attr) in {Vector}:
            width += MD.char_w + MD.pad
        return round(width)


    def build(self, MD:MenuData, left_x=0, top_y=0):
        
        height = MD.box_h
        width = self.width(MD)
        bottom_y = top_y - height

        attr = self.prop_map.get_attribute()
        text_maps = []
        if type(attr) in {Vector}:
            self.sub_map.text = MD.vec_chars[self.attr_index]
            self.sub_map.font_size = MD.font_s
            self.sub_map.color = MD.prefs.font_tertiary_color
            y = top_y - MD.pad - MD.text_h + MD.text_d
            self.sub_map.location = Vector((left_x, y))
            text_maps.append(self.sub_map)
            # Move Box
            left_x += MD.char_w + MD.pad
            width -= MD.char_w + MD.pad

        self.attr_map.font_size = MD.font_s
        self.attr_map.color = MD.prefs.font_secondary_color
        self.attr_map.location.x = left_x
        self.attr_map.location.y = bottom_y + MD.pad + MD.text_d
        text_maps.append(self.attr_map)

        self.bounds.build(left_x=left_x, bottom_y=bottom_y, w=width, h=height, text_maps=text_maps)
        self.bounds.poly_color = MD.prefs.background_color
        self.bounds.line_color = MD.prefs.border_primary_color

        self.font_size = MD.font_s
        self.inner_width = width - MD.pad * 2
        self.pad = MD.pad
        self.__set_display_text(MD)

        self.tip_loc.x = MD.window_rx + MD.pad
        self.tip_loc.y = self.bounds.tl.y


    def update(self, MD:MenuData):
        if MD.locked_item == self:
            self.__locked_update(MD)
            return
        if not self.__within_view(MD):
            return
        if self.bounds.point_within_bounds(MD.mouse):
            self.show_extra_labels = True
            attr = self.prop_map.get_attribute()
            if attr is None:
                return
            if type(attr) == bool and attr == True:
                self.bounds.line_color = MD.prefs.border_tertiary_color
            else:
                self.bounds.line_color = MD.prefs.border_secondary_color
                self.bounds.poly_color = MD.prefs.background_highlight_color
            context = MD.context
            event = MD.event
            increment = increment_value(event)
            if MD.LMB_pressed:
                # Button
                if callable(attr):
                    attr(context, event, self.prop_map)
                    return
                # Bool
                if type(attr) == bool:
                    self.prop_map.set_attribute(not attr)
                    self.prop_map.invoke_callback(MD)
                    return
                # Lock State
                if type(attr) in {int, float, str, Vector}:
                    MD.locked_item = self
                    MD.entry_mode_exit_item = None
                    # List Pick Menu
                    if self.list_pick_menu and self.prop_map.list_items:
                        blocked_indexes = [self.prop_map.list_index]
                        self.list_pick_menu.update_for_internal_menu(context, event, blocked_indexes=blocked_indexes, build=True)
                        self.show_list_pick_menu = True
            elif abs(increment) > 0:
                if type(attr) in {int, float, bool, Vector}:
                    self.__auto_update_value(MD, increase=True if increment > 0 else False)
        # Keep list modes up to date with changes from modal
        if not MD.locked_item:
            if self.prop_map.list_items:
                attr = self.prop_map.get_attribute()
                if attr != self.attr_map.text:
                    self.__set_display_text(MD)


    def externally_lock_for_entry(self, MD:MenuData):
        MD.locked_item = self
        self.tip_loc.y = self.bounds.tl.y
        self.show_extra_labels = True
        self.bounds.poly_color = MD.prefs.background_highlight_color
        self.bounds.line_color = MD.prefs.border_secondary_color
        self.manual_entry_mode = True
        self.attr_map.location.x = self.bounds.center.x
        self.attr_map.text = ""
        self.starting_text_on_manual_entry = self.__attr_value_to_text()
        set_manual_input_timer(MD.context, register=True)


    def __locked_update(self, MD:MenuData):
        
        # List Pick Menu
        if self.list_pick_menu and self.prop_map.list_items:
            self.list_pick_menu.update_for_internal_menu(MD.context, MD.event, build=False)
            if not self.show_list_pick_menu:
                MD.locked_item = None
                self.reset(MD)
            return

        # Modal Manual Entry
        if self.manual_entry_mode:
            self.__manual_entry(MD)
            return

        attr = self.prop_map.get_attribute()
        if attr is None:
            MD.locked_item = None
            MD.entry_mode_exit_item = None
            self.reset(MD)
            return

        # Dragging Int / Float
        if type(attr) in {int, float, Vector}:
            # Adjust
            if MD.mouse_dragging:
                event = MD.event
                self.used_drag = True
                if event.ctrl or self.delta_drag.x > MD.mouse.x:
                    self.bounds.line_color = self.prefs.border_tertiary_color
                else:
                    self.bounds.line_color = self.prefs.border_secondary_color
                factor = screen_factor()
                distance = (self.delta_drag - MD.mouse).length * factor
                threshold = 20 * factor if event.shift else 5 * factor
                if distance > threshold:
                    increase = True
                    if event.ctrl or self.delta_drag.x > MD.mouse.x:
                        increase = False
                    self.delta_drag.x = MD.mouse.x
                    self.delta_drag.y = MD.mouse.y
                    self.__auto_update_value(MD, increase=increase)
                    self.__set_display_text(MD)
                    self.prop_map.invoke_callback(MD)
                return
            # Finished
            elif self.used_drag:
                MD.locked_item = None
                self.reset(MD)
                return
        
        # Flip Bool & Done
        elif type(attr) == bool:
            MD.locked_item = None
            self.prop_map.auto_update_value()
            self.__set_display_text(MD)
            self.prop_map.invoke_callback(MD)
            self.reset(MD)
            return

        # Start Manual Entry Mode
        if MD.LMB_released and self.used_drag == False:
            # Start manual entry mode
            if type(attr) in {int, float, str, Vector}:
                self.manual_entry_mode = True
                self.attr_map.location.x = self.bounds.center.x
                self.attr_map.text = ""
                self.starting_text_on_manual_entry = self.__attr_value_to_text()
                set_manual_input_timer(MD.context, register=True)


    def __manual_entry(self, MD:MenuData):

        def clear_state():
            MD.locked_item = None
            MD.entry_mode_exit_item = self
            self.reset(MD)
            self.__set_display_text(MD)
            set_manual_input_timer(MD.context, register=False)

        attr = self.prop_map.get_attribute()

        # Error : Cancel
        if attr is None:
            clear_state()
            return

        context = MD.context
        event = MD.event

        # Entry
        if event.value == 'PRESS':
            # Remove Chars
            if event.type == 'BACK_SPACE':
                if event.ctrl:
                    self.manual_entry_string = ""
                else:
                    self.manual_entry_string = self.manual_entry_string[:len(self.manual_entry_string) - 1]
            # Limit
            if len(self.manual_entry_string) > self.max_chars:
                notify(context, messages=[("$Error", "Limit Reached!"), ("Max", f"{self.max_chars} Chars")])
                self.manual_entry_string = self.manual_entry_string[:self.max_chars]
            # INT
            elif type(attr) == int:
                if event.ascii in self.int_numeric:
                    if event.ascii == "-":
                        if self.manual_entry_string.startswith("-"):
                            self.manual_entry_string = self.manual_entry_string.replace("-", "")
                        else:
                            self.manual_entry_string = "-" + self.manual_entry_string
                    else:
                        self.manual_entry_string += event.ascii
            # FLOAT / VECTOR
            elif type(attr) in {float, Vector}:
                if event.ascii in self.float_numeric:
                    if event.ascii == ".":
                        if self.manual_entry_string.count(".") == 0:
                            self.manual_entry_string += event.ascii
                    elif event.ascii == "-":
                        if self.manual_entry_string.startswith("-"):
                            self.manual_entry_string = self.manual_entry_string.replace("-", "")
                        else:
                            self.manual_entry_string = "-" + self.manual_entry_string
                    else:
                        self.manual_entry_string += event.ascii
            # STRING
            elif type(attr) == str:
                self.manual_entry_string += event.ascii
                if self.manual_entry_string.startswith(" "):
                    self.manual_entry_string = self.manual_entry_string[1:]
            
            # Set Display Text
            self.__set_display_text_for_manual_entry(self.manual_entry_string)
        
        # Confirm
        if event.type in {'RET', 'TAB', 'NUMPAD_ENTER', 'LEFTMOUSE'} and event.value == 'RELEASE':
            # Error : No Value
            if self.manual_entry_string == "":
                clear_state()
                return
            # Error : Chars not in Float Numeric
            if type(attr) in {float, Vector}:
                if not all(bool(char in self.float_numeric) for char in self.manual_entry_string):
                    notify(context, messages=[("$Error", "Not all values are numeric"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
            # Error : To many Dots
            if type(attr) in {float, Vector}:
                if self.manual_entry_string.count('.') > 1:
                    notify(context, messages=[("$Error", "To many decimal points"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
            # Error : To many negative signs
            if type(attr) in {int, float, Vector}:
                if self.manual_entry_string.count('-') > 1:
                    notify(context, messages=[("$Error", "To many negative signs"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
            # Error : Chars not in Int Numeric
            if type(attr) == int:
                if not all(bool(char in self.int_numeric) for char in self.manual_entry_string):
                    notify(context, messages=[("$Error", "Not all values are numeric"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
            
            # INT
            if type(attr) == int:
                value = 0
                try:
                    value = int(self.manual_entry_string)
                except:
                    notify(context, messages=[("$Error", "Could not convert to Integer"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
                self.prop_map.set_attribute(value=value)
            # FLOAT
            elif type(attr) == float:
                value = 0
                try:
                    value = float(self.manual_entry_string)
                except:
                    notify(context, messages=[("$Error", "Could not convert to Float"), ("Value", "Reverted to previous")])
                    clear_state()
                    return
                self.prop_map.set_attribute(value=value)
            # STRING
            elif type(attr) == str:
                self.prop_map.set_attribute(value=self.manual_entry_string.strip())
            # VECTOR
            elif type(attr) == Vector:
                try:
                    value = float(self.manual_entry_string)
                    attr[self.attr_index] = value
                except:
                    notify(context, messages=[("$Error", "Could not convert compoenent to Float"), ("Value", "Reverted to previous")])
                    clear_state()
                    return

            # Notify Owner
            self.prop_map.invoke_callback(MD)

            # Clear
            clear_state()
            return

        # Cancel
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'RELEASE':
            clear_state()
            return


    def __within_view(self, MD:MenuData):
        if MD.visible_region_ty == 0 and MD.visible_region_by == 0:
            return True
        if self.bounds.tl.y - self.pad > MD.visible_region_ty:
            return False
        if self.bounds.bl.y + self.pad < MD.visible_region_by:
            return False
        return True


    def __set_display_text(self, MD:MenuData):
        attr_text = self.__attr_value_to_text()
        text = fitted_text_to_width(text=attr_text, max_w=self.inner_width, left_to_right=True)
        text_w = text_dims(text, MD.font_s)[0]
        difference = abs(self.inner_width - text_w)
        self.attr_map.location.x = self.bounds.bl.x + self.pad + round((difference / 2))
        self.attr_map.text = text


    def __set_display_text_for_manual_entry(self, text=""):
        '''Uses the text passed in to set the inner text'''
        text = fitted_text_to_width(text=text, max_w=self.inner_width, left_to_right=False)
        text_w = text_dims(text, self.prefs.font_size)[0]
        difference = abs(self.inner_width - text_w)
        self.attr_map.location.x = self.bounds.bl.x + self.pad + round((difference / 2))
        self.attr_map.text = text


    def __attr_value_to_text(self):
        attr = self.prop_map.get_attribute()
        if attr is None:
            return ""
        if type(attr) == bool:
            return self.prop_map.label
        if type(attr) == int:
            if self.prop_map.as_degrees:
                return f"{attr}º"
            return str(attr)
        if type(attr) == float:
            attr = round(attr, self.prop_map.precision)
            if self.prop_map.as_degrees:
                return f"{attr}º"
            return str(attr)
        if type(attr) == str:
            return str(attr)
        if type(attr) == Vector:
            attr = round(attr[self.attr_index], self.prop_map.precision)
            if self.prop_map.as_degrees:
                return f"{attr}º"
            return str(attr)
        if callable(attr):
            return self.prop_map.label


    def __auto_update_value(self, MD:MenuData, increase=True, text=""):
        increment_value = self.prop_map.increment_value
        attr = self.prop_map.get_attribute()
        if attr is None:
            return
        # Int
        if type(attr) == int:
            if increase:
                attr += increment_value
            else:
                attr -= increment_value
            attr = round(attr)
            self.prop_map.set_attribute(attr)
        # Float
        elif type(attr) == float:
            if increase:
                attr += increment_value
            else:
                attr -= increment_value
            self.prop_map.set_attribute(attr)
        # Bool
        elif type(attr) == bool:
            attr = not attr
            self.prop_map.set_attribute(attr)
        # String
        elif type(attr) == str:
            attr = text
            self.prop_map.set_attribute(attr)
        # Vector
        elif type(attr) == Vector:
            if increase:
                attr[self.attr_index] += increment_value
            else:
                attr[self.attr_index] -= increment_value
        
        self.prop_map.invoke_callback(MD)


    def __list_pick_callback(self, context, event, label=""):
        if label is None:
            self.show_list_pick_menu = False
            return
        try:
            self.show_list_pick_menu = False
            if label in self.prop_map.list_items:
                self.prop_map.list_index = self.prop_map.list_items.index(label)
                setattr(self.prop_map.instance, self.prop_map.prop_name, label)
                if self.prop_map.call_back != None:
                    if callable(self.prop_map.call_back):
                        self.prop_map.call_back(context, event, self.prop_map)
        except:
            pass


    def vertical_shift(self, y_offset):
        self.bounds.offset(y_offset=y_offset)


    def reset(self, MD:MenuData):
        if MD.locked_item == self:
            return

        self.show_list_pick_menu = False

        attr = self.prop_map.get_attribute()
        prefs = MD.prefs

        # Border Colors : Secondary
        if self.prop_map.highlight_callback is not None and callable(self.prop_map.highlight_callback):
            if self.prop_map.highlight_callback(MD.context, MD.event, self.prop_map):
                self.bounds.line_color = prefs.border_secondary_color
            else:
                self.bounds.line_color = prefs.border_primary_color

        # Border Colors : Secondary
        elif isinstance(attr, bool) and bool(attr):
            self.bounds.line_color = prefs.border_secondary_color

        # Border Colors : Primary
        else:
            self.bounds.line_color = prefs.border_primary_color

        self.tip_loc.y = self.bounds.tl.y
        self.bounds.poly_color = prefs.background_color
        self.show_extra_labels = False
        self.full_attr_text = ""
        self.used_drag = False
        self.manual_entry_mode = False
        self.manual_entry_string = ""
        self.starting_text_on_manual_entry = ""
        self.__set_display_text(MD)


    def draw(self, MD:MenuData):
        # Border
        if self.manual_entry_mode:
            self.bounds.line_color = self.color_a.lerp(self.color_b, OSCILLATION)
        self.bounds.draw()

        # Scissor OFF
        scissor_was_on = MD.scissor_on
        if MD.scissor_on:
            MD.turn_scissor_off()
        # List Pick Menu
        if self.show_list_pick_menu and self.list_pick_menu and self.prop_map.list_items:
            self.list_pick_menu.draw()
        # Entry Mode
        elif self.manual_entry_mode:
            attr = self.prop_map.get_attribute()
            if attr is None:
                return
            type_str = "None"
            if type(attr) in {float, Vector}:
                type_str = "Float"
            elif type(attr) == int:
                type_str = "Integer"
            elif type(attr) == str:
                type_str = "Text"
            msgs = [
                ("Previous", self.starting_text_on_manual_entry),
                ("Type", type_str),
                ("Enter / LMB", "Confirm"),
                ("Escape / RMB", "Cancel"),
                ("Tab", "Next Prop Box"),
                ("Backspace", "Clear last (Ctrl for line)")]
            draw_label(messages=msgs, left_x=self.tip_loc.x, top_y=self.tip_loc.y)

            if self.manual_entry_string == "":
                draw_text(text="?", x=self.attr_map.location.x, y=self.attr_map.location.y, size=self.prefs.font_size, color=self.prefs.font_primary_color)
        # Dragging
        elif self.used_drag:
            msgs = [
                ("Shift", "Slow Increase"),
                ("Ctrl", "Subtractive Increase")]
            draw_label(messages=msgs, left_x=self.tip_loc.x, top_y=self.tip_loc.y)
        # Labels
        elif self.show_extra_labels:
            if self.prop_map.tip or self.full_attr_text:
                msgs = []
                if self.prop_map.tip:
                    msgs.append(("Tip", self.prop_map.tip))
                if self.full_attr_text:
                    msgs.append(("Full", self.full_attr_text))
                draw_label(messages=msgs, left_x=self.tip_loc.x, top_y=self.tip_loc.y)

        # Scissor ON
        if scissor_was_on:
            MD.turn_scissor_on()


class PropMap:
    def __init__(self,
        label="", tip="", show_label=True, label_pos='LEFT',
        instance=None, prop_name='', call_back=None,
        increment_value=1, precision=2, as_degrees=False, min_val=None, max_val=None,
        list_items=[], list_index=0,
        label_len=0, box_len=0,
        align_vec='Vertical',
        user_data={},
        highlight_callback=None):

        self.label = label
        self.tip = tip
        self.show_label = show_label
        self.label_pos = label_pos
        self.instance = instance
        self.prop_name = prop_name
        self.call_back = call_back
        self.increment_value = increment_value
        self.precision = precision
        self.as_degrees = as_degrees
        self.min_val = min_val
        self.max_val = max_val
        self.list_index = list_index
        self.list_items = list_items
        self.label_len = label_len
        self.box_len = box_len
        self.align_vec = align_vec
        self.user_data = user_data
        self.highlight_callback = highlight_callback
        self.label_map = TextMap()
        self.prop_boxes = []
        self.__gen_prop_boxes()


    def __gen_prop_boxes(self):
        attr = self.get_attribute()
        if attr != None:
            if type(attr) in {bool, int, float, str}:
                self.prop_boxes.append(PropBox(prop_map=self))
            elif type(attr) in {Vector}:
                for i in range(len(attr)):
                    self.prop_boxes.append(PropBox(prop_map=self, attr_index=i))
            elif callable(attr):
                self.prop_boxes.append(PropBox(prop_map=self))


    def get_attribute(self):
        attr = None
        if self.instance and self.prop_name:
            if hasattr(self.instance, self.prop_name):
                attr = getattr(self.instance, self.prop_name)

                # List Items
                if self.list_items:
                    if self.list_index >= 0 and self.list_index <= (len(self.list_items) - 1):
                        list_item = str(self.list_items[self.list_index])
                        if list_item != attr and attr in self.list_items:
                            self.list_index = self.list_items.index(attr)
                            attr = str(self.list_items[self.list_index])
        return attr
    

    def set_attribute(self, value=None, attr_index=0):
        attr = self.get_attribute()

        if type(attr) in {Vector, int, float}:
            if type(self.min_val) in {int, float} and value < self.min_val:
                value = self.min_val
            elif type(self.max_val) in {int, float} and value > self.max_val:
                value = self.max_val

        if type(attr) in {Vector}:
            attr[attr_index] = value
        elif type(attr) in {int, float, bool, str}:
            setattr(self.instance, self.prop_name, value)


    def invoke_callback(self, MD:MenuData):
        if self.call_back != None:
            if callable(self.call_back):
                self.call_back(MD.context, MD.event, self)


    def width(self, MD:MenuData):
        width = 0
        attr = self.get_attribute()
        if type(attr) in {Vector}:
            if self.align_vec == 'Vertical':
                label_w = MD.char_w * self.label_len
                box_w = (MD.char_w + MD.pad) + (MD.char_w * self.box_len)
                width = label_w if label_w > box_w else box_w
            else:
                box_w = MD.char_w + MD.pad + (MD.char_w * self.box_len)
                box_w = (box_w + MD.pad) * len(self.prop_boxes)
                label_w = MD.char_w * self.label_len
                width = label_w if label_w > box_w else box_w
        else:
            width = MD.char_w * self.label_len
            width += MD.char_w * self.box_len
        return round(width)


    def height(self, MD:MenuData):
        '''Height of prop boxes : [NO overage padding]'''
        height = 0
        attr = self.get_attribute()
        if type(attr) in {Vector}:
            if self.label:
                height += MD.box_h
            if self.align_vec == 'Vertical':
                height += MD.box_h * len(attr)
                height += MD.pad * (len(attr) - 1)
            else:
                height += MD.box_h
        else:
            height += MD.box_h
            if self.label_pos == 'TOP' and type(attr) in {int, float, str, bool}:
                height += MD.box_h
        return round(height)


    def build(self, MD:MenuData, left_x=0, top_y=0):
        attr = self.get_attribute()

        label_top = True if self.label_pos == 'TOP' and type(attr) in {int, float, str, bool} else False

        if (self.label) and (not callable(attr)) and (type(attr) != bool) and (not self.list_items):
            self.label_map.text = self.label
            self.label_map.font_size = MD.font_s
            self.label_map.color = MD.prefs.font_primary_color
            x = left_x
            if label_top:
                label_w = text_dims(self.label, MD.font_s)[0]
                width = 0
                for prop_box in self.prop_boxes:
                    delta_w = prop_box.width(MD)
                    if delta_w > width:
                        width = delta_w
                x += round(abs((width - label_w)) / 2)
            self.label_map.location.x = x
            self.label_map.location.y = top_y - MD.pad - MD.text_h + MD.text_d

        prop_box_lx = left_x
        prop_box_ty = top_y

        if self.label:
            if type(attr) in {Vector}:
                prop_box_ty -= MD.box_h
            else:
                prop_box_lx += MD.char_w * self.label_len
                if label_top:
                    prop_box_ty -= MD.box_h

        for prop_box in self.prop_boxes:
            prop_box.build(MD, left_x=prop_box_lx, top_y=prop_box_ty)
            if type(attr) in {Vector} and self.align_vec == 'Vertical':
                prop_box_ty -= MD.box_h + MD.pad
            else:
                prop_box_lx += MD.pad + prop_box.width(MD)


    def update(self, MD:MenuData):
        for prop_box in self.prop_boxes:
            prop_box.update(MD)
            if MD.locked_item != None:
                return


    def vertical_shift(self, y_offset):
        self.label_map.location.y += y_offset
        for prop_box in self.prop_boxes:
            prop_box.vertical_shift(y_offset)


    def reset(self, MD:MenuData):
        for prop_box in self.prop_boxes:
            prop_box.reset(MD)


    def draw(self, MD:MenuData):
        if self.show_label:
            self.label_map.draw()
        for prop_box in self.prop_boxes:
            if prop_box == MD.locked_item:
                continue
            prop_box.draw(MD)


class Row:
    def __init__(self, label="", prop_maps=[], align='CENTER', min_label_height=False, min_borders=False, highlight_id=None, highlight_callback=None):
        self.label = label
        self.prop_maps = prop_maps
        self.align = align
        self.min_label_height = min_label_height
        self.min_borders = min_borders
        self.highlight_id = highlight_id
        self.highlight_callback = highlight_callback
        self.label_map = TextMap()
        self.bounds = Rect2D()


    def width(self, MD:MenuData):

        width = MD.pad
        for prop_map in self.prop_maps:
            width += prop_map.width(MD)
            width += MD.pad

        if self.min_borders:
            width -= MD.pad * 2

        if self.label:
            label_w = text_dims(self.label, MD.font_s)[0]
            label_w += MD.pad * 2
            if label_w > width:
                width = label_w

        return round(width)


    def height(self, MD:MenuData):
        '''Returns the tallest prop map plus label if valid : [ADDS overage padding]'''
        height = 0
        # Tallest prop map
        for prop_map in self.prop_maps:
            prop_map_h = prop_map.height(MD)
            if prop_map_h > height:
                height = prop_map_h
        # Top and Bottom padding
        if not self.min_borders:
            height += MD.pad * 2
        # Label spacing
        if self.label:
            height += MD.text_h
            if self.min_label_height == False:
                height += MD.pad * 2
            else:
                height += MD.pad
        return round(height)


    def build(self, MD:MenuData, top_y=0, width=0):

        left_x = MD.window_lx + MD.pad * 2
        height = self.height(MD)
        bottom_y = round(top_y - height)

        if self.min_borders:
            width += MD.pad * 2
            top_y += MD.pad
            left_x -= MD.pad

        text_maps = []
        if self.label:
            self.label_map.text = self.label
            self.label_map.font_size = MD.font_s
            self.label_map.color = MD.prefs.font_primary_color
            x = left_x + MD.pad
            y = top_y - MD.pad - MD.text_h + MD.text_d
            self.label_map.location = Vector((x, y))
            text_maps.append(self.label_map)

        self.bounds.build(left_x=left_x, bottom_y=bottom_y, w=width, h=height, text_maps=text_maps)
        self.bounds.poly_color = MD.prefs.background_color
        self.bounds.line_color = MD.prefs.border_primary_color

        row_w = self.bounds.width
        maps_w = sum([prop_map.width(MD) for prop_map in self.prop_maps])
        difference = row_w - maps_w
        count = len(self.prop_maps) if len(self.prop_maps) > 0 else 1
        x_offset = difference / (count + 1)

        map_lx = 0
        if self.align == 'LEFT':
            map_lx = left_x + MD.pad
        elif self.align == 'CENTER':
            map_lx = left_x + x_offset
        elif self.align == 'RIGHT':
            difference -= MD.pad * count
            map_lx = left_x + difference

        map_ty = top_y - MD.pad
        if self.label:
            if self.min_label_height:
                map_ty -= MD.text_h + MD.pad
            else:
                map_ty -= MD.text_h + MD.pad * 2

        for prop_map in self.prop_maps:
            prop_map.build(MD, left_x=map_lx, top_y=map_ty)
            map_w = prop_map.width(MD)
            if self.align == 'LEFT':
                map_lx += map_w + MD.pad
            elif self.align == 'CENTER':
                map_lx += map_w + x_offset
            elif self.align == 'RIGHT':
                map_lx += map_w + MD.pad


    def update(self, MD:MenuData):

        if callable(self.highlight_callback) and self.highlight_callback(self):
            self.bounds.line_color = MD.prefs.border_tertiary_color
        else:
            self.bounds.line_color = MD.prefs.border_primary_color

        for prop_map in self.prop_maps:
            prop_map.update(MD)
            if MD.locked_item != None:
                return


    def vertical_shift(self, y_offset):
        self.bounds.offset(y_offset=y_offset)
        for prop_map in self.prop_maps:
            prop_map.vertical_shift(y_offset)


    def reset(self, MD:MenuData):
        if callable(self.highlight_callback) and self.highlight_callback(self):
            self.bounds.line_color = MD.prefs.border_tertiary_color
        else:
            self.bounds.line_color = MD.prefs.border_primary_color

        for prop_map in self.prop_maps:
            prop_map.reset(MD)


    def draw(self, MD:MenuData):
        if not self.min_borders:
            self.bounds.draw()

        for prop_map in self.prop_maps:
            prop_map.draw(MD)


class Container:
    def __init__(self, label="", center_label=False, rows=[], force_no_scroll_bar=False, max_rows=5):
        self.label = label
        self.center_label = center_label
        self.rows = rows
        self.force_no_scroll_bar = force_no_scroll_bar
        self.max_rows = max_rows
        self.label_map = TextMap()
        self.bounds = Rect2D()
        self.show_scroll_bar = False
        self.scroll_rail = Rect2D()
        self.scroll_grip = Rect2D()
        self.seperator_line_batch = None
        self.mouse_y = 0
        self.pad = 0
        self.full_h = 0
        self.sci_x = 0
        self.sci_y = 0
        self.sci_w = 0
        self.sci_h = 0


    def width(self, MD:MenuData):
        '''Returns the widest row or the label if wider : [NO overage padding]'''
        width = 0
        for row in self.rows:
            row_w = row.width(MD)
            if row_w > width:
                width = row_w
        width += MD.pad * 2
        if self.label:
            label_w = text_dims(self.label, MD.font_s)[0]
            label_w += MD.pad * 2
            if label_w > width:
                width = label_w
        if self.show_scroll_bar:
            width += MD.scroll_bar_width
        return round(width)


    def height(self, MD:MenuData):
        '''Returns the sum height of all the rows with padding in between them : [ADDS overage padding]'''
        height = MD.pad
        for row in self.rows:
            height += row.height(MD)
            height += MD.pad
        height = round(height)

        self.full_h = height

        if not self.force_no_scroll_bar:
            if height > self.max_rows * (MD.box_h + MD.pad * 2):
                self.show_scroll_bar = True
                height = self.max_rows * (MD.box_h + MD.pad * 2)
        if self.label:
            height += MD.box_h
        return height


    def build(self, MD:MenuData, top_y=0):

        self.pad = MD.pad
        left_x = MD.window_lx + MD.pad
        width = MD.window_w - MD.pad * 2
        height = self.height(MD)
        bottom_y = round(top_y - height)

        self.sci_x = left_x + 1
        self.sci_y = bottom_y + 1
        self.sci_w = (width - MD.scroll_bar_width if self.show_scroll_bar else width) - 2
        self.sci_h = (height - MD.text_h - MD.pad * 2 if self.label else height) -1

        text_maps = []
        if self.label and isinstance(self.label, str):
            self.label_map.text = self.label
            self.label_map.font_size = MD.font_s
            self.label_map.color = MD.prefs.font_primary_color
            y = top_y - MD.pad - MD.text_h + MD.text_d
            x = left_x + MD.pad
            if self.center_label:
                label_width = text_dims(self.label, MD.font_s)[0]
                diff = abs(width - label_width)
                x = round(left_x + (diff / 2))
            self.label_map.location = Vector((x, y))
            text_maps.append(self.label_map)

            # Seperator
            y = top_y - MD.text_h - MD.pad * 2
            p1 = Vector((left_x, y))
            p2 = Vector((left_x + width, y))
            self.seperator_line_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": (p1, p2)})


        self.bounds.build(left_x=left_x, bottom_y=bottom_y, w=width, h=height, text_maps=text_maps)
        self.bounds.line_color = MD.prefs.border_primary_color
        self.bounds.poly_color = MD.prefs.background_submenu_color
        self.bounds.line_width = 2

        if self.show_scroll_bar:
            bar_lx = left_x + width - MD.scroll_bar_width
            bar_w = MD.scroll_bar_width
            bar_h = height
            if self.label:
                bar_h -= MD.text_h + MD.pad * 2
            self.scroll_rail.build(left_x=bar_lx, bottom_y=bottom_y, w=bar_w, h=bar_h)
            self.scroll_rail.poly_color = MD.prefs.background_color
            self.scroll_rail.line_color = MD.prefs.border_primary_color

            handle_h = round(bar_h / 4)
            handle_by = bottom_y + (handle_h * 3)
            self.scroll_grip.build(left_x=bar_lx, bottom_y=handle_by, w=bar_w, h=handle_h)
            self.scroll_grip.poly_color = MD.prefs.background_color
            self.scroll_grip.line_color = MD.prefs.border_secondary_color
        
        row_w = width - MD.pad * 2
        if self.show_scroll_bar:
            row_w -= MD.scroll_bar_width
        row_ty = top_y - MD.pad
        if self.label:
            row_ty -= MD.text_h + MD.pad * 2

        for row in self.rows:
            row.build(MD, top_y=row_ty, width=row_w)
            row_ty -= row.height(MD)
            row_ty -= MD.pad


    def update(self, MD:MenuData):

        if MD.locked_item == self:
            self.__locked_update(MD)
            return
        
        if self.show_scroll_bar:
            if self.scroll_grip.point_within_bounds(MD.mouse):
                self.scroll_grip.poly_color = MD.prefs.background_highlight_color
                self.scroll_grip.line_color = MD.prefs.border_secondary_color
                if MD.mouse_dragging:
                    MD.locked_item = self
                    self.mouse_y = MD.mouse.y
                    return

        if self.show_scroll_bar:
            MD.visible_region_ty = self.scroll_rail.tl.y
            MD.visible_region_by = self.scroll_rail.bl.y
        else:
            MD.visible_region_ty = 0
            MD.visible_region_by = 0

        # Scrolling : Returns if true
        if self.show_scroll_bar and self.bounds.point_within_bounds(MD.mouse):
            scroll_container = True
            scroll = mouse_scroll_direction(MD.event)
            if abs(scroll) > 0:
                for row in self.rows:
                    if self.__row_in_view(row):
                        for prop_map in row.prop_maps:
                            for prop_box in prop_map.prop_boxes:
                                if prop_box.bounds.point_within_bounds(MD.mouse):
                                    scroll_container = False
                if scroll_container:
                    y_offset = scroll * 4
                    self.scroll_grip.offset(y_offset=y_offset, by_limit=self.scroll_rail.bl.y, ty_limit=self.scroll_rail.tl.y)
                    self.__offset_rows_to_grip()
                    return


        for row in self.rows:
            if self.__row_in_view(row):
                row.update(MD)
                if MD.locked_item != None:
                    return


    def __locked_update(self, MD:MenuData):
        if MD.mouse_dragging == False:
            MD.locked_item = None
            self.reset(MD)
            return
        y_offset = MD.mouse.y - self.mouse_y
        self.mouse_y = MD.mouse.y
        self.scroll_grip.offset(y_offset=y_offset, by_limit=self.scroll_rail.bl.y, ty_limit=self.scroll_rail.tl.y)
        self.__offset_rows_to_grip()


    def __row_in_view(self, row):
        if self.show_scroll_bar == False:
            return True
        if row.bounds.tl.y > self.scroll_rail.bl.y:
            if row.bounds.bl.y < self.scroll_rail.tl.y:
                return True
        return False


    def __offset_rows_to_grip(self):
        max_offset = self.full_h - self.scroll_rail.height
        scroll_max = self.scroll_rail.height - self.scroll_grip.height
        grip_offset = self.scroll_rail.tl.y - self.scroll_grip.tl.y
        ratio = max_offset / scroll_max
        row_offset = ratio * grip_offset
        curr_offset = (self.rows[0].bounds.tl.y + self.pad) - self.scroll_rail.tl.y
        offset = row_offset - curr_offset
        for row in self.rows:
            row.vertical_shift(offset)


    def externally_ensure_locked_box_is_visible(self, MD:MenuData):

        if self.show_scroll_bar == False:
            return
        
        if MD.locked_item is None:
            return

        prop_box_bounds = MD.locked_item.bounds

        if self.bounds.other_rect_within_bounds(rect2d=prop_box_bounds):
            return

        offset_y = 0
        if prop_box_bounds.bl.y < self.scroll_rail.bl.y:
            offset_y = self.scroll_rail.bl.y - prop_box_bounds.bl.y
            offset_y += self.pad
        else:
            return
        
        overage = self.full_h - self.scroll_rail.height
        scroll = self.scroll_rail.height - self.scroll_grip.height
        ratio = overage / scroll
        grip_offset = round(offset_y / ratio)
        self.scroll_grip.offset(y_offset=-grip_offset, by_limit=self.scroll_rail.bl.y, ty_limit=self.scroll_rail.tl.y)
        for row in self.rows:
            row.vertical_shift(offset_y)


    def externally_ensure_row_visible(self, row:Row):

        if self.show_scroll_bar == False:
            return
        if type(row) != Row:
            return

        row_bounds = row.bounds

        if self.bounds.other_rect_within_bounds(rect2d=row_bounds):
            return

        offset_y = 0
        # Below Scroll
        if row_bounds.bl.y < self.scroll_rail.bl.y:
            offset_y = self.scroll_rail.bl.y - row_bounds.bl.y
            offset_y += self.pad
        # Above Scroll
        elif row_bounds.tl.y > self.scroll_rail.tl.y:
            offset_y = self.scroll_rail.tl.y - row_bounds.tl.y
            offset_y -= self.pad
        # Within
        else:
            return

        overage = self.full_h - self.scroll_rail.height
        scroll = self.scroll_rail.height - self.scroll_grip.height
        ratio = overage / scroll
        grip_offset = round(offset_y / ratio)
        self.scroll_grip.offset(y_offset=-grip_offset, by_limit=self.scroll_rail.bl.y, ty_limit=self.scroll_rail.tl.y)
        for row in self.rows:
            row.vertical_shift(offset_y)


    def reset(self, MD:MenuData):
        for row in self.rows:
            if self.__row_in_view(row):
                row.reset(MD)
        if MD.locked_item == self:
            return
        self.scroll_grip.poly_color = MD.prefs.background_color
        self.scroll_grip.line_color = MD.prefs.border_secondary_color


    def draw(self, MD:MenuData):
        self.bounds.draw()
        if self.seperator_line_batch:
            state.blend_set('ALPHA')
            state.line_width_set(1)
            UNIFORM_COLOR.uniform_float("color", MD.prefs.border_primary_color)
            self.seperator_line_batch.draw(UNIFORM_COLOR)
            state.line_width_set(1)
            state.blend_set('NONE')
        if self.show_scroll_bar:
            self.scroll_rail.draw()
            self.scroll_grip.draw()
            MD.set_scissor_params(x=self.sci_x, y=self.sci_y, w=self.sci_w, h=self.sci_h)
            MD.turn_scissor_on()
        for row in self.rows:
            row.draw(MD)
        MD.turn_scissor_off()


class Menu:
    def __init__(self, context, event, containers=[]):
        self.prefs = user_prefs().drawing
        self.containers = containers
        self.MD = MenuData(context, event)
        self.hide_menu = False
        self.status = UX_STATUS.ACTIVE
        self.bounds = Rect2D()
        self.tl = Vector((0,0))
        self.bl = Vector((0,0))
        self.tr = Vector((0,0))
        self.br = Vector((0,0))
        self.poly_batch = None
        self.line_batches = []
        self.build(context)
        reset_mouse_drag()

        self.debug = []


    def close(self, context):
        set_manual_input_timer(context, register=False)
        reset_mouse_drag()


    def hide(self):
        self.status = UX_STATUS.INACTIVE
        self.hide_menu = True
    

    def show(self):
        self.status = UX_STATUS.ACTIVE
        self.hide_menu = False if self.containers else True


    def build(self, context):

        MD = self.MD

        # --- WINDOW : MAX Height --- #
        for container in self.containers:
            MD.window_h += container.height(MD)
        MD.window_h += MD.pad * (len(self.containers) + 1)

        # --- WINDOW : MAX Width --- #
        for container in self.containers:
            container_w = container.width(MD)
            if container_w > MD.window_w:
                MD.window_w = container_w
        MD.window_w += MD.pad * 2

        # --- WINDOW : XY --- #
        MD.window_lx = MD.spad
        MD.window_rx = MD.spad + MD.window_w
        MD.window_ty = round(context.area.height / 2) + round(MD.window_h / 2)
        MD.window_by = MD.window_ty - MD.window_h

        # --- CONTAINERS --- #
        top_y = MD.window_ty - MD.pad
        for container in self.containers:
            container.build(MD, top_y)
            top_y -= container.height(MD)
            top_y -= MD.pad

        # --- MENU BOUNDARY --- #
        self.bounds.build(left_x=MD.window_lx, bottom_y=MD.window_by, w=MD.window_w, h=MD.window_h)
        self.tl = Vector((MD.window_lx, MD.window_ty))
        self.bl = Vector((MD.window_lx, MD.window_by))
        self.tr = Vector((MD.window_rx, MD.window_ty))
        self.br = Vector((MD.window_rx, MD.window_by))

        # --- MENU BATCHES --- #
        self.poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": (self.tl, self.bl, self.tr, self.br)}, indices=[(0, 1, 2), (1, 2, 3)])
        self.line_batches = [
            batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (self.tl, self.bl), "color": (self.prefs.border_secondary_color, self.prefs.border_secondary_color)}), # Left
            batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (self.tr, self.br), "color": (self.prefs.border_primary_color  , self.prefs.border_primary_color)}), # Right
            batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (self.tl, self.tr), "color": (self.prefs.border_secondary_color, self.prefs.border_primary_color)}), # Top
            batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (self.bl, self.br), "color": (self.prefs.border_secondary_color, self.prefs.border_primary_color)})] # Bottom


    def update(self, context, event):
        
        MD = self.MD

        MD.update(context, event)

        for container in self.containers:
            container.reset(MD)

        if MD.locked_item:
            MD.locked_item.update(MD)
            self.status = UX_STATUS.ACTIVE
            if MD.entry_mode_exit_item:
                self.__tab_to_next()
            return

        if self.bounds.point_within_bounds(MD.mouse):
            self.status = UX_STATUS.ACTIVE
            for container in self.containers:
                container.update(MD)
                if MD.locked_item:
                    break
        else:
            self.status = UX_STATUS.INACTIVE


    def mouse_within_bounds(self, event):
        return self.bounds.point_within_bounds(Vector((event.mouse_region_x, event.mouse_region_y)))


    def focus_to_row_by_prop(self, instance=None, prop_name=''):
        for container in self.containers:
            for row in container.rows:
                for prop_map in row.prop_maps:
                    if prop_map.instance == instance and prop_map.prop_name == prop_name:
                        container.externally_ensure_row_visible(row)
                        return


    def __tab_to_next(self):

        MD = self.MD

        event = MD.event
        exited_item = MD.entry_mode_exit_item
        MD.entry_mode_exit_item = None

        if event.type == 'TAB' and event.value == 'RELEASE':
            found = False
            for container in self.containers:
                for row in container.rows:
                    for prop_map in row.prop_maps:
                        for prop_box in prop_map.prop_boxes:
                            if found:
                                attr = prop_map.get_attribute()
                                if type(attr) in {int, float, str, Vector}:
                                    if type(attr) == str and prop_map.list_items:
                                        continue
                                    MD.locked_item = prop_box
                                    container.externally_ensure_locked_box_is_visible(MD)
                                    prop_box.externally_lock_for_entry(MD)
                                    return
                            elif prop_box == exited_item:
                                found = True


    def draw(self):
        if self.hide_menu:
            return
        if self.poly_batch:
            state.blend_set('ALPHA')
            UNIFORM_COLOR.uniform_float("color", self.prefs.background_color)
            self.poly_batch.draw(UNIFORM_COLOR)
            state.blend_set('NONE')
        for line_batch in self.line_batches:
            state.blend_set('ALPHA')
            state.line_width_set(1)
            line_batch.draw(SMOOTH_COLOR)
            state.blend_set('NONE')
        MD = self.MD
        for container in self.containers:
            MD.turn_scissor_off()
            container.draw(MD)
        if isinstance(MD.locked_item, PropBox):
            MD.locked_item.draw(MD)

########################•########################
"""                ENTRY FORMS                """
########################•########################

class EntryFormComponent:
    def __init__(self):
        self.bounds = Rect2D(poly_color=(0,0,0,0), line_color=(0,0,0,0))
        self.labels = []
        self.prefs = user_prefs().drawing


    def build(self, side_padding=0, top_padding=0, text_maps=[], extra_points=[]):
        self.labels = [label for label in self.labels if isinstance(label, Rect2D)]
        if not self.labels:
            return
        points = []
        for label in self.labels:
            points.extend(label.get_corners())
        if extra_points:
            points.extend(extra_points)
        top_left, bottom_right = rectangle_from_bounds_2d(points=points)
        if top_left is None or bottom_right is None:
            return
        left_x = top_left.x - side_padding
        bottom_y = bottom_right.y - top_padding
        w = abs(bottom_right.x - top_left.x) + side_padding * 2
        h = abs(top_left.y - bottom_right.y) + top_padding * 2
        self.bounds.build(left_x=left_x, bottom_y=bottom_y, w=w, h=h, text_maps=text_maps)
        prefs = user_prefs().drawing
        self.bounds.poly_color = prefs.background_color
        self.bounds.line_color = prefs.border_primary_color
        self.bounds.line_width = 2


    def reset(self):
        for label in self.labels:
            label.poly_color = self.prefs.background_color
            label.line_color = self.prefs.border_primary_color


    def update(self, context, event):
        mouse = (event.mouse_region_x, event.mouse_region_y)
        if self.bounds.point_within_bounds(mouse):
            for label in self.labels:
                if label.point_within_bounds(mouse):
                    label.poly_color = self.prefs.background_highlight_color
                    label.line_color = self.prefs.border_secondary_color
                    if len(label.text_maps) == 1:
                        if LMB_press(event):
                            return label.text_maps[0].text
        return ""


    def draw(self):
        self.bounds.draw()
        for label in self.labels:
            label.draw()


class ManualEntryForm:
    def __init__(self):
        self.status = UX_STATUS.INACTIVE
        self.value = None
        self.value_type = None
        self.min_val = None
        self.max_val = None
        self.as_degrees = False
        self.only_file_safe_chars = False
        # Build Data
        self.prefs = user_prefs()
        self.factor = screen_factor()
        self.font_s = self.prefs.drawing.font_size
        self.char_w = round(text_dims("W", self.font_s)[0])
        self.text_h = round(max_text_height(self.font_s))
        self.text_d = round(text_descender_height(self.font_s))
        self.pad = round(self.prefs.drawing.padding * self.factor)
        self.half_pad = round(self.pad / 2)
        self.box_h = round(self.text_h + self.pad * 2)
        self.text_pad = self.pad + self.text_h - self.text_d
        # Controls Text
        self.cancel_text = "Cancel"
        self.empty_space_text = "Space"
        self.clear_all_text = "Clear"
        self.backspace_text = "⌫"
        self.done_text = "OK"
        self.control_texts = [self.cancel_text, self.empty_space_text, self.clear_all_text, self.backspace_text, self.done_text]
        # Components
        self.header_component = None
        self.input_component = None
        self.controls_component = None
        self.cursor_component = None
        self.vkeys_toggle_component = None
        self.vkeys_letters_component = None
        self.vkeys_numbers_component = None
        self.vkeys_brackets_component = None
        self.vkeys_math_ops_component = None
        self.vkeys_math_func_component = None
        # Input
        self.evaluated_text_map = None
        self.eval_lx = 0
        self.eval_rx = 0
        self.input_text_map = None
        self.input_bounds = None
        self.line_color_a = copied_color(self.prefs.drawing.border_primary_color)
        self.line_color_b = copied_color(self.prefs.drawing.border_tertiary_color)
        self.line_color_c = copied_color(self.prefs.drawing.background_color)
        self.line_color_d = copied_color(self.prefs.drawing.font_primary_color)
        self.entry_string = ""
        self.cursor_index = 0
        self.cursor_point_a = Vector((0,0))
        self.cursor_point_b = Vector((0,0))
        # Chars
        self.max_chars_width = self.char_w * 25
        self.chars_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.chars_numbers = "0123456789"
        self.chars_brackets = '[](){}<>'
        self.not_file_safe_chars = '\/:*?"<>|'
        self.math_phrases = ["abs", "cos", "sin"]
        self.final_math_symbols = "0123456789 . () + - ÷ • cos sin abs"
        # Event
        self.capital_letters = True
        self.mouse = Vector((0,0))


    def close(self, context):
        set_manual_input_timer(context, register=False)


    def start(self, context, event, label="", value=None, value_type=None, min_val=None, max_val=None, as_degrees=False, only_file_safe_chars=False, top_y=0):
        if value_type not in {int, float, str}:
            self.status = UX_STATUS.INACTIVE
            return
        
        # Defualts
        self.status = UX_STATUS.ACTIVE
        self.header_component = EntryFormComponent()
        self.input_component = EntryFormComponent()
        self.controls_component = EntryFormComponent()
        self.cursor_component = EntryFormComponent()
        self.vkeys_toggle_component = EntryFormComponent()
        
        # Props Data
        self.value = value
        self.previous_value = value
        self.value_type = value_type
        self.min_val = min_val
        self.max_val = max_val
        self.as_degrees = as_degrees
        self.only_file_safe_chars = only_file_safe_chars
        self.display_virtual_keyboard = self.prefs.settings.display_virtual_keyboard
        self.entry_string = ""
        
        # Build Data
        CENTER_X = round(context.area.width / 2)
        VALUE_TYPE_STR = {int:"Integer", float:"Float", str:"String"}[self.value_type]
        temp_a = text_dims(label, self.font_s)[0] + self.pad * 4
        temp_b = text_dims("Previous", self.font_s)[0] + text_dims(str(self.previous_value), self.font_s)[0] + self.pad * 5
        temp_c = text_dims("Type", self.font_s)[0] + text_dims(VALUE_TYPE_STR, self.font_s)[0] + self.pad * 5
        temp_d = text_dims(self.cancel_text, self.font_s)[0] + text_dims(self.backspace_text, self.font_s)[0] + text_dims(self.done_text, self.font_s)[0] + self.pad * 10
        temp_e = self.max_chars_width + self.pad * 2
        CENTER_W = max([temp_a, temp_b, temp_c, temp_d, temp_e])
        CENTER_LX = CENTER_X - round(CENTER_W / 2)
        CENTER_RX = CENTER_LX + CENTER_W
        FONT_PRIMARY_COLOR = copied_color(self.prefs.drawing.font_primary_color)
        FONT_SECONDARY_COLOR = copied_color(self.prefs.drawing.font_secondary_color)
        FONT_TERTIARY_COLOR = copied_color(self.prefs.drawing.font_tertiary_color)
        BACKGROUND_COLOR = copied_color(self.prefs.drawing.background_color)
        BACKGROUND_SUBMENU_COLOR = copied_color(self.prefs.drawing.background_submenu_color)
        BORDER_PRIMARY_COLOR = copied_color(self.prefs.drawing.border_primary_color)
        BORDER_TERTIARY_COLOR = copied_color(self.prefs.drawing.border_tertiary_color)

        # Build Deltas
        DELTA_Y = top_y if top_y > 0 else round(context.area.height * 0.75)

        # --------------- HEADER --------------- #
        DELTA_Y -= self.pad

        # Label
        text_a = str(label) if label else "Entry Mode"
        label = self.__build_label(text_a=text_a, color_a=FONT_PRIMARY_COLOR, left_x=CENTER_LX, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.header_component.labels.append(label)

        # Type
        DELTA_Y -= self.box_h + self.pad        
        text_a = "Type"
        text_b = VALUE_TYPE_STR
        label = self.__build_label(text_a=text_a, text_b=text_b, color_a=FONT_PRIMARY_COLOR, color_b=FONT_PRIMARY_COLOR, left_x=CENTER_LX, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.header_component.labels.append(label)

        # Previous
        DELTA_Y -= self.box_h + self.pad
        text_a = "Previous"
        text_b = self.__value_to_string(self.previous_value, max_w=CENTER_RX / 2)
        text_b = text_b if text_b else "-"
        label = self.__build_label(text_a=text_a, text_b=text_b, color_a=FONT_PRIMARY_COLOR, color_b=FONT_TERTIARY_COLOR, left_x=CENTER_LX, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.header_component.labels.append(label)

        # Evaluated
        if self.value_type in {int, float}:
            DELTA_Y -= self.box_h + self.pad        
            text_a = "Evaluated"
            text_b = "(>~.~)>"
            label = self.__build_label(text_a=text_a, text_b=text_b, color_a=FONT_PRIMARY_COLOR, color_b=FONT_TERTIARY_COLOR, left_x=CENTER_LX, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            if label:
                if len(label.text_maps) == 2:
                    self.eval_lx = CENTER_X
                    self.eval_rx = CENTER_RX
                    self.evaluated_text_map = label.text_maps[1]
                    self.header_component.labels.append(label)
        
        # Build
        self.header_component.build(side_padding=self.pad, top_padding=self.pad)
        DELTA_Y -= self.box_h + self.pad
        
        # --------------- INPUT --------------- #
        DELTA_Y -= self.pad
        min_max_pad = text_dims("100,000.000", self.font_s)[0]
        
        # Input
        label = self.__build_label(text_a="VAL", color_a=FONT_SECONDARY_COLOR, left_x=CENTER_LX, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.input_component.labels.append(label)
            self.input_text_map = label.text_maps[0]
            self.input_bounds = label
        
        # Min
        y = DELTA_Y - self.text_pad
        text = "∞" if self.min_val is None else self.__value_to_string(self.min_val, max_w=min_max_pad)
        text_w = text_dims(text, self.font_s)[0]
        x = CENTER_LX - min_max_pad + round((min_max_pad - text_w) / 2)
        color = FONT_TERTIARY_COLOR if self.min_val else FONT_SECONDARY_COLOR
        min_text_map = TextMap(text=text, font_size=self.font_s, color=color, location=Vector((x, y)))
        
        # Max
        text = "∞" if self.max_val is None else self.__value_to_string(self.max_val, max_w=min_max_pad)
        text_w = text_dims(text, self.font_s)[0]
        x = CENTER_RX + round((min_max_pad - text_w) / 2)
        color = FONT_TERTIARY_COLOR if self.max_val else FONT_SECONDARY_COLOR
        max_text_map = TextMap(text=text, font_size=self.font_s, color=color, location=Vector((x, y)))
        
        # Build
        side_padding = min_max_pad + self.pad * 2
        self.input_component.build(side_padding=side_padding, top_padding=self.pad, text_maps=[min_text_map, max_text_map])
        DELTA_Y -= self.box_h + self.pad
        
        # --------------- CONTROLS --------------- #
        DELTA_Y -= self.pad
        space = round(CENTER_W / len(self.control_texts))
        left_x = CENTER_LX
        half_pad = round(self.pad / 2)
        for text in self.control_texts:
            right_x = left_x + space if text != self.control_texts[-1] else CENTER_RX
            left_pad = half_pad if text != self.control_texts[0] else 0
            right_pad = half_pad if text != self.control_texts[-1] else 0
            label = self.__build_label(text_a=text, color_a=FONT_SECONDARY_COLOR, left_x=left_x + left_pad, right_x=right_x - right_pad, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            if label:
                left_x += space
                self.controls_component.labels.append(label)
        
        # Build
        self.controls_component.build(side_padding=self.pad, top_padding=self.pad)
        
        # --------------- CURSOR --------------- #
        left_x = CENTER_RX + self.pad * 2
        width = text_dims("← →", self.font_s)[0] + self.pad * 5
        right_x = left_x + width
        half = round(width / 2)
        
        # Left
        label = self.__build_label(text_a="←", color_a=FONT_SECONDARY_COLOR, left_x=left_x, right_x=left_x + half - self.half_pad, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.cursor_component.labels.append(label)
        
        # Right
        label = self.__build_label(text_a="→", color_a=FONT_SECONDARY_COLOR, left_x=left_x + half + self.half_pad, right_x=right_x, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.cursor_component.labels.append(label)
        
        # Build
        self.cursor_component.build(side_padding=self.pad, top_padding=self.pad, text_maps=[])
        DELTA_Y -= self.box_h + self.pad
        
        # --------------- VK Toggle --------------- #
        DELTA_Y -= self.pad
        
        # ON / OFF
        switch_width = text_dims("OFF", self.font_s)[0] + self.pad * 2
        left_x = CENTER_RX - switch_width
        label = self.__build_label(text_a="ON", color_a=FONT_SECONDARY_COLOR, left_x=left_x, right_x=CENTER_RX, top_y=DELTA_Y, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.vkeys_toggle_component.labels.append(label)
        
        # VK Text Map
        x = CENTER_LX + self.pad
        y = DELTA_Y - self.text_pad
        text_map = TextMap(text="Virtual Keys", font_size=self.font_s, color=FONT_PRIMARY_COLOR, location=Vector((x, y)))
        
        # Build
        self.vkeys_toggle_component.build(side_padding=self.pad, top_padding=self.pad, text_maps=[text_map], extra_points=[Vector((CENTER_LX, DELTA_Y))])
        DELTA_Y -= self.box_h + self.pad
        
        # --------------- VIRTUAL KEYS SETUP --------------- #
        DELTA_Y -= self.pad
        DELTA_LEFT_X = 0
        BOX_W = self.char_w + self.pad * 2
        letters_w = ((BOX_W + self.pad) * 10) + (self.pad)
        numbers_w = ((BOX_W + self.pad) * 3) + (self.pad)
        brackets_w = ((BOX_W + self.pad) * 2) + (self.pad)
        math_ops_w = ((BOX_W + self.pad) * 1) + (self.pad)
        math_funcs_w = ((BOX_W + self.pad) * 2) + (self.pad)
        if self.value_type == str:
            total_w = letters_w + numbers_w +  brackets_w
            DELTA_LEFT_X = CENTER_X - round(total_w / 2)
        elif self.value_type in {int, float}:
            total_w = numbers_w + math_ops_w + math_funcs_w
            DELTA_LEFT_X = CENTER_X - round(total_w / 2)
        
        # --------------- VK LETTERS --------------- #
        if self.value_type == str:
            self.vkeys_letters_component = EntryFormComponent()
            row_1_chars = "QWERTYUIOP"
            row_2_chars = "ASDFGHJKL"
            row_3_chars = "ZXCVBNM"
            row_4_chars = "_-@#$%&:!?"
            half = round((BOX_W + self.pad) / 2)
            ty = DELTA_Y
            
            # Row 1
            labels = self.__build_row_from_chars(chars=row_1_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_letters_component.labels.extend(labels)
            ty -= self.box_h + self.pad
            
            # Row 2
            left_x = DELTA_LEFT_X + half
            labels = self.__build_row_from_chars(chars=row_2_chars, color=FONT_SECONDARY_COLOR, left_x=left_x, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_letters_component.labels.extend(labels)
            ty -= self.box_h + self.pad
            
            # Row 3
            left_x = DELTA_LEFT_X + half - self.pad
            labels = self.__build_row_from_chars(chars=row_3_chars, color=FONT_SECONDARY_COLOR, left_x=left_x, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_letters_component.labels.extend(labels)
            left_x += ((BOX_W + self.pad) * 7)
            shift_box_w = BOX_W * 2.5 + self.pad
            right_x = left_x + shift_box_w
            label = self.__build_label(text_a="Shift", color_a=FONT_SECONDARY_COLOR, left_x=left_x, right_x=right_x, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            if label:
                self.vkeys_letters_component.labels.append(label)
            ty -= self.box_h + self.pad
            
            # Row 4
            labels = self.__build_row_from_chars(chars=row_4_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_letters_component.labels.extend(labels)
            
            # Build
            self.vkeys_letters_component.build(side_padding=self.pad, top_padding=self.pad)
            DELTA_LEFT_X += letters_w
        
        # --------------- VK NUMBERS --------------- #
        self.vkeys_numbers_component = EntryFormComponent()
        row_1_chars = "789"
        row_2_chars = "456"
        row_3_chars = "123"
        ty = DELTA_Y
        
        # Row 1
        labels = self.__build_row_from_chars(chars=row_1_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        self.vkeys_numbers_component.labels.extend(labels)
        ty -= self.box_h + self.pad
        
        # Row 2
        labels = self.__build_row_from_chars(chars=row_2_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        self.vkeys_numbers_component.labels.extend(labels)
        ty -= self.box_h + self.pad
        
        # Row 3
        labels = self.__build_row_from_chars(chars=row_3_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        self.vkeys_numbers_component.labels.extend(labels)
        ty -= self.box_h + self.pad
        
        # Row 4
        right_x = DELTA_LEFT_X + BOX_W * 2 + self.pad
        label = self.__build_label(text_a="0", color_a=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, right_x=right_x, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.vkeys_numbers_component.labels.append(label)
        left_x = right_x + self.pad
        label = self.__build_label(text_a=".", color_a=FONT_SECONDARY_COLOR, left_x=left_x, right_x=left_x + BOX_W, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
        if label:
            self.vkeys_numbers_component.labels.append(label)
        
        # Build
        self.vkeys_numbers_component.build(side_padding=self.pad, top_padding=self.pad)
        DELTA_LEFT_X += numbers_w
        
        # --------------- VK BRACKETS --------------- #
        if self.value_type == str:
            self.vkeys_brackets_component = EntryFormComponent()
            row_1_chars = "[]"
            row_2_chars = "()"
            row_3_chars = "{}"
            row_4_chars = "<>"
            ty = DELTA_Y
            
            # Row 1
            labels = self.__build_row_from_chars(chars=row_1_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_brackets_component.labels.extend(labels)
            ty -= self.box_h + self.pad
            
            # Row 2
            labels = self.__build_row_from_chars(chars=row_2_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_brackets_component.labels.extend(labels)
            ty -= self.box_h + self.pad
            
            # Row 3
            labels = self.__build_row_from_chars(chars=row_3_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_brackets_component.labels.extend(labels)
            ty -= self.box_h + self.pad
            
            # Row 4
            labels = self.__build_row_from_chars(chars=row_4_chars, color=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, top_y=ty, box_w=BOX_W, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
            self.vkeys_brackets_component.labels.extend(labels)
            
            # Build
            self.vkeys_brackets_component.build(side_padding=self.pad, top_padding=self.pad)
            DELTA_LEFT_X += brackets_w
        
        # --------------- VK MATH OPS --------------- #
        if self.value_type in {int, float}:
            self.vkeys_math_ops_component = EntryFormComponent()
            column_chars = "÷x-+"
            ty = DELTA_Y
            for char in column_chars:
                label = self.__build_label(text_a=char, color_a=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, right_x=DELTA_LEFT_X + BOX_W, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR, font_size=self.font_s+2)
                if label:
                    ty -= self.box_h + self.pad
                    self.vkeys_math_ops_component.labels.append(label)
            self.vkeys_math_ops_component.build(side_padding=self.pad, top_padding=self.pad)
            DELTA_LEFT_X += math_ops_w
        
        # --------------- VK MATH FUNC --------------- #
        if self.value_type in {int, float}:
            self.vkeys_math_func_component = EntryFormComponent()
            ty = DELTA_Y
            left_x = DELTA_LEFT_X
            
            # Row 1
            row_1_chars = "()"
            for char in row_1_chars:
                label = self.__build_label(text_a=char, color_a=FONT_SECONDARY_COLOR, left_x=left_x, right_x=left_x + BOX_W, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
                if label:
                    left_x += BOX_W + self.pad
                    self.vkeys_math_func_component.labels.append(label)
            ty -= self.box_h + self.pad
            
            # Row 2-4
            right_x = DELTA_LEFT_X + (len(row_1_chars) * BOX_W) + self.pad
            for text in self.math_phrases:
                label = self.__build_label(text_a=text, color_a=FONT_SECONDARY_COLOR, left_x=DELTA_LEFT_X, right_x=right_x, top_y=ty, poly_color=BACKGROUND_COLOR, line_color=BORDER_PRIMARY_COLOR)
                if label:
                    ty -= self.box_h + self.pad
                    self.vkeys_math_func_component.labels.append(label)
            
            # Build
            self.vkeys_math_func_component.build(side_padding=self.pad, top_padding=self.pad)
        
        # --------------- SETUP --------------- #
        if self.state_is_valid():
            self.__set_drawing_text()
            self.__update_cursor_position()


    def update(self, context, event):
        if not self.state_is_valid():
            set_manual_input_timer(context, register=False)
            self.status = UX_STATUS.INACTIVE
            return

        # Cancel
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self.status = UX_STATUS.INACTIVE
            self.value = None
            set_manual_input_timer(context, register=False)
            return

        # Init Oscillation
        if AREA is None:
            set_manual_input_timer(context, register=True)

        self.mouse.x = event.mouse_region_x
        self.mouse.y = event.mouse_region_y

        if self.__update_controls(context, event):
            if self.status == UX_STATUS.INACTIVE:
                set_manual_input_timer(context, register=False)
            return

        self.__update_cursor(context, event)
        self.__update_vkey_toggle(context, event)

        virtual_key = self.__update_vkey_components(context, event)

        if virtual_key == "Shift":
            virtual_key = ""
            self.capital_letters = not self.capital_letters
            for label in self.vkeys_letters_component.labels:
                if len(label.text_maps) == 1:
                    text = label.text_maps[0].text
                    if text.upper() in self.chars_alphabet:
                        label.text_maps[0].text = text.upper() if self.capital_letters else text.lower()

        char = virtual_key if virtual_key else ""
        char = event.ascii if not char and event.value == 'PRESS' else char
        self.__append_char(context, char)


    def state_is_valid(self):
        if self.status == UX_STATUS.INACTIVE:
            return False
        if not (self.input_component and self.controls_component and self.cursor_component and self.vkeys_toggle_component):
            return False
        if not (self.input_text_map and self.input_bounds):
            return False
        if len(self.vkeys_toggle_component.labels) != 1:
            return False
        if self.value_type == str:
            if not (self.vkeys_letters_component and self.vkeys_numbers_component and self.vkeys_brackets_component):
                return False
        elif self.value_type in {int, float}:
            if not self.evaluated_text_map:
                return False
            if not (self.vkeys_numbers_component and self.vkeys_math_ops_component and self.vkeys_math_func_component):
                return False
        return True


    def evaluate_entry(self):
        if self.value_type in {int, float}:
            if not self.entry_string:
                self.value = None
            try:
                expression = str(self.entry_string)
                if '÷' in expression:
                    expression = expression.replace("÷", "/")
                if 'x' in expression:
                    expression = expression.replace("x", "*")
                if '•' in expression:
                    expression = expression.replace("•", "*")
                result = radians(eval(expression)) if self.as_degrees else eval(expression)
                value = int(result) if self.value_type == int else round(float(result), 3)
                if self.min_val and value < self.min_val:
                    self.value = self.min_val
                elif self.max_val and value > self.max_val:
                    self.value = self.max_val
                else:
                    self.value = value
            except:
                self.value = None
        elif self.value_type == str:
            if type(self.entry_string) != str:
                self.entry_string = str(self.entry_string)
            if self.max_val and len(self.entry_string) > self.max_val:
                self.entry_string = self.entry_string[len(self.entry_string) - self.max_val:]
            self.value = fitted_text_to_width(self.entry_string, max_w=self.max_chars_width, left_to_right=True, overage_text="")


    def draw(self):
        if not self.state_is_valid():
            return
        
        self.input_bounds.line_color = self.line_color_a.lerp(self.line_color_b, OSCILLATION)
        self.header_component.draw()
        self.input_component.draw()
        draw_line(p1=self.cursor_point_a, p2=self.cursor_point_b, width=1, color=self.line_color_c.lerp(self.line_color_d, OSCILLATION))
        self.controls_component.draw()
        self.cursor_component.draw()
        self.vkeys_toggle_component.draw()

        if self.display_virtual_keyboard:
            if self.value_type == str:
                if self.vkeys_letters_component:
                    self.vkeys_letters_component.draw()
                if self.vkeys_numbers_component:
                    self.vkeys_numbers_component.draw()
                if self.vkeys_brackets_component:
                    self.vkeys_brackets_component.draw()
            elif self.value_type in {int, float}:
                if self.vkeys_numbers_component:
                    self.vkeys_numbers_component.draw()
                if self.vkeys_math_ops_component:
                    self.vkeys_math_ops_component.draw()
                if self.vkeys_math_func_component:
                    self.vkeys_math_func_component.draw()


    def __build_label(self, text_a="", text_b="", color_a=(0,0,0,1), color_b=(0,0,0,1), left_x=0, right_x=0, top_y=0, poly_color=(0,0,0,1), line_color=(0,0,0,1), font_size=-1):

        font_size = font_size if font_size > 0 else self.font_s

        label_w = abs(right_x - left_x)
        label_cx = left_x + round(label_w / 2)
        text_y = top_y - self.text_pad

        text_a_w = text_dims(text_a, font_size)[0]
        text_b_w = text_dims(text_b, font_size)[0] if text_b else 0
        text_maps = []
        if text_b_w == 0:
            text_map_a = TextMap(text=text_a, font_size=font_size, color=color_a)
            x = left_x + round((label_w - text_a_w) / 2)
            text_map_a.location = Vector((x, text_y))
            text_maps.append(text_map_a)
        else:
            text_map_a = TextMap(text=text_a, font_size=font_size, color=color_a)
            x = left_x + self.pad
            text_map_a.location = Vector((x, text_y))
            text_maps.append(text_map_a)

            text_map_b = TextMap(text=text_b, font_size=font_size, color=color_b)
            x = label_cx + round(((label_w / 2) - text_b_w) / 2)
            text_map_b.location = Vector((x, text_y))
            text_maps.append(text_map_b)

        label = Rect2D(poly_color=poly_color, line_color=line_color, line_width=1)
        y = top_y - self.box_h
        label.build(left_x=left_x, bottom_y=y, w=label_w, h=self.box_h, text_maps=text_maps)
        return label


    def __build_row_from_chars(self, chars="", color=(0,0,0,0), left_x=0, top_y=0, box_w=0, poly_color=(0,0,0,1), line_color=(0,0,0,1)):
        labels = []
        for char in chars:
            label = self.__build_label(text_a=char, color_a=color, left_x=left_x, right_x=left_x + box_w, top_y=top_y, poly_color=poly_color, line_color=line_color)
            if label:
                labels.append(label)
                left_x += box_w + self.pad
        return labels


    def __value_to_string(self, value, max_w=0):
        text = str(value)
        if type(value) == int:
            if self.as_degrees:
                text = str(int(degrees(value)))
            else:
                text = str(value)
        elif type(value) == float:
            if self.as_degrees:
                text = str(round(degrees(value), 3))
            else:
                text = str(round(value, 3))
        if self.as_degrees and value != None:
            degree_width = text_dims("º", self.font_s)[0]
            text = fitted_text_to_width(text, max_w=round(max_w - degree_width), left_to_right=True, overage_text="")
            text = f"{text}º"
        else:
            text = fitted_text_to_width(text, max_w=round(max_w), left_to_right=True, overage_text="")
        return text


    def __update_controls(self, context, event):
        # Reset / Update
        self.controls_component.reset()
        controls_text = self.controls_component.update(context, event)
        # Cancel
        if controls_text == self.cancel_text:
            self.status = UX_STATUS.INACTIVE
            self.value = None
            return True
        # Space
        elif controls_text == self.empty_space_text or (event.type == 'SPACE' and event.value == 'PRESS'):
            self.__append_char(context, char=" ")
            self.__set_drawing_text()
            return True
        # Clear All
        elif controls_text == self.clear_all_text or (event.ctrl and event.type == 'BACK_SPACE' and event.value == 'PRESS'):
            self.entry_string = ""
            self.input_text_map.text = self.entry_string
            self.__set_drawing_text()
            self.__update_cursor_position()
            return True
        # Backspace
        elif controls_text == self.backspace_text or (event.type == 'BACK_SPACE' and event.value == 'PRESS'):
            self.__backspace_char()
            return True
        # Done
        elif controls_text == self.done_text or (event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS'):
            self.evaluate_entry()
            self.status = UX_STATUS.INACTIVE
            return True
        return False


    def __update_cursor(self, context, event):
        self.cursor_component.reset()
        cursor_text = self.cursor_component.update(context, event)
        if cursor_text == '←' or (event.type == 'LEFT_ARROW' and event.value == 'PRESS'):
            if event.ctrl:
                indices = [index for index, char in enumerate(self.entry_string) if index < self.cursor_index - 1 and char in '[](){}<> ']
                if indices:
                    self.cursor_index = indices[-1] + 1
                else:
                    self.cursor_index = 0
            else:
                self.cursor_index -= 1
            self.__update_cursor_position()
        elif cursor_text == '→' or (event.type == 'RIGHT_ARROW' and event.value == 'PRESS'):
            if event.ctrl:
                indices = [index for index, char in enumerate(self.entry_string) if index > self.cursor_index and char in '[](){}<> ']
                if indices:
                    self.cursor_index = indices[0]
                else:
                    self.cursor_index = len(self.entry_string)
            else:
                self.cursor_index += 1
            self.__update_cursor_position()
        elif event.type == 'HOME' and event.value == 'PRESS':
            self.cursor_index = 0
            self.__update_cursor_position()
        elif event.type == 'END' and event.value == 'PRESS':
            self.cursor_index = len(self.entry_string)
            self.__update_cursor_position()


    def __update_cursor_position(self):
        if self.cursor_index < 0:
            self.cursor_index = 0
        if self.cursor_index > len(self.entry_string):
            self.cursor_index = len(self.entry_string)
        half = round(self.pad / 2)
        x = self.input_text_map.location.x
        x += text_dims(self.entry_string[:self.cursor_index], self.font_s)[0]
        ty = self.input_bounds.tl.y - half
        by = self.input_bounds.bl.y + half
        self.cursor_point_a = Vector((x,ty))
        self.cursor_point_b = Vector((x,by))


    def __update_vkey_toggle(self, context, event):
        self.vkeys_toggle_component.reset()
        if self.vkeys_toggle_component.bounds.point_within_bounds(self.mouse):
            label = self.vkeys_toggle_component.labels[0]
            label.poly_color = self.prefs.drawing.background_highlight_color
            label.line_color = self.prefs.drawing.border_secondary_color
            if LMB_press(event):
                self.prefs.settings.display_virtual_keyboard = not self.prefs.settings.display_virtual_keyboard
                self.display_virtual_keyboard = self.prefs.settings.display_virtual_keyboard
                if len(label.text_maps) > 0:
                    label.text_maps[0].text = "ON" if self.prefs.settings.display_virtual_keyboard else "OFF"


    def __update_vkey_components(self, context, event):
        if not self.display_virtual_keyboard:
            return ""
        virtual_key = ""
        if self.value_type == str:
            self.vkeys_letters_component.reset()
            self.vkeys_numbers_component.reset()
            self.vkeys_brackets_component.reset()
            virtual_key = self.vkeys_letters_component.update(context, event)
            if not virtual_key:
                virtual_key = self.vkeys_numbers_component.update(context, event)
            if not virtual_key:
                virtual_key = self.vkeys_brackets_component.update(context, event)
        elif self.value_type in {int, float}:
            self.vkeys_numbers_component.reset()
            self.vkeys_math_ops_component.reset()
            self.vkeys_math_func_component.reset()
            virtual_key = self.vkeys_numbers_component.update(context, event)
            if not virtual_key:
                virtual_key = self.vkeys_math_ops_component.update(context, event)
            if not virtual_key:
                virtual_key = self.vkeys_math_func_component.update(context, event)
        return virtual_key


    def __append_char(self, context, char=""):
        if not char:
            return
        if self.value_type in {int, float}:
            if char in "xX*":
                char = '•'
            elif char in '\|/':
                char = '÷'
            lower = char.lower()
            first_char = lower[0] if len(lower) > 1 else lower
            if first_char in 'cos sin abs':
                if first_char == 'c':
                    char = 'cos()'
                elif first_char == 's':
                    char = 'sin()'
                elif first_char == 'a':
                    char = 'abs()'
                elif char != ' ':
                    return
            elif char not in self.final_math_symbols:
                return
        elif self.value_type == str:
            if self.max_val and len(self.entry_string) == self.max_val:
                return
            if self.only_file_safe_chars and char in self.not_file_safe_chars:
                notify(context, messages=[("Not file safe", f"${char}")])
                return
        text_w = text_dims(self.entry_string + char, self.font_s)[0]
        if text_w < self.max_chars_width:
            self.entry_string = self.entry_string[:self.cursor_index] + char + self.entry_string[self.cursor_index:]
            self.input_text_map.text = self.entry_string
            if len(char) > 1:
                self.cursor_index += len(char) - 1
            else:
                self.cursor_index += 1
            self.__set_drawing_text()
            self.__update_cursor_position()


    def __backspace_char(self):
        if len(self.entry_string) > 0 and self.cursor_index > 0:
            self.entry_string = self.entry_string[:self.cursor_index - 1] + self.entry_string[self.cursor_index:]
            self.cursor_index -= 1
            self.__set_drawing_text()
            self.__update_cursor_position()


    def __set_drawing_text(self):
        lx = self.input_bounds.bl.x
        bounds_w = self.input_bounds.width
        text_w = text_dims(self.entry_string, self.font_s)[0]
        self.input_text_map.text = self.entry_string
        self.input_text_map.location.x = lx + round((bounds_w - text_w) / 2)

        if self.evaluated_text_map and self.value_type in {int, float}:
            self.evaluate_entry()
            eval_w = abs(self.eval_lx - self.eval_rx)
            eval_text = self.__value_to_string(self.value, max_w=eval_w)
            self.evaluated_text_map.text = eval_text
            eval_text_w = text_dims(eval_text, self.font_s)[0]
            self.evaluated_text_map.location.x = self.eval_lx + round((eval_w - eval_text_w) / 2)

########################•########################
"""                  SLIDES                   """
########################•########################

def limits_text(slide_prop, position='LEFT', float_to_3=False):
    attr = slide_prop.get_attr()
    text = ""
    # LIST | TUPLE | STRING
    if type(attr) in {list, tuple, str}:
        if position == 'LEFT':
            text = str(attr[0]) if len(attr) > 0 else "0"
        elif position == 'RIGHT':
            text = str(attr[-1]) if len(attr) > 0 else "0"
        elif position == 'CENTER':
            if slide_prop.index >= 0 and slide_prop.index < len(attr):
                text = str(attr[slide_prop.index])
        if slide_prop.as_degrees:
            text = f"{text}º"
    # BOOL
    elif type(attr) == bool:
        if position == 'LEFT':
            text = "Off"
        elif position == 'RIGHT':
            text = "On"
        elif position == 'CENTER':
            text = "On" if attr else "Off"
    # INT
    elif type(attr) == int:
        value = 0
        if position == 'LEFT':
            value = int(slide_prop.min_val)
        elif position == 'RIGHT':
            value = int(slide_prop.max_val)
        elif position == 'CENTER':
            value = int(attr)
        if slide_prop.as_degrees:
            text = f"{round(degrees(value))}º"
        else:
            text = str(value)
    # FLOAT
    elif type(attr) == float:
        value = 0.0
        if position == 'LEFT':
            value = slide_prop.min_val
        elif position == 'RIGHT':
            value = slide_prop.max_val
        elif position == 'CENTER':
            value = attr
        if slide_prop.as_degrees:
            if float_to_3:
                text = f"{round(degrees(value), 3):.03f}º"
            else:
                text = f"{round(degrees(value))}º"
        else:
            if float_to_3:
                text = f"{round(value, 3):.03f}"
            else:
                text = f"{round(value, 3)}"
    return text.replace('_', ' ').title()


class SlideData:
    def __init__(self, context, event, slide_props=[], slide_bar_props=[], slide_panel_props=[]):
        # Slide Prop Data
        self.slide_props = slide_props
        self.slide_bar_props = slide_bar_props
        self.slide_panel_props = slide_panel_props
        # Types
        self.slide_bar_types = {int, float, list}
        self.slide_panel_types = {bool, tuple}
        # Dimensions
        self.prefs = user_prefs().drawing
        self.factor = screen_factor()
        self.smpad = self.prefs.slide_menu_padding
        self.spad = round(self.prefs.screen_padding * self.factor)
        self.pad = round(self.prefs.padding * self.factor)
        self.font_s = self.prefs.font_size
        self.char_w = round(text_dims("W", self.font_s)[0])
        self.text_h = round(max_text_height(self.font_s))
        self.text_d = round(text_descender_height(self.font_s))
        self.box_h = round(self.text_h + self.pad * 2)
        self.area_w = context.area.width
        self.area_h = context.area.height
        self.area_center_x = round(self.area_w / 2)
        self.area_center_y = round(self.area_h / 2)
        self.slider_w = round(self.area_w / 3)
        self.slider_lx = self.area_center_x - round(self.slider_w / 2)
        self.slider_rx = self.area_center_x + round(self.slider_w / 2)
        self.slide_bar_tip_loc = Vector((0,0))
        self.slide_panel_tip_y = 0
        # Clamp for Dot Move
        self.min_dot_y = int(self.spad + self.pad)
        if self.smpad > self.area_h - self.spad - self.pad:
            self.prefs.slide_menu_padding = 0
            self.smpad = self.prefs.slide_menu_padding
        # Delta
        self.build_y = self.area_h - self.smpad
        self.farthest_rx = 0
        self.farthest_lx = self.area_w
        self.slide_bar_lowest_y = 0
        # Locks
        self.locked_item = None
        self.ui_was_clicked = False
        self.locked_mini_slider = None
        # Events
        self.context = context
        self.event = event
        self.prefs = user_prefs().drawing
        self.mouse = Vector((0,0))
        self.LMB_pressed = False
        self.LMB_released = False
        self.mouse_dragging = False
        self.accumulation_threshold = round(self.area_w / 60)
        self.item_to_draw_ontop = None
        self.update(context, event)


    def update(self, context, event):
        self.context = context
        self.event = event
        self.mouse.x = event.mouse_region_x
        self.mouse.y = event.mouse_region_y
        self.LMB_pressed = LMB_press(event)
        self.LMB_released = LMB_release(event)
        self.mouse_dragging = is_mouse_dragging(event)


class MiniSlider:
    def __init__(self, SD, slide_prop=None, add=True):
        self.slide_prop = slide_prop
        self.add = add
        # Circle
        self.sign_text = "+" if self.add else "-"
        self.circle_map = TextMap()
        self.circle_line_color = SD.prefs.border_secondary_color
        self.circle_poly_color = SD.prefs.background_color
        self.circle_poly_batch = None
        self.circle_line_batch = None
        self.circle_r = round(SD.box_h / 2)
        self.circle_detection = self.circle_r + SD.pad
        # Line
        self.line_color_a = SD.prefs.slider_negative_color
        self.line_color_b = SD.prefs.slider_positive_color
        self.anchor_point_a = Vector((0,0))
        self.anchor_point_b = Vector((0,0))
        self.anchor_point_c = Vector((0,0))
        # Info
        self.info_map = TextMap()
        self.label = []
        # Event
        self.threshold = 45 * SD.factor
        self.circle_center = Vector((0, 0))
        self.label_lx = 0
        self.label_ty = 0
        self.track_point = Vector((0,0))
        self.limit_reached_msg = None


    def build(self, SD:SlideData, rx=0, cy=0, anchor_point=Vector((0,0))):
        ty = cy + round(SD.box_h / 2)
        by = ty - SD.box_h
        circle_cx = rx - self.circle_r
        self.circle_detection = self.circle_r + SD.pad
        self.anchor_point_a = anchor_point.copy()
        self.anchor_point_b = Vector((circle_cx - self.circle_r, cy))
        self.anchor_point_c = Vector((circle_cx + self.circle_r, cy))
        # Circle Map
        self.circle_map.font_size = SD.font_s
        self.circle_map.text = self.sign_text
        x = circle_cx - round(text_dims(self.sign_text, SD.font_s)[0] / 2)
        y = cy - SD.text_d
        self.circle_map.location = Vector((x, y))
        # Circle Batches
        self.circle_center = Vector((circle_cx, cy))
        res = 18
        step = (pi * 2) / res
        points = [Vector((cos(step * i), sin(step * i))) * self.circle_r + self.circle_center for i in range(res + 1)]
        indices = [(0, i, i+1) for i in range(res - 1)]
        self.circle_poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=indices)
        self.circle_line_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})
        # Info Map
        self.__set_info_data(SD)
        self.info_map.font_size = SD.font_s
        x = circle_cx - (self.circle_r + SD.char_w * 5)
        y = cy - SD.text_d
        self.info_map.location = Vector((x, y))
        self.__set_label_data(SD)


    def reset(self, SD:SlideData):
        if SD.locked_mini_slider == self:
            return
        self.__set_info_data(SD)
        self.__set_label_data(SD)
        self.circle_poly_color = SD.prefs.background_color
        self.limit_reached_msg = None


    def update(self, SD:SlideData):
        # Event Finder
        if SD.locked_mini_slider is None:
            if (self.circle_center - SD.mouse).length <= self.circle_detection:
                if not self.__attr_is_max():
                    self.circle_line_color = SD.prefs.border_secondary_color
                    self.circle_poly_color = SD.prefs.background_highlight_color
                    SD.locked_mini_slider = self
                    self.track_point = SD.mouse.copy()
        # Stretch-Arm-Strong
        elif SD.locked_mini_slider == self:
            delta = (self.track_point - SD.mouse).length
            threshold = self.threshold
            if SD.event.shift:
                threshold *= 2
            elif SD.event.ctrl:
                threshold *= 4
            elif SD.event.alt:
                threshold /= 2
            # Threshold Requirements
            if delta >= threshold:
                self.track_point = SD.mouse.copy()
                prop_type = self.slide_prop.prop_type
                value = self.slide_prop.get_attr()
                # Increase
                if prop_type == int:
                    value += self.slide_prop.increment if self.add else -self.slide_prop.increment
                else:
                    value += self.slide_prop.increment if self.add else -self.slide_prop.increment
                # Limits : MAX
                if self.add and value > self.slide_prop.max_val:
                    if self.slide_prop.soft_max:
                        self.slide_prop.max_val = value
                    else:
                        value = self.slide_prop.max_val
                        self.limit_reached_msg = ("Limit", "MAX")
                # Limits : MIN
                elif not self.add and value < self.slide_prop.min_val:
                    if self.slide_prop.soft_min:
                        self.slide_prop.min_val = value
                    else:
                        value = self.slide_prop.min_val
                        self.limit_reached_msg = ("Limit", "MIN")
                
                self.slide_prop.set_attribute(value, SD)
                self.slide_prop.invoke_callback(SD)
            self.__set_info_data(SD)
            self.__set_label_data(SD)


    def __set_label_data(self, SD:SlideData):
        self.label.clear()
        value_text = limits_text(self.slide_prop, position='CENTER', float_to_3=True)
        self.label.append((self.slide_prop.label, value_text))
        if type(self.limit_reached_msg) == tuple:
            self.label.append(self.limit_reached_msg)
        else:
            self.label.append(("SHIFT", "1/2 Speed"))
            self.label.append(("CTRL" , "1/4 Speed"))
            self.label.append(("ALT"  , "2x Speed"))
        self.label_lx = SD.mouse.x - round(label_dims(self.label, SD.font_s)[0] + self.circle_r * 2 + SD.pad * 2)
        self.label_ty = SD.mouse.y + round(SD.box_h / 2)
        if self.__attr_is_max():
            self.circle_map.color = SD.prefs.font_tertiary_color
            self.circle_line_color = SD.prefs.font_tertiary_color
        else:
            self.circle_map.color = SD.prefs.font_secondary_color
            self.circle_line_color = SD.prefs.font_secondary_color


    def __attr_is_max(self):
        attr = self.slide_prop.get_attr()
        if type(attr) not in {int, float}:
            return False
        if self.add:
            if self.slide_prop.soft_max == False and attr >= self.slide_prop.max_val:
                return True
        else:
            if self.slide_prop.soft_min == False and attr <= self.slide_prop.min_val:
                return True
        return False


    def __set_info_data(self, SD:SlideData):
        if self.add:
            self.info_map.text = str(round(self.slide_prop.max_val, 3))
            self.info_map.color = SD.prefs.font_secondary_color if self.slide_prop.soft_max else SD.prefs.font_tertiary_color
        else:
            self.info_map.text = str(round(self.slide_prop.min_val, 3))
            self.info_map.color = SD.prefs.font_secondary_color if self.slide_prop.soft_min else SD.prefs.font_tertiary_color


    def draw(self, SD:SlideData):
        if self.circle_poly_batch and self.circle_line_batch:
            state.blend_set('ALPHA')
            UNIFORM_COLOR.uniform_float("color", self.circle_poly_color)
            self.circle_poly_batch.draw(UNIFORM_COLOR)
            state.line_width_set(1)
            UNIFORM_COLOR.uniform_float("color", self.circle_line_color)
            self.circle_line_batch.draw(UNIFORM_COLOR)
            self.circle_map.draw()
            state.blend_set('NONE')
        if SD.locked_mini_slider == self:
            draw_label(messages=self.label, left_x=self.label_lx, top_y=self.label_ty)
            draw_line_smooth_colors(SD.mouse, self.anchor_point_b, width=1, color_1=self.line_color_a, color_2=self.line_color_b)
        elif SD.locked_mini_slider != None:
            self.info_map.draw()
        else:
            self.info_map.draw()
            draw_line_smooth_colors(self.anchor_point_c, self.anchor_point_a, width=1, color_1=self.line_color_a, color_2=self.line_color_b)


class SlidePanelItem:
    def __init__(self, slide_prop=None):
        self.slide_prop = slide_prop
        self.label_map = TextMap()
        self.value_map = TextMap()
        self.tip_map = TextMap()
        self.label_bounds = Rect2D()
        self.detection_bounds = Rect2D()
        self.opt_labels = []
        self.opt_labels_bounds = Rect2D()
        self.mini_sliders = []
        self.line_batch = None
        self.poly_batch = None
        self.value_text_width = 0
        # Runtime
        self.runtime_rebuild_pos_y = -1
        # Event
        self.show_tip = False
        self.show_opt_labels = False
        self.show_mini_sliders = False
        self.last_preview_index_called = -1


    def build(self, SD:SlideData):
        # For Run Time Rebuilds
        if self.runtime_rebuild_pos_y < 0:
            self.runtime_rebuild_pos_y = SD.build_y
        # Calc Build Locations
        self.slide_prop.ensure_limits()
        top_y = SD.build_y
        text_y = top_y - SD.pad - SD.text_h + SD.text_d
        label = self.slide_prop.label
        label_box_w = round(self.slide_prop.label_len * SD.char_w)
        label_box_lx = SD.area_w - SD.spad - label_box_w
        label_box_by = top_y - SD.box_h
        # Label
        self.label_map.text = self.slide_prop.label
        self.label_map.font_size = SD.font_s
        self.label_map.color = SD.prefs.font_secondary_color
        label_text_w = text_dims(label, SD.font_s)[0]
        x = SD.area_w - SD.spad - label_box_w + ((label_box_w - label_text_w) / 2)
        self.label_map.location = Vector((x, text_y))
        # Value Display
        self.value_text_width = round(SD.char_w * self.slide_prop.prop_len)
        self.value_map.text = self.slide_prop.label
        self.value_map.font_size = SD.font_s
        self.value_map.color = SD.prefs.font_primary_color
        x = label_box_lx - SD.char_w * self.slide_prop.prop_len
        self.value_map.location = Vector((x, text_y))
        # Bounds
        self.label_bounds.poly_color = SD.prefs.background_color
        self.label_bounds.line_color = SD.prefs.border_primary_color
        self.label_bounds.build(left_x=label_box_lx, bottom_y=label_box_by, w=label_box_w, h=SD.box_h, text_maps=[self.label_map, self.value_map])
        # Detection
        x = label_box_lx - SD.char_w * self.slide_prop.prop_len - SD.pad
        y = label_box_by - 2 * SD.factor
        w = label_box_w + self.value_text_width + SD.pad * 3
        h = SD.box_h + 4 * SD.factor
        self.detection_bounds.build(left_x=x, bottom_y=y, w=w, h=h)
        # Tip
        self.tip_map.text = self.slide_prop.label_tip
        self.tip_map.font_size = SD.font_s
        self.tip_map.color = SD.prefs.font_primary_color
        x = SD.area_w - SD.spad - text_dims(self.tip_map.text, SD.font_s)[0]
        self.tip_map.location = Vector((x, SD.slide_panel_tip_y))
        # Autos
        self.__set_display_text()
        self.__build_opt_labels(SD)
        self.__build_mini_sliders(SD)
        self.__build_gradients_batches(SD)
        # Offset
        SD.build_y -= SD.box_h + 4 * SD.factor


    def reset(self, SD:SlideData):
        if self.mini_sliders:
            for mini_slider in self.mini_sliders:
                mini_slider.reset(SD)
        if SD.locked_item == self:
            return
        self.show_tip = False
        self.show_opt_labels = False
        self.show_mini_sliders = False
        self.label_bounds.line_color = SD.prefs.border_secondary_color if self.slide_prop.is_attr_value_true() else SD.prefs.border_primary_color
        self.label_bounds.poly_color = SD.prefs.background_color


    def update(self, SD:SlideData):
        if SD.locked_item == self:
            self.__locked_update(SD)
            return
        # Mouse Within Panel Box
        if self.detection_bounds.point_within_bounds(SD.mouse):
            # Nudge mouse up 1 pixel if its at the bottom
            if SD.mouse.y == self.detection_bounds.bl.y:
                SD.mouse.y += 1
            # Show Tip
            if self.tip_map.text:
                self.show_tip = True
            # Already True and Mouse Over
            if self.label_bounds.line_color == SD.prefs.border_secondary_color:
                self.label_bounds.line_color = SD.prefs.border_tertiary_color
            else:
                self.label_bounds.line_color = SD.prefs.border_secondary_color
            self.label_bounds.poly_color = SD.prefs.background_highlight_color
            # Activate
            if SD.LMB_pressed:
                SD.ui_was_clicked = True
                # Alternative Routes
                if SD.event.shift and callable(self.slide_prop.panel_box_shift_callback):
                    self.slide_prop.panel_box_shift_callback(SD.context, SD.event, self.slide_prop)
                    self.__build_opt_labels(SD)
                    self.__set_display_text()
                    return
                elif SD.event.ctrl and callable(self.slide_prop.panel_box_ctrl_callback):
                    self.slide_prop.panel_box_ctrl_callback(SD.context, SD.event, self.slide_prop)
                    self.__build_opt_labels(SD)
                    self.__set_display_text()
                    return
                # Types
                attr = self.slide_prop.get_attr()
                # Boolean Toggle
                if type(attr) == bool:
                    value = not attr
                    self.slide_prop.set_attribute(value, SD)
                    self.slide_prop.invoke_callback(SD)
                    self.__set_display_text()
                # Option Boxes
                elif type(attr) in {tuple, list, str} and self.opt_labels:
                    SD.locked_item = self
                    self.show_opt_labels = True
                    if callable(self.slide_prop.preview_callback):
                        self.last_preview_index_called = -1
                        self.slide_prop.preview_callback(SD.context, SD.event, self.slide_prop, index=0, initialized=True)
                    self.__locked_update(SD)
                # Mini Sliders
                elif type(attr) in {int, float} and self.mini_sliders:
                    SD.locked_item = self
                    self.show_mini_sliders = True


    def __locked_update(self, SD:SlideData):
        self.show_tip = False
        # Option Labels
        if self.show_opt_labels:
            for opt_label in self.opt_labels:
                valid = opt_label.user_data['VALID']
                index = opt_label.user_data['INDEX']
                text_map = opt_label.text_maps[0] if len(opt_label.text_maps) > 0 else None
                opt_label.poly_color = SD.prefs.background_color
                # Already selected
                if self.slide_prop.index == index:
                    valid = False
                # Cannot be Selected
                if not valid:
                    if text_map:
                        text_map.color = SD.prefs.font_primary_color
                    # Mouse was in a different label, reset the preview
                    if opt_label.point_within_bounds(SD.mouse):
                        self.last_preview_index_called = -1
                    if index == self.slide_prop.index:
                        opt_label.line_color = SD.prefs.border_tertiary_color
                    else:
                        opt_label.line_color = SD.prefs.border_primary_color
                    continue
                # Check if Mouse Within || If Selected || Preview Callbacks
                elif opt_label.point_within_bounds(SD.mouse):
                    opt_label.line_color = SD.prefs.border_secondary_color
                    opt_label.poly_color = SD.prefs.background_highlight_color
                    if text_map:
                        text_map.color = SD.prefs.font_secondary_color
                    # Selected
                    if SD.LMB_released:
                        self.slide_prop.index = index
                        self.__set_display_text()
                        self.slide_prop.invoke_callback(SD)
                        self.last_preview_index_called = -1
                    # Preview Callback
                    elif self.last_preview_index_called != index and callable(self.slide_prop.preview_callback):
                        self.last_preview_index_called = index
                        self.slide_prop.preview_callback(SD.context, SD.event, self.slide_prop, index=index, initialized=False)
                # Selectable but not selected
                else:
                    opt_label.line_color = SD.prefs.border_primary_color
                    if text_map:
                        text_map.color = SD.prefs.font_secondary_color
        # Mini Sliders
        elif self.show_mini_sliders:
            for mini_slider in self.mini_sliders:
                mini_slider.update(SD)
            if SD.locked_mini_slider:
                self.__set_display_text()
        # Reset
        if SD.LMB_released:
            SD.locked_item = None
            SD.locked_mini_slider = None
            SD.ui_was_clicked = True
            self.reset(SD)


    def __set_display_text(self):
        text = limits_text(self.slide_prop, position='CENTER')
        text = fitted_text_to_width(text, max_w=self.value_text_width)
        self.value_map.text = text


    def __build_opt_labels(self, SD:SlideData):
        self.opt_labels = []
        attr = self.slide_prop.get_attr()
        if (type(attr) not in {tuple, list, str}) or (not attr):
            return
        # Convert to Proper Strings
        texts = [str(item).replace('_', ' ').title() for item in attr]
        if self.slide_prop.as_degrees:
            texts = [f"{text}º" for text in texts]
        if self.slide_prop.index_list_items:
            texts = [f"{index + 1} : {text}" for index, text in enumerate(texts)]
        # Padding : Vertical | Horizontal
        pix_pad = round(2 * SD.factor)
        MAX_ROWS = 10
        # [ (col_w, [index, text] ) ]
        columns = []
        column = []
        temp_text = []
        count = 0
        for index, text in enumerate(texts):
            count += 1
            temp_text.append(text)
            column.append((index, text))
            if (index == (len(texts) - 1)) or count == MAX_ROWS:
                label_w = max([text_dims(t, SD.font_s)[0] for t in temp_text])
                label_w += SD.pad * 2
                columns.append((label_w, column))
                column = []
                temp_text = []
                count = 0
        # Delta : Left X
        delta_lx = self.detection_bounds.bl.x - SD.pad
        # Build Labels
        for label_w, row in reversed(columns):
            # Delta : Left X | Top Y
            delta_lx -= label_w + pix_pad
            delta_ty = self.detection_bounds.tl.y
            for index, text in row:
                # Text Map
                text_map = TextMap()
                text_map.font_size = SD.font_s
                text_map.text = text
                # Text Map : Color
                text_map.color = SD.prefs.font_primary_color if attr[index] in self.slide_prop.invalid_list_opts else SD.prefs.font_secondary_color
                # Text Map : Position
                x = delta_lx + SD.pad
                y = delta_ty - SD.pad - SD.text_h + SD.text_d
                text_map.location = Vector((x, y))
                # Label Bounds
                label = Rect2D()
                label.user_data['INDEX'] = index
                label.user_data['VALID'] = attr[index] not in self.slide_prop.invalid_list_opts
                # Label Bounds : Color
                label.poly_color = SD.prefs.background_color
                label.line_color = SD.prefs.border_tertiary_color if index == self.slide_prop.index else SD.prefs.border_primary_color
                # Label Bounds : Build
                x = delta_lx
                y = delta_ty - SD.box_h
                label.build(left_x=x, bottom_y=y, w=label_w, h=SD.box_h, text_maps=[text_map])
                # Assign
                self.opt_labels.append(label)
                # Deltas
                delta_ty -= (SD.box_h + pix_pad)


    def __build_mini_sliders(self, SD:SlideData):
        attr = self.slide_prop.get_attr()
        if type(attr) not in {int, float}:
            return
        # Calcs
        rx = self.detection_bounds.bl.x - SD.pad * 6
        anchor_point = Vector((self.detection_bounds.bl.x, self.detection_bounds.center.y))
        # Plus
        cy = self.detection_bounds.center.y + SD.box_h
        plus_mini = MiniSlider(SD, self.slide_prop, add=True)
        plus_mini.build(SD, rx=rx, cy=cy, anchor_point=anchor_point)
        # Minus
        cy = self.detection_bounds.center.y - SD.box_h
        minus_mini = MiniSlider(SD, self.slide_prop, add=False)
        minus_mini.build(SD, rx=rx, cy=cy, anchor_point=anchor_point)
        # Append
        self.mini_sliders = [plus_mini, minus_mini]


    def __build_gradients_batches(self, SD:SlideData):
        color = SD.prefs.slider_negative_color
        color_1 = (color[0], color[1], color[2], color[3])
        color_2 = (color[0], color[1], color[2], 0.0)
        lx = self.detection_bounds.tl.x
        rx = self.detection_bounds.tr.x
        by = self.detection_bounds.bl.y
        ty = self.detection_bounds.tl.y
        p1 = (rx, ty) # TR color_1
        p2 = (lx, ty) # TL color_2
        p3 = (rx, by) # BR color_1
        p4 = (lx, by) # BL color_2
        self.line_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (p1, p2, p4, p3, p1), "color": (color_2, color_1, color_1, color_2, color_2)})
        self.poly_batch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {"pos": (p2, p4, p1, p3), "color": (color_1, color_1, color_2, color_2)}, indices=((0, 1, 2), (1, 2, 3)))


    def draw(self, SD:SlideData):
        state.blend_set('ALPHA')
        if self.poly_batch:
            self.poly_batch.draw(SMOOTH_COLOR)
        state.line_width_set(1)
        if self.line_batch:
            self.line_batch.draw(SMOOTH_COLOR)
        state.blend_set('NONE')
        self.label_bounds.draw()
        if self.show_tip:
            self.tip_map.draw()
        if self.show_opt_labels and self.opt_labels:
            for opt_label in self.opt_labels:
                opt_label.draw()
        elif self.show_mini_sliders and self.mini_sliders:
            for mini_slider in self.mini_sliders:
                mini_slider.draw(SD)


class SlideBarItem:
    def __init__(self, slide_prop=None):
        self.slide_prop = slide_prop
        self.label_map = TextMap()
        self.min_map = TextMap()
        self.max_map = TextMap()
        self.tip_label = Label2D()
        self.label_bounds = Rect2D()
        self.slider_map = TextMap()
        self.slider_bounds = Rect2D()
        self.detection_bounds = Rect2D()
        self.line_batches = []
        self.poly_batches = []
        self.runtime_rebuild_pos_y = -1
        # Event
        self.mouse_x = 0
        self.accumulated = 0
        self.show_tip = False
        self.last_value = None
        self.manual_entry_mode = False
        self.manual_entry_form = ManualEntryForm()
        self.mouse_dragged_in_locked_update = False


    def build(self, SD:SlideData):
        # For Run Time Rebuilds
        if self.runtime_rebuild_pos_y < 0:
            self.runtime_rebuild_pos_y = SD.build_y
        text_y = SD.build_y - SD.pad - SD.text_h + SD.text_d
        self.slide_prop.ensure_limits()
        attr = self.slide_prop.get_attr()
        if type(attr) in {int, float}:
            self.last_value = attr
        # Left Limit Text
        x_offset = text_dims("-100.000", SD.font_s)[0]
        self.min_map.text = limits_text(self.slide_prop, position='LEFT')
        self.min_map.color = SD.prefs.font_secondary_color if self.slide_prop.soft_min and type(attr) not in {list, tuple, str} else SD.prefs.font_tertiary_color
        self.min_map.location = Vector((SD.slider_lx - x_offset, text_y))
        x_offset += SD.pad * 2
        # Right Limit Text
        self.max_map.text = limits_text(self.slide_prop, position='RIGHT')
        self.max_map.color = SD.prefs.font_secondary_color if self.slide_prop.soft_max and type(attr) not in {list, tuple, str} else SD.prefs.font_tertiary_color
        self.max_map.location = Vector((SD.slider_rx + SD.pad, text_y))
        # Left Label Text
        label = self.slide_prop.label
        label_w = round(self.slide_prop.label_len * SD.char_w) + SD.pad * 2
        label_map_x = SD.slider_lx - label_w + round((label_w - text_dims(label, SD.font_s)[0]) / 2)
        label_map_x -= x_offset
        self.label_map.text = label
        self.label_map.font_size = SD.font_s
        self.label_map.color = SD.prefs.font_secondary_color if callable(self.slide_prop.label_callback) else SD.prefs.font_primary_color
        self.label_map.location = Vector((label_map_x, text_y))
        # Left Label Bounds
        label_bounds_x = SD.slider_lx - label_w - x_offset
        label_bounds_y = SD.build_y - SD.box_h
        label_bounds_h = SD.box_h
        self.label_bounds.poly_color = SD.prefs.background_color
        self.label_bounds.line_color = SD.prefs.border_primary_color
        self.label_bounds.build(left_x=label_bounds_x, bottom_y=label_bounds_y, w=label_w, h=label_bounds_h, text_maps=[self.label_map, self.min_map, self.max_map])
        # Slider Text
        slider_map_w = round(self.slide_prop.prop_len * SD.char_w) + SD.pad * 2
        slider_map_x = SD.area_center_x - round(slider_map_w / 2)
        self.slider_map.text = "0"
        self.slider_map.font_size = SD.font_s
        self.slider_map.color = SD.prefs.font_secondary_color
        self.slider_map.location = Vector((slider_map_x, text_y))
        # Slider Bounds
        slider_bounds_y = SD.build_y - SD.box_h
        slider_bounds_h = SD.box_h
        self.slider_bounds.poly_color = SD.prefs.background_color
        self.slider_bounds.line_color = SD.prefs.border_primary_color
        self.slider_bounds.build(left_x=slider_map_x, bottom_y=slider_bounds_y, w=slider_map_w, h=slider_bounds_h, text_maps=[self.slider_map])
        # Position
        self.__move_slider_to_attr(SD)
        # Over detection
        detection_bounds_x = self.label_bounds.bl.x - SD.pad
        detection_bounds_y = slider_bounds_y
        detection_bounds_w = SD.slider_rx - detection_bounds_x
        detection_bounds_h = SD.box_h
        self.detection_bounds.build(left_x=detection_bounds_x, bottom_y=detection_bounds_y, w=detection_bounds_w, h=detection_bounds_h)
        # Slider Gradients / Inner Text
        self.__build_gradients_batches(SD)
        self.__set_inner_text(SD)
        # Build Y -> Used to move the next row down
        SD.build_y -= detection_bounds_h
        # RX -> Used to build menu circle
        if self.max_map.location.x > SD.farthest_rx:
            SD.farthest_rx = self.max_map.location.x
        # LX -> Used to set tip location
        if detection_bounds_x < SD.farthest_lx:
            SD.farthest_lx = detection_bounds_x
        # Make the first and last slide bar's detection zone slightly larger in the Y
        if self.slide_prop in SD.slide_bar_props:
            max_index = len(SD.slide_bar_props) - 1
            index = SD.slide_bar_props.index(self.slide_prop)
            if index == 0:
                self.detection_bounds.tl.y += SD.pad * 2
                self.detection_bounds.tr.y += SD.pad * 2
            elif index == max_index:
                self.detection_bounds.bl.y -= SD.pad * 2
                self.detection_bounds.br.y -= SD.pad * 2


    def build_tips(self, SD:SlideData):
        if not self.slide_prop.label_tip:
            return
        tip = self.slide_prop.label_tip
        x = SD.slide_bar_tip_loc.x
        y = SD.slide_bar_tip_loc.y
        tips = []
        if type(tip) == str:
            tips.append((tip, ""))
        elif type(tip) in {list, tuple}:
            tips = tip
        self.tip_label.build_from_msgs(pos_x=x, pos_y=y, messages=tips, pos='TOP_LEFT')
                

    def reset(self, SD:SlideData):
        if SD.locked_item == self:
            return
        self.slider_bounds.line_color = SD.prefs.border_primary_color
        self.slider_bounds.poly_color = SD.prefs.background_color
        self.label_bounds.line_color = SD.prefs.border_primary_color
        self.accumulated = 0
        self.show_tip = False
        self.manual_entry_mode = False
        self.mouse_dragged_in_locked_update = False
        self.__external_data_update_handler(SD)


    def update(self, SD:SlideData):
        # Locked Update
        if SD.locked_item == self:
            self.__locked_update(SD)
            return
        # Label as Btn
        if callable(self.slide_prop.label_callback) and self.label_bounds.point_within_bounds(SD.mouse):
            self.label_bounds.line_color = SD.prefs.border_secondary_color
            SD.item_to_draw_ontop = self
            # Nudge mouse up 1 pixel if its at the bottom
            if SD.mouse.y == self.detection_bounds.bl.y:
                SD.mouse.y += 1
            if self.slide_prop.label_tip:
                self.show_tip = True
            if SD.LMB_pressed:
                SD.ui_was_clicked = True
                self.slide_prop.label_callback(SD.context, SD.event, self.slide_prop)
                self.__move_slider_to_attr(SD)
                self.__set_inner_text(SD)
                self.__build_gradients_batches(SD)
        # Locking Slider
        elif self.slider_bounds.point_within_bounds(SD.mouse) or self.detection_bounds.point_within_bounds(SD.mouse):
            self.slider_bounds.line_color = SD.prefs.border_secondary_color
            self.slider_bounds.poly_color = SD.prefs.background_highlight_color
            SD.item_to_draw_ontop = self
            # Nudge mouse up 1 pixel if its at the bottom
            if SD.mouse.y == self.detection_bounds.bl.y:
                SD.mouse.y += 1
            if SD.LMB_pressed:
                SD.locked_item = self
                self.mouse_x = SD.mouse.x


    def vertical_shift(self, SD:SlideData, y_offset):
        self.label_bounds.offset(y_offset=y_offset)
        self.slider_bounds.offset(y_offset=y_offset)
        self.detection_bounds.offset(y_offset=y_offset)
        self.tip_label.bounds.offset(y_offset=y_offset)
        self.__build_gradients_batches(SD)


    def __locked_update(self, SD:SlideData):
        if self.manual_entry_mode:
            self.__manual_entry(SD)
            return
        prop_type = self.slide_prop.prop_type
        context = SD.context
        event = SD.event
        SD.item_to_draw_ontop = self
        offset = SD.mouse.x - self.mouse_x
        # Locks ability to start manual entry mode
        if SD.mouse_dragging:
            self.mouse_dragged_in_locked_update = True
        # Manual Entry Form
        if self.mouse_dragged_in_locked_update == False and LMB_release(event):
            if prop_type in {int, float}:
                self.manual_entry_mode = True
                self.show_tip = False
                self.accumulated = 0
                attr = self.slide_prop.get_attr()
                min_val = None if self.slide_prop.soft_min else self.slide_prop.min_val
                max_val = None if self.slide_prop.soft_max else self.slide_prop.max_val
                label = self.slide_prop.label
                self.manual_entry_form.start(context, event, label=label, value=attr, value_type=prop_type, min_val=min_val, max_val=max_val, as_degrees=self.slide_prop.as_degrees)
                self.__manual_entry(SD)
                return
        if event.shift:
            offset *= .5
        elif event.ctrl:
            offset *= .25
        elif event.alt:
            offset *= 4

        clamped_ty, clamped_by, clamped_lx, clamped_rx = self.slider_bounds.offset(x_offset=offset, lx_limit=SD.slider_lx, rx_limit=SD.slider_rx)

        self.mouse_x = SD.mouse.x
        self.__build_gradients_batches(SD)
        if prop_type in {list, tuple, str}:
            width = SD.slider_w - self.slider_bounds.width
            delta = self.slider_bounds.tl.x - SD.slider_lx
            factor = delta / width
            attr = self.slide_prop.get_attr()
            value = round(lerp(0, len(attr) - 1, factor))
            self.slide_prop.index = value

        elif prop_type in {int, float}:
            slider_cx = self.slider_bounds.center.x
            slider_hw = self.slider_bounds.width / 2
            bar_lx = SD.slider_lx + slider_hw
            bar_rx = SD.slider_rx - slider_hw
            # Accumulate
            if (abs(offset) > 0) and (clamped_lx or clamped_rx):
                self.accumulated += offset

            # Soft (MIN / MAX) Increase Amount
            increment = self.slide_prop.increment

            # Soft Max Increase
            if self.accumulated > SD.accumulation_threshold and self.slide_prop.soft_max:
                self.slide_prop.max_val += increment
                self.max_map.text = limits_text(self.slide_prop, position='RIGHT')
            # Soft Min Decrease
            elif self.accumulated < -SD.accumulation_threshold and self.slide_prop.soft_min:
                self.slide_prop.min_val -= increment
                self.min_map.text = limits_text(self.slide_prop, position='LEFT')
            # Reset Accumulation
            if (abs(self.accumulated) > SD.accumulation_threshold):
                self.accumulated = 0

            # Set Value
            value = remap_value(self.slider_bounds.center.x, min_a=bar_lx, max_a=bar_rx, min_b=self.slide_prop.min_val, max_b=self.slide_prop.max_val)
            self.slide_prop.set_attribute(value, SD)
            self.last_value = value

        # Callback
        if abs(offset) > 0:
            self.slide_prop.invoke_callback(SD)
            self.__set_inner_text(SD)
        # Unlock
        if SD.LMB_released:
            SD.locked_item = None
            self.reset(SD)


    def __manual_entry(self, SD:SlideData):
        self.manual_entry_form.update(SD.context, SD.event)
        if self.manual_entry_form.status == UX_STATUS.INACTIVE:
            value = self.manual_entry_form.value
            if type(value) in {int, float}:
                # Soft Min
                if self.slide_prop.soft_min:
                    if value < self.slide_prop.min_val:
                        self.slide_prop.min_val = value
                        self.min_map.text = limits_text(self.slide_prop, position='LEFT')
                # Soft Max
                if self.slide_prop.soft_max:
                    if value > self.slide_prop.max_val:
                        self.slide_prop.max_val = value
                        self.max_map.text = limits_text(self.slide_prop, position='RIGHT')
                # Set Value
                self.last_value = value
                self.slide_prop.set_attribute(value, SD)
                self.slide_prop.invoke_callback(SD)
                self.__move_slider_to_attr(SD)
                self.__set_inner_text(SD)
                self.__build_gradients_batches(SD)
            SD.locked_item = None
            self.reset(SD)


    def __move_slider_to_attr(self, SD:SlideData):
        x_offset = 0
        attr = self.slide_prop.get_attr()
        value = attr
        min_value = self.slide_prop.min_val
        max_value = self.slide_prop.max_val
        if type(attr) in {list, tuple, str}:
            value = self.slide_prop.index
            min_value = 0
            max_value = len(attr) - 1
        elif type(attr) == bool:
            value = self.slide_prop.index
            min_value = 0
            max_value = 1
        sw_h = round(self.slider_bounds.width / 2)
        min_b = SD.slider_lx + sw_h
        max_b = SD.slider_rx - sw_h
        position = remap_value(value, min_a=min_value, max_a=max_value, min_b=min_b, max_b=max_b)
        offset = position - self.slider_bounds.center.x
        self.slider_bounds.offset(x_offset=offset, lx_limit=SD.slider_lx, rx_limit=SD.slider_rx)


    def __set_inner_text(self, SD:SlideData):
        text = limits_text(self.slide_prop, position='CENTER')
        text_w = text_dims(text, SD.font_s)[0]
        half = round((self.slider_bounds.width - text_w) / 2)
        x = self.slider_bounds.bl.x + half
        self.slider_map.location.x = x
        self.slider_map.text = text


    def __build_gradients_batches(self, SD:SlideData):
        self.line_batches.clear()
        self.poly_batches.clear()
        slide_ty = self.slider_bounds.tl.y
        slide_by = self.slider_bounds.bl.y
        color = SD.prefs.slider_negative_color
        color_1 = (color[0], color[1], color[2], color[3])
        color_2 = (color[0], color[1], color[2], 0.0)
        width_offset = round(SD.text_h * .625)
        rx = self.slider_bounds.tl.x
        p1 = (rx, slide_ty - width_offset) # TR
        p2 = (SD.slider_lx, slide_ty - width_offset) # TL
        line_batch_1 = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (p1, p2), "color": (color_1, color_2)})
        self.line_batches.append(line_batch_1)
        p3 = (rx, slide_by + width_offset) # BR
        p4 = (SD.slider_lx, slide_by + width_offset) # BL
        line_batch_2 = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (p3, p4), "color": (color_1, color_2)})
        self.line_batches.append(line_batch_2)
        poly_batch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {"pos": (p2, p4, p1, p3), "color": (color_2, color_2, color_1, color_1)}, indices=((0, 1, 2), (1, 2, 3)))
        self.poly_batches.append(poly_batch)
        color = SD.prefs.slider_positive_color
        color_1 = (color[0], color[1], color[2], color[3])
        color_2 = (color[0], color[1], color[2], 0.0)
        lx = self.slider_bounds.tr.x
        p1 = (lx, slide_ty - width_offset) # TR
        p2 = (SD.slider_rx, slide_ty - width_offset) # TL
        line_batch_1 = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (p1, p2), "color": (color_1, color_2)})
        self.line_batches.append(line_batch_1)
        p3 = (lx, slide_by + width_offset) # BR
        p4 = (SD.slider_rx, slide_by + width_offset) # BL
        line_batch_2 = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (p3, p4), "color": (color_1, color_2)})
        self.line_batches.append(line_batch_2)
        poly_batch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {"pos": (p2, p4, p1, p3), "color": (color_2, color_2, color_1, color_1)}, indices=((0, 1, 2), (1, 2, 3)))
        self.poly_batches.append(poly_batch)


    def __external_data_update_handler(self, SD:SlideData):
        attr = self.slide_prop.get_attr()
        if type(attr) in {int, float}:
            if attr != self.last_value:
                self.last_value = attr
                self.slide_prop.ensure_limits()
                self.__move_slider_to_attr(SD)
                self.__set_inner_text(SD)
                self.min_map.text = limits_text(self.slide_prop, position='LEFT')
                self.max_map.text = limits_text(self.slide_prop, position='RIGHT')
                self.__build_gradients_batches(SD)


    def draw(self, SD:SlideData):
        state.blend_set('ALPHA')
        for poly_batch in self.poly_batches:
            poly_batch.draw(SMOOTH_COLOR)
        state.line_width_set(1)
        for line_batch in self.line_batches:
            line_batch.draw(SMOOTH_COLOR)
        state.blend_set('NONE')
        self.label_map.draw()
        self.label_bounds.draw()
        self.slider_bounds.draw()
        if self.show_tip:
            self.tip_label.draw()
        if self.manual_entry_mode:
            self.manual_entry_form.draw()


class SlideProp:
    '''
    PAR
        • as_slide : (Bool)
            → True  -> Builds a central top bar slider
            → False -> Creates a side panel control
        • label : (String)
            → The label string to display
        • label_len : (Int)
            → How wide to calculate the label box to be
        • label_callback : (Function)
            → The function to call when the label is pressed (Only for central top bar) (Side bar uses only the callback)
        • label_tip : (String | Tuple)
            → The string to display when mouse is hovering over label
            → If Tuple, It will split it up
        • instance : (Object)
            → The class object that the prop exist within top level
        • prop_type : (Object)
            → Used to track the starting type that it was intended to be used as (since float might be considered integers after rounding)
        • prop_name : (String)
            → The name of the property on the instance object
        • prop_len : (Int)
            → How wide to calculate the label box to be
        • increment : (Int | Float)
            → The amount to increase or decrease the property value by when the prop_type is (Int or Float)
        • min_val : (Int | Float)
            → The minimum value the user can adjust the property to
        • soft_min : (Bool)
            → Whether or not the user may decrease the value below the set min_val
        • max_val : (Int | Float)
            → The maximum value the user can adjust the property to
        • soft_max : (Bool)
            → Whether or not the user may increase the value above the set max_val
        • as_degrees : (Bool)
            → Convert values to degrees, appends the degrees symbol
        • index_list_items : (Bool)
            → Index the SidePanel PopUp items
        • index : (Int)
            → For List, Tuple, String -> The position to start the slider or active item at
        • invalid_list_opts : (List)
            → For side menu when item is in (List, Tuple, String), grey out boxes when submenu appears
        • preview_callback
            → Required Function Params (context, event, slide_prop:SlideProp, index:int, initialized:bool)
            → index = Label that the mouse just entered
            → initialized = When the submenu is just opened
        • callback
            → Required Function Params (context, event, slide_prop:SlideProp)
            → The callback to invoke when a property is set
        • panel_box_shift_callback
            → Required Function Params (context, event, slide_prop:SlideProp)
            → Alternative Callback function for Slide Panel Box
        • panel_box_ctrl_callback
            → Required Function Params (context, event, slide_prop:SlideProp)
            → Alternative Callback function for Slide Panel Box
    '''
    def __init__(self,
            as_slider=True,
            label="", label_len=0, label_callback=None, label_tip="",
            instance=None, prop_type=None, prop_name='', prop_len=0,
            increment=0.25, min_val=-1, soft_min=False, max_val=1, soft_max=False,
            as_degrees=False, index_list_items=False,
            index=0, invalid_list_opts=[], preview_callback=None,
            callback=None,
            panel_box_shift_callback=None, panel_box_ctrl_callback=None):

        # User Data
        self.as_slider = as_slider
        self.label = label
        self.label_len = label_len
        self.label_callback = label_callback
        self.label_tip = label_tip
        self.instance = instance
        self.prop_type = prop_type
        self.prop_name = prop_name
        self.prop_len = prop_len
        self.increment = ceil(abs(increment)) if self.prop_type == int else float(abs(increment))
        self.min_val = min_val
        self.soft_min = soft_min
        self.max_val = max_val
        self.soft_max = soft_max
        self.as_degrees = as_degrees
        self.index_list_items = index_list_items
        self.index = index
        self.invalid_list_opts = invalid_list_opts
        self.preview_callback = preview_callback
        self.callback = callback
        self.panel_box_shift_callback = panel_box_shift_callback
        self.panel_box_ctrl_callback = panel_box_ctrl_callback
        # Internal Data
        self.controller = None
        self.min_val_copy = min_val
        self.max_val_copy = max_val


    def get_attr(self):
        if self.instance and self.prop_name:
            if hasattr(self.instance, self.prop_name):
                return getattr(self.instance, self.prop_name)
        return None


    def set_attribute(self, value, SD:SlideData):
        if self.instance and self.prop_name:
            if hasattr(self.instance, self.prop_name):
                if self.prop_type == int:
                    value = int(value)
                elif self.prop_type == float:
                    value = float(value)
                elif self.prop_type == str:
                    value = str(value)
                elif self.prop_type == bool:
                    value = bool(value)
                setattr(self.instance, self.prop_name, value)


    def invoke_callback(self, SD:SlideData):
        if callable(self.callback):
            self.callback(SD.context, SD.event, self)


    def ensure_limits(self):
        attr = self.get_attr()
        if type(attr) in {int, float}:
            if attr < self.min_val:
                if self.soft_min:
                    self.min_val = attr
                else:
                    attr = self.min_val
            elif attr > self.max_val:
                if self.soft_max:
                    self.max_val = attr
                else:
                    attr = self.max_val
        elif type(attr) in {tuple, list, str}:
            max_index = len(attr) - 1
            if self.index > max_index:
                self.index = max_index
            elif self.index < 0:
                self.index = 0


    def is_attr_value_true(self):
        attr = self.get_attr()
        if attr and type(attr) == bool:
            return True
        return False


    def build(self, SD:SlideData):
        if self.as_slider:
            self.controller = SlideBarItem(slide_prop=self)
        else:
            self.controller = SlidePanelItem(slide_prop=self)
        self.controller.build(SD)
    

    def build_tips(self, SD:SlideData):
        if isinstance(self.controller, SlideBarItem):
            self.controller.build_tips(SD)


    def reset(self, SD:SlideData):
        if self.controller:
            self.controller.reset(SD)


    def update(self, SD:SlideData):
        if self.controller:
            self.controller.update(SD)


    def vertical_shift(self, SD:SlideData, y_offset):
        if type(self.controller) == SlideBarItem:
            self.controller.vertical_shift(SD, y_offset=y_offset)


    def draw(self, SD:SlideData):
        if self.controller:
            self.controller.draw(SD)


class SlideMenu:
    def __init__(self, context, event, slide_props=[]):
        self.status = UX_STATUS.INACTIVE
        slide_props = [slide_prop for slide_prop in slide_props if type(slide_prop) == SlideProp]
        slide_bar_props = [slide_prop for slide_prop in slide_props if slide_prop.as_slider]
        slide_panel_props = [slide_prop for slide_prop in slide_props if not slide_prop.as_slider]
        self.SD = SlideData(context, event, slide_props=slide_props, slide_bar_props=slide_bar_props, slide_panel_props=slide_panel_props)
        self.dot_poly_batch = None
        self.dot_line_batch = None
        self.dot_poly_color = self.SD.prefs.background_color
        self.dot_line_color = self.SD.prefs.border_secondary_color
        self.dot_center = Vector((0,0))
        self.dot_radius = 12 * self.SD.factor
        # Event
        self.dot_exist = False
        self.dot_moving = False
        # Build
        self.build(context)


    def close(self, context):
        set_manual_input_timer(context, register=False)
        reset_mouse_drag()


    def build(self, context):
        SD = self.SD
        slide_props = SD.slide_props
        slide_bar_props = SD.slide_bar_props
        slide_panel_props = SD.slide_panel_props
        if slide_bar_props:
            # Build Sliders
            for slide_prop in slide_bar_props:
                slide_prop.build(SD)
            # Build Tips
            x = SD.farthest_lx
            y = SD.build_y - SD.text_h - SD.pad * 2
            SD.slide_bar_tip_loc = Vector((x, y))
            for slide_prop in slide_bar_props:
                slide_prop.build_tips(SD)
            # Set the bottom Y : Used for the Manual Input
            if len(slide_bar_props) > 0:
                slide_prop = slide_bar_props[-1]
                SD.slide_bar_lowest_y = slide_prop.controller.detection_bounds.bl.y
            # Build Menu Dot
            self.__build_dot()
        if slide_panel_props:
            pane_h = (SD.box_h + 4 * SD.factor) * len(slide_panel_props)
            SD.build_y = SD.area_h - (SD.area_h - pane_h) / 2
            SD.slide_panel_tip_y = SD.build_y - pane_h - SD.text_h
            for slide_prop in slide_panel_props:
                slide_prop.build(SD)
        for slide_prop in slide_props:
            slide_prop.reset(SD)


    def update(self, context, event):

        SD = self.SD
        SD.item_to_draw_ontop = None
        SD.update(context, event)

        # Moving
        if self.dot_moving:
            self.__offset_menu()
            self.status = UX_STATUS.ACTIVE
            return

        slide_props = SD.slide_props

        # Reset
        for slide_prop in slide_props:
            slide_prop.reset(SD)

        # Locked Item
        if SD.locked_item:
            SD.locked_item.update(SD)
            self.status = UX_STATUS.ACTIVE
            return

        # Event Finder
        for slide_prop in slide_props:
            slide_prop.update(SD)
            if SD.locked_item:
                self.status = UX_STATUS.ACTIVE
                return

        # Prevent Modal Exit
        if SD.ui_was_clicked:
            SD.ui_was_clicked = False
            self.status = UX_STATUS.ACTIVE
            return
        
        # Check Dot Move
        if self.dot_exist:
            if (SD.mouse - self.dot_center).length <= self.dot_radius + SD.pad:
                self.dot_poly_color = SD.prefs.background_highlight_color
                if SD.LMB_pressed:
                    self.dot_moving = True
                    self.status = UX_STATUS.ACTIVE
                    return
            else:
                self.dot_poly_color = SD.prefs.background_color
                self.dot_moving = False

        # Nothing
        self.status = UX_STATUS.INACTIVE


    def get_slide_prop_by_label(self, label=""):
        slide_props = self.SD.slide_props
        for slide_prop in slide_props:
            if slide_prop.label == label:
                return slide_prop
        return None


    def rebuild_slide_prop(self, slide_prop):
        '''
        IFO : Rebuilds the slide prop in place
        IFO : Cannot be a locked item
        '''

        if not isinstance(slide_prop, SlideProp):
            return
        if slide_prop == self.SD.locked_item:
            return

        SD = self.SD
        slide_bar_props = SD.slide_bar_props
        slide_panel_props = SD.slide_panel_props

        if slide_prop in slide_bar_props:
            SD.build_y = slide_prop.controller.runtime_rebuild_pos_y
            slide_prop.controller.build(SD)

        elif slide_prop in slide_panel_props:
            SD.build_y = slide_prop.controller.runtime_rebuild_pos_y
            slide_prop.controller.build(SD)
        else:
            return

        slide_prop.reset(SD)


    def __offset_menu(self):
        SD = self.SD
        start_y = self.dot_center.y

        offset = round(SD.area_h - SD.mouse.y)
        min_offset = round(SD.area_h - SD.spad - SD.box_h - SD.pad - (SD.box_h * len(SD.slide_bar_props)))
        if offset > min_offset:
            offset = min_offset

        SD.prefs.slide_menu_padding = offset
        SD.smpad = SD.prefs.slide_menu_padding
        self.__build_dot()
        slide_bar_props = SD.slide_bar_props
        y_offset = self.dot_center.y - start_y
        for slide_prop in slide_bar_props:
            slide_prop.vertical_shift(SD, y_offset)
        # Set the bottom Y : Used for the Manual Input
        if len(slide_bar_props) > 0:
            slide_prop = slide_bar_props[-1]
            SD.slide_bar_lowest_y = slide_prop.controller.detection_bounds.bl.y
        if SD.LMB_released:
            self.dot_moving = False


    def __build_dot(self):
        SD = self.SD
        self.dot_exist = True
        x = SD.farthest_lx - self.dot_radius * 4
        y = SD.area_h - SD.smpad - self.dot_radius
        self.dot_center = Vector((x, y))
        res = 32
        step = (pi * 2) / res
        points = [ Vector((cos(step * i), sin(step * i))) * self.dot_radius + self.dot_center for i in range(res + 1)]
        indices = [(0, i, i+1) for i in range(res - 1)]
        self.dot_poly_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=indices)
        self.dot_line_batch = batch_for_shader(UNIFORM_COLOR, 'LINE_STRIP', {"pos": points})


    def draw(self):
        if self.dot_exist and self.dot_poly_batch and self.dot_line_batch:
            state.blend_set('ALPHA')
            UNIFORM_COLOR.uniform_float("color", self.dot_poly_color)
            self.dot_poly_batch.draw(UNIFORM_COLOR)
            state.line_width_set(1)
            UNIFORM_COLOR.uniform_float("color", self.dot_line_color)
            self.dot_line_batch.draw(UNIFORM_COLOR)
            state.blend_set('NONE')

        SD = self.SD
        slide_props = SD.slide_props
        for slide_prop in slide_props:
            if slide_prop.controller == SD.item_to_draw_ontop:
                continue
            slide_prop.draw(SD)

        if isinstance(SD.item_to_draw_ontop, SlideBarItem):
            SD.item_to_draw_ontop.draw(SD)
