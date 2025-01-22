########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import time
import math
import bmesh
import gc
from mathutils import Vector, Matrix
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set

########################•########################
"""                  SETTINGS                 """
########################•########################

TEST_NUM = 0
UPDATE_ONLY_ON_PRESS = False
PRINT_FPS = False
DRAW_START_POS = True

########################•########################
"""                  OPERATOR                 """
########################•########################

class PS_OT_ModalTesting(bpy.types.Operator):
    bl_idname      = "ps.modal_testing"
    bl_label       = "Modal Testing"
    bl_description = "Modal Testing"
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return poll_test(context)

    def invoke(self, context, event):
        # Clear Handles
        utils.context.object_mode_toggle_reset()
        utils.event.reset_mouse_drag()
        utils.notifications.remove_notify_handle()
        utils.poly_fade.remove_poly_fade_handle()
        utils.vec_fade.remove_vec_fade_handle()
        utils.debug.remove_debug_handle()
        # Event
        self.modal_status = MODAL_STATUS.RUNNING
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.start_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.mouse_offseet = 0
        # Test
        invoke_test(self, context, event)
        if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
            return {'CANCELLED'}
        # Panels
        utils.modal_labels.info_panel_init(context, messages=[("LMB", "Finish"), ("RMB", "Cancel"),])
        utils.modal_labels.status_panel_init(context, messages=[("Ops", "Testing Mode")])
        # Screen
        utils.context.hide_3d_panels(context)
        self.screen_factor = utils.screen.screen_factor()
        # Shaders
        call_args = (self.draw_post_view, (context,), self, 'modal_status', MODAL_STATUS.ERROR)
        self.handle_post_view  = bpy.types.SpaceView3D.draw_handler_add(except_guard_prop_set, call_args, 'WINDOW', 'POST_VIEW')
        call_args = (self.draw_post_pixel, (context,), self, 'modal_status', MODAL_STATUS.ERROR)
        self.handle_post_pixel = bpy.types.SpaceView3D.draw_handler_add(except_guard_prop_set, call_args, 'WINDOW', 'POST_PIXEL')
        # Modal
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        except_guard_prop_set(self.update, (context, event), self, 'modal_status', MODAL_STATUS.ERROR)
        # Catch Error / Cancelled
        if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
            self.exit_modal(context)
            return {'CANCELLED'}
        # Finished
        if self.modal_status == MODAL_STATUS.CONFIRM:
            self.exit_modal(context)
            return {'FINISHED'}
        # View Movement
        if self.modal_status == MODAL_STATUS.PASS:
            return {'PASS_THROUGH'}
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def update(self, context, event):
        self.modal_status = MODAL_STATUS.RUNNING
        # View Movement
        if utils.event.pass_through(event, with_scoll=True, with_numpad=True, with_shading=True):
            self.modal_status = MODAL_STATUS.PASS
        # Finished
        elif utils.event.confirmed(event):
            self.modal_status = MODAL_STATUS.CONFIRM
        # Cancelled
        elif utils.event.cancelled(event, value='PRESS'):
            self.modal_status = MODAL_STATUS.CANCEL
        # Test
        elif not UPDATE_ONLY_ON_PRESS or event.value == 'PRESS':
            self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            self.mouse_offseet = (self.start_pos - self.mouse).length
            start = time.time()
            update_test(self, context, event)
            print_fps(start, time.time())

    def exit_modal(self, context):
        def shut_down():
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_post_view , "WINDOW")
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_post_pixel, "WINDOW")
            self.handle_post_view, self.handle_post_pixel = None, None
            utils.context.restore_3d_panels(context)
            exit_test(self, context)
            context.area.tag_redraw()
        utils.guards.except_guard(try_func=shut_down, try_args=None)

    def draw_post_view(self, context):
        draw_3d_test(self, context)

    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        draw_2d_test(self, context)
        if DRAW_START_POS:
            utils.graphics.draw_dot_2d(radius=10, res=18, line_width=1, poly_color=(0,0,1,.75), border_color=(0,0,1,1), center=self.start_pos)

def poll_test(context):
    global_data = globals()
    name = f'test_poll_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            return func(context)

def invoke_test(self, context, event):
    global_data = globals()
    name = f'test_setup_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            func(self, context, event)

def update_test(self, context, event):
    global_data = globals()
    name = f'test_update_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            func(self, context, event)

def exit_test(self, context):
    global_data = globals()
    name = f'test_exit_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            func(self, context)

def draw_2d_test(self, context):
    global_data = globals()
    name = f'test_draw_2d_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            func(self, context)

def draw_3d_test(self, context):
    global_data = globals()
    name = f'test_draw_3d_{TEST_NUM}'
    if name in global_data:
        func = global_data[name]
        if callable(func):
            func(self, context)

########################•########################
"""                  TEMPLATE                 """
########################•########################

def test_poll_0(context):
    return True

def test_setup_0(self, context, event):
    return

def test_update_0(self, context, event):
    return

def test_exit_0(self, context):
    return

def test_draw_2d_0(self, context):
    return

def test_draw_3d_0(self, context):
    return

########################•########################
"""                   TEST                    """
########################•########################

'''
[TEST 1]
    Modally adjust a mesh with a bmesh
'''

class Controller:
    def __init__(self, obj):
        self.obj = obj
        self.obj.update_from_editmode()
        self.mesh = self.obj.data
        self.backup = self.mesh.copy()
        self.bm = bmesh.from_edit_mesh(self.mesh)

    def restore(self):
        bmesh.ops.delete(self.bm, geom=self.bm.verts, context='VERTS')
        self.bm.from_mesh(self.backup)

    def update(self):
        bmesh.update_edit_mesh(self.mesh)

    def close(self):
        self.bm.free()
        self.bm = None
        if self.backup.name in bpy.data.meshes:
            bpy.data.meshes.remove(self.backup) 

def test_poll_1(context):
    return context.mode == 'EDIT_MESH'

def test_setup_1(self, context, event):
    self.controller = Controller(obj=context.edit_object)

def test_update_1(self, context, event):
    self.controller.restore()

    bm = self.controller.bm
    bmesh.ops.bevel(
        bm,
        geom=[e for e in bm.edges if e.select],
        offset=self.mouse_offseet * 0.01,
        offset_type='OFFSET',
        profile_type='SUPERELLIPSE',
        segments=2,
        profile=1,
        affect='EDGES',
        clamp_overlap=False,
        material=0,
        loop_slide=True,
        mark_seam=False,
        mark_sharp=False,
        harden_normals=False,
        face_strength_mode='NONE',
        miter_outer='SHARP',
        miter_inner='SHARP',
        spread=0,
        vmesh_method='ADJ')

    self.controller.update()
    
def test_exit_1(self, context):
    self.controller.close()
    self.controller = None
    del self.controller
    gc.collect()

########################•########################
"""                   UTILS                   """
########################•########################

def key_pressed(event, key='A'):
    if event.type == key and event.value == 'PRESS':
        return True
    return False

def print_fps(start, finish):
    if PRINT_FPS:
        frame_time = finish - start
        fps = str(round(1 / frame_time, 6)) if frame_time > 0 else "INF"
        print(f"FPS : {fps:<16}FRAME_TIME : {round(frame_time,6):<10}")

