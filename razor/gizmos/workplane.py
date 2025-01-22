########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
from bpy.types import Gizmo, GizmoGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from gpu_extras.batch import batch_for_shader
from bpy.props import BoolProperty, IntProperty, StringProperty, EnumProperty, FloatProperty
from bpy_extras.view3d_utils import region_2d_to_origin_3d
from ..props.workplane import PS_PROPS_Razor_Workplane
from ...resources.shapes import workplane as workplane_shapes
from ... import utils

########################•########################
"""                 CONSTANTS                 """
########################•########################

BTN_OFFSET_Y = 0.54
BTN_SPACING_X = 0.1

########################•########################
"""                  SHADERS                  """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')
POST_PIXEL_HANDLE = None

def unregister_pixel_shader():
    global POST_PIXEL_HANDLE
    if POST_PIXEL_HANDLE:
        bpy.types.SpaceView3D.draw_handler_remove(POST_PIXEL_HANDLE, "WINDOW")
    POST_PIXEL_HANDLE = None


def register_pixel_shader(callback=None, call_args=tuple()):
    global POST_PIXEL_HANDLE
    except_guard_callback = utils.guards.except_guard_callback
    call_args = (callback, call_args, unregister_pixel_shader)
    POST_PIXEL_HANDLE = bpy.types.SpaceView3D.draw_handler_add(except_guard_callback, call_args, 'WINDOW', 'POST_PIXEL')

########################•########################
"""                   UTILS                   """
########################•########################

GIZMO_GROUP_INSTANCE = None

def refresh_workplane_gizmo_group(context):
    global GIZMO_GROUP_INSTANCE
    if isinstance(GIZMO_GROUP_INSTANCE, PS_GGT_Razor_Workplane):
        GIZMO_GROUP_INSTANCE.refresh(context)
    context.area.tag_redraw()


def should_omit_gizmo_for_bad_view_angle(self, context):
    transform = self.workplane.transform
    location_ws = transform.location

    hw = context.area.width / 2
    hh = context.area.height / 2
    prj = context.region_data.perspective_matrix @ location_ws.to_4d()
    if prj.w <= 0.0:
        return False
    location_ss = Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w)))
    ray_org = region_2d_to_origin_3d(context.region, context.region_data, location_ss)
    ray_normal = (ray_org - location_ws).normalized()

    dot = ray_normal.dot(transform.get_normal())
    if abs(round(dot, 3)) < 0.05:
        if type(self) in {PS_GT_Razor_Workplane_LOC_X, PS_GT_Razor_Workplane_LOC_Y, PS_GT_Razor_Workplane_LOC_XY, PS_GT_Razor_Workplane_ROT_Z, PS_GT_Razor_Workplane_SCALE, PS_GT_Razor_Workplane_RES}:
            return True
    elif 1 - abs(round(dot, 3)) < 0.05:
        if type(self) in {PS_GT_Razor_Workplane_LOC_Z,}:
            return True
    dot = ray_normal.dot(transform.get_x_tangent())
    if abs(round(dot, 3)) < 0.05:
        if type(self) in {PS_GT_Razor_Workplane_ROT_X,}:
            return True
    dot = ray_normal.dot(transform.get_y_tangent())
    if abs(round(dot, 3)) < 0.05:
        if type(self) in {PS_GT_Razor_Workplane_ROT_Y,}:
            return True
    return False


def get_gizmo_color_from_type(self):
    if isinstance(self, (PS_GT_Razor_Workplane_LOC_X, PS_GT_Razor_Workplane_ROT_X)):
        return (1,0,0,1)
    if isinstance(self, (PS_GT_Razor_Workplane_LOC_Y, PS_GT_Razor_Workplane_ROT_Y)):
        return (0,1,0,1)
    if isinstance(self, (PS_GT_Razor_Workplane_LOC_Z, PS_GT_Razor_Workplane_ROT_Z)):
        return (0,0,1,1)
    if isinstance(self, PS_GT_Razor_Workplane_LOC_XY):
        return (1,1,0,1)
    if isinstance(self, PS_GT_Razor_Workplane_SCALE):
        return (1,0,1,1)
    if isinstance(self, PS_GT_Razor_Workplane_RES):
        return (0,1,1,1)
    return (1,1,1,1)

########################•########################
"""                  GIZMOS                   """
########################•########################

class PS_Gizmo(Gizmo):

    # --- AUTO INIT --- #

    def setup(self):
        # PS : DATA
        self.workplane = None
        self.workplanes = []
        self.gizmo_axis = 'X'
        self.border_batch = None
        self.button_batch = None
        self.label_a_batch = None
        self.label_b_batch = None
        self.gizmo_batch = None
        self.gizmo_color = get_gizmo_color_from_type(self)
        # PS : EVENT
        self.ghost_batch = None
        self.adjusting_all = False
        # B3D
        self.use_select_background = False
        self.use_event_handle_all = False
        self.use_grab_cursor = False
        self.use_draw_modal = True
        self.hide_keymap = False
        self.hide_select = False
        self.hide = False

    # --- INIT --- #

    def setup_widgets(self, workplane):
        if not isinstance(workplane, PS_PROPS_Razor_Workplane): return
        self.workplane = workplane

        if isinstance(self, PS_GT_Razor_Workplane_Grid):
            offset = Vector((-0.5, BTN_OFFSET_Y, 0))
            coords = workplane_shapes.wp_border.coords
            self.border_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})
            coords = workplane_shapes.wp_circle_btn.coords
            self.button_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [offset + co for co in coords]})
            coords = workplane_shapes.wp_set_label.coords
            self.label_a_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [offset + co for co in coords]})
            coords = workplane_shapes.wp_edit_label.coords
            self.label_b_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [offset + co for co in coords]})

        elif isinstance(self, PS_GT_Razor_Workplane_Sketch):
            offset = Vector((-0.5 + BTN_SPACING_X, BTN_OFFSET_Y, 0))
            coords = workplane_shapes.wp_circle_btn.coords
            self.button_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [offset + co for co in coords]})
            coords = workplane_shapes.wp_sketch.coords
            self.label_a_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [offset + co for co in coords]})

        elif isinstance(self, PS_GT_Razor_Workplane_LOC_X):
            self.gizmo_axis = 'X'
            coords = workplane_shapes.loc_x.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_LOC_Y):
            self.gizmo_axis = 'Y'
            coords = workplane_shapes.loc_y.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_LOC_Z):
            self.gizmo_axis = 'Z'
            coords = workplane_shapes.loc_z.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_LOC_XY):
            self.gizmo_axis = 'XY'
            coords = workplane_shapes.loc_xy.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_ROT_X):
            self.gizmo_axis = 'X'
            coords = workplane_shapes.rot_x.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_ROT_Y):
            self.gizmo_axis = 'Y'
            coords = workplane_shapes.rot_y.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_ROT_Z):
            self.gizmo_axis = 'Z'
            coords = workplane_shapes.rot_z.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_SCALE):
            coords = workplane_shapes.scale.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

        elif isinstance(self, PS_GT_Razor_Workplane_RES):
            coords = workplane_shapes.res.coords
            self.gizmo_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})

    # --- MODAL UTILS --- #

    def modal_labels_controller(self, context, register_callback=False, unregister_callback=False, help_msgs=None, status_msgs=None):
        if help_msgs is not None:
            utils.modal_labels.info_panel_init(context, messages=help_msgs)
        if status_msgs is not None:
            utils.modal_labels.status_panel_init(context, messages=status_msgs)
        if register_callback:
            register_pixel_shader(callback=self.draw_2d, call_args=tuple())
        if unregister_callback:
            unregister_pixel_shader()
        context.area.tag_redraw()


    def modal_generic_invoke(self, context):
        self.workplanes = []
        if self.hide or self.workplane.hide:
            return False
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane):
            return False
        razor = context.scene.razor
        for workplane in razor.workplanes:
            if not workplane.hide:
                self.workplanes.append(workplane)
                workplane.set_backup_data()
                workplane.reset_ops_data()
        if self.workplanes:
            return True
        return False


    def modal_generic_exit(self, context, cancel=False):
        self.modal_labels_controller(context, unregister_callback=True)
        if cancel and self.workplanes:
            for workplane in self.workplanes:
                workplane.restore_from_backup_data()
        context.area.tag_redraw()

    # --- GIZMO SELECT DRAW --- #

    def draw_select(self, context, select_id):
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane): return
        if context.scene.razor.ops.active: return
        # BUTTONS
        elif type(self) in {PS_GT_Razor_Workplane_Grid, PS_GT_Razor_Workplane_Sketch}:
            if not isinstance(self.button_batch, gpu.types.GPUBatch): return
            self.button_batch.program_set(UNIFORM_COLOR)
            gpu.select.load_id(select_id)
            with gpu.matrix.push_pop():
                gpu.matrix.multiply_matrix(self.matrix_basis)
                self.button_batch.draw(UNIFORM_COLOR)
        # GIZMOS
        else:
            if not isinstance(self.gizmo_batch, gpu.types.GPUBatch): return
            razor = bpy.context.scene.razor
            if self.workplane.uuid == razor.active_workplane:
                if should_omit_gizmo_for_bad_view_angle(self, context): return
                self.gizmo_batch.program_set(UNIFORM_COLOR)
                gpu.select.load_id(select_id)
                with gpu.matrix.push_pop():
                    gpu.matrix.multiply_matrix(self.matrix_basis)
                    self.gizmo_batch.draw(UNIFORM_COLOR)

    # --- GIZMO DRAW --- #

    def draw_buttons(self):
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane): return
        if not isinstance(self.button_batch, gpu.types.GPUBatch): return
        if not isinstance(self.label_a_batch, gpu.types.GPUBatch): return
        razor = bpy.context.scene.razor
        settings = razor.settings

        if razor.ops.active: return

        color = settings.workplane_inactive_color
        if self.is_modal:
            color = settings.workplane_modal_color
        elif self.is_highlight:
            color = settings.workplane_select_color
        elif razor.active_workplane == self.workplane.uuid:
            color = settings.workplane_active_color

        UNIFORM_COLOR.uniform_float("color", color)
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')
        gpu.state.depth_mask_set(False)

        if isinstance(self, PS_GT_Razor_Workplane_Grid):
            if not isinstance(self.border_batch, gpu.types.GPUBatch): return
            if not isinstance(self.label_b_batch, gpu.types.GPUBatch): return
            with gpu.matrix.push_pop():
                gpu.matrix.multiply_matrix(self.matrix_basis)
                self.button_batch.draw(UNIFORM_COLOR)
                if self.is_highlight:
                    if razor.active_workplane == self.workplane.uuid:
                        self.label_b_batch.draw(UNIFORM_COLOR)
                    else:
                        self.label_a_batch.draw(UNIFORM_COLOR)
        else:
            if razor.active_workplane != self.workplane.uuid: return
            with gpu.matrix.push_pop():
                gpu.matrix.multiply_matrix(self.matrix_basis)
                self.button_batch.draw(UNIFORM_COLOR)
                if self.is_highlight:
                    self.label_a_batch.draw(UNIFORM_COLOR)
        gpu.state.blend_set('NONE')


    def draw_gizmos(self, context):
        razor = bpy.context.scene.razor
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane): return
        if not isinstance(self.gizmo_batch, gpu.types.GPUBatch): return
        if razor.active_workplane != self.workplane.uuid: return
        if not self.is_modal:
            if should_omit_gizmo_for_bad_view_angle(self, context): return

        gpu.state.depth_test_set('NONE')
        gpu.state.depth_mask_set(False)

        if self.is_highlight or self.is_modal:
            gpu.state.line_width_set(3)
            UNIFORM_COLOR.uniform_float("color", self.gizmo_color)
        else:
            UNIFORM_COLOR.uniform_float("color", (1,1,1,1))

        gpu.state.blend_set('ALPHA')
        with gpu.matrix.push_pop():
            gpu.matrix.multiply_matrix(self.matrix_basis)
            self.gizmo_batch.draw(UNIFORM_COLOR)
        gpu.state.line_width_set(1)
        gpu.state.blend_set('NONE')

    # --- MODAL GRAPHICS --- #

    def setup_ghost(self):
        GRID = self.workplane.get_grid_data(gen_batches=True, corners=True)
        self.ghost_batch = GRID['CORNERS_BATCH']


    def draw_ghost(self, mode='DRAW_START_BORDER'):
        if not self.workplane: return
        gpu.state.depth_test_set('NONE')
        gpu.state.depth_mask_set(False)
        gpu.state.line_width_set(1)
        gpu.state.blend_set('ALPHA')
        if mode == 'DRAW_START_BORDER':
            if not isinstance(self.ghost_batch, gpu.types.GPUBatch): return
            UNIFORM_COLOR.uniform_float("color", self.gizmo_color)
            self.ghost_batch.draw(UNIFORM_COLOR)
        elif mode == 'FADE_ACTIVE_BORDER':
            GRID = self.workplane.get_grid_data(corners=True)
            BL, BR, TL, TR = GRID['CORNERS']
            utils.vec_fade.init(lines=[BL, TL, TL, TR, TR, BR, BR, BL], color_a=self.gizmo_color, color_b=(1,1,1), duration=0.125)
        gpu.state.blend_set('NONE')


    def draw_workplanes_border(self):
        if not self.workplanes: return
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(3)
        UNIFORM_COLOR.uniform_float("color", self.gizmo_color)
        for workplane in self.workplanes:
            GRID = workplane.get_grid_data(gen_batches=True, corners=True)
            batch = GRID['CORNERS_BATCH']
            batch.draw(UNIFORM_COLOR)
        gpu.state.line_width_set(1)
        gpu.state.blend_set('NONE')

    # --- OVERRIDES --- #

    def invoke(self, context, event):
        return {'CANCELLED'}


    def modal(self, context, event, tweak):
        return {'FINISHED'}


    def exit(self, context, cancel):
        pass


    def draw_2d(self):
        pass

# --- GRID | BORDER | SET BTN | EDIT BTN --- #

class PS_GT_Razor_Workplane_Grid(PS_Gizmo):
    bl_idname = "PS_GT_Razor_Workplane_Grid"

    def invoke(self, context, event):
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane):
            return {'CANCELLED'}

        razor = bpy.context.scene.razor
        was_active = self.workplane.uuid == razor.active_workplane

        if not razor.set_active_workplane(self.workplane.uuid):
            return {'CANCELLED'}

        if was_active:
            bpy.ops.ps.razor_workplane_popup('INVOKE_DEFAULT')

        return {'FINISHED'}


    def draw(self, context):
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane): return
        self.draw_buttons()
        if self.is_highlight:
            utils.modal_labels.fade_label_init(context, text=self.workplane.name, coord_ws=self.matrix_world.translation, remove_previous=True, duration=1.0)

        razor = bpy.context.scene.razor
        active = razor.active_workplane == self.workplane.uuid

        # Colors / Settings
        gpu.state.blend_set('ALPHA')
        settings = razor.settings
        grid_color = settings.grid_inactive_color
        border_color = settings.workplane_inactive_color
        if active:
            grid_color = settings.grid_active_color
            if razor.ops.active:
                border_color = settings.workplane_modal_color
            else:
                border_color = settings.workplane_active_color
            gpu.state.depth_test_set('NONE')
            gpu.state.depth_mask_set(False)
        else:
            gpu.state.depth_test_set('LESS_EQUAL')
            gpu.state.depth_mask_set(True)

        # Border
        if active:
            if isinstance(self.border_batch, gpu.types.GPUBatch):
                UNIFORM_COLOR.uniform_float("color", border_color)
                with gpu.matrix.push_pop():
                    gpu.matrix.multiply_matrix(self.matrix_basis)
                    self.border_batch.draw(UNIFORM_COLOR)

        # Grid
        gpu.state.line_width_set(1)
        UNIFORM_COLOR.uniform_float("color", grid_color)
        GRID = self.workplane.get_grid_data(gen_batches=True, axis_lines=True, central_lines=True)
        GRID['AXIS_LINES_X_BATCH'].draw(UNIFORM_COLOR)
        GRID['AXIS_LINES_Y_BATCH'].draw(UNIFORM_COLOR)
        if self.is_highlight or active:
            GRID['CENTRAL_LINES_X_BATCH'].draw(SMOOTH_COLOR)
            GRID['CENTRAL_LINES_Y_BATCH'].draw(SMOOTH_COLOR)

        gpu.state.depth_test_set('NONE')
        gpu.state.depth_mask_set(False)
        gpu.state.line_width_set(1)
        gpu.state.blend_set('NONE')

# --- SKETCH BTN --- #

class PS_GT_Razor_Workplane_Sketch(PS_Gizmo):
    bl_idname = "PS_GT_Razor_Workplane_Sketch"

    def invoke(self, context, event):
        if not isinstance(self.workplane, PS_PROPS_Razor_Workplane):
            return {'CANCELLED'}
        bpy.ops.ps.razor_ops('INVOKE_DEFAULT', surface_type='WORKPLANE', workplane_uuid=self.workplane.uuid)
        context.area.tag_redraw()
        return {'FINISHED'}


    def draw(self, context):
        self.draw_buttons()

# --- LOCATION --- #

class PS_Gizmo_LOC(PS_Gizmo):

    def main_local_space(self, context, event):
        # --- EVENT --- #
        self.adjusting_all = False

        # --- WORKPLANE --- #
        transform = self.workplane.transform
        mat_ws = transform.get_matrix()
        mat_ws_inv = mat_ws.inverted_safe()
        rot_mat = transform.get_rot_mat()
        rot_mat_inv = rot_mat.inverted_safe()
        center = transform.location
        normal = transform.get_normal()

        GRID = self.workplane.get_grid_data(corners=True)
        BL, BR, TL, TR = GRID['CORNERS']

        if self.gizmo_axis == 'X':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=center, plane_no=normal, fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = mat_ws_inv @ hit_point_ws

            # --- FLAGS --- #
            if self.workplane.ops_vec_a_set == False:
                self.workplane.ops_vec_a_set = True
                self.workplane.ops_vec_a = self.workplane.backup_location - hit_point_ws
            
            # --- LOCATIONS --- #
            start_point = self.workplane.ops_vec_a
            axis_L_ws = BL.lerp(TL, 0.5)
            axis_R_ws = BR.lerp(TR, 0.5)
            point_to_axis_ws, factor = geometry.intersect_point_line(start_point + hit_point_ws, axis_L_ws, axis_R_ws)
            if event.ctrl:
                point_rounded_ls = rot_mat_inv @ point_to_axis_ws
                point_rounded_ls.x = utils.math3.round_to_increment(point_rounded_ls.x, increment=0.25)
                point_rounded_ws = rot_mat @ point_rounded_ls
                transform.location = point_rounded_ws
            else:
                transform.location = point_to_axis_ws

        elif self.gizmo_axis == 'Y':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=center, plane_no=normal, fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = mat_ws_inv @ hit_point_ws

            # --- FLAGS --- #
            if self.workplane.ops_vec_a_set == False:
                self.workplane.ops_vec_a_set = True
                self.workplane.ops_vec_a = self.workplane.backup_location - hit_point_ws

            # --- LOCATIONS --- #
            start_point = self.workplane.ops_vec_a
            axis_L_ws = BL.lerp(BR, 0.5)
            axis_R_ws = TL.lerp(TR, 0.5)
            point_to_axis_ws, factor = geometry.intersect_point_line(start_point + hit_point_ws, axis_L_ws, axis_R_ws)
            if event.ctrl:
                point_rounded_ls = rot_mat_inv @ point_to_axis_ws
                point_rounded_ls.y = utils.math3.round_to_increment(point_rounded_ls.y, increment=0.25)
                point_rounded_ws = rot_mat @ point_rounded_ls
                transform.location = point_rounded_ws
            else:
                transform.location = point_to_axis_ws

        elif self.gizmo_axis == 'Z':
            # --- HIT --- #
            view_no = (context.region_data.view_rotation @ Vector((0,0,1))).normalized()
            plane_no = view_no.cross(normal)
            plane_no = plane_no.cross(normal)
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=center, plane_no=plane_no, fallback=None)
            if hit_point_ws is None: return False

            # --- FLAGS --- #
            if self.workplane.ops_vec_a_set == False:
                self.workplane.ops_vec_a_set = True
                self.workplane.ops_vec_a = self.workplane.backup_location - hit_point_ws
            
            # --- LOCATIONS --- #
            start_point = self.workplane.ops_vec_a
            axis_L_ws = center
            axis_R_ws = center + normal
            point_to_axis_ws, factor = geometry.intersect_point_line(start_point + hit_point_ws, axis_L_ws, axis_R_ws)
            point_to_axis_l = mat_ws_inv @ point_to_axis_ws
            if event.ctrl:
                point_rounded_ls = rot_mat_inv @ point_to_axis_ws
                point_rounded_ls.z = utils.math3.round_to_increment(point_rounded_ls.z, increment=0.25)
                point_rounded_ws = rot_mat @ point_rounded_ls
                transform.location = point_rounded_ws
            else:
                transform.location = point_to_axis_ws

        elif self.gizmo_axis == 'XY':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=center, plane_no=normal, fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = mat_ws_inv @ hit_point_ws

            # --- FLAGS --- #
            if self.workplane.ops_vec_a_set == False:
                self.workplane.ops_vec_a_set = True
                self.workplane.ops_vec_a = self.workplane.backup_location - hit_point_ws
            
            # --- LOCATIONS --- #
            start_point = self.workplane.ops_vec_a
            if event.ctrl:
                point_ls = rot_mat_inv @ (start_point + hit_point_ws)
                point_ls.x = utils.math3.round_to_increment(point_ls.x, increment=0.25)
                point_ls.y = utils.math3.round_to_increment(point_ls.y, increment=0.25)
                transform.location = rot_mat @ point_ls
            else:
                transform.location = hit_point_ws

        # Move All
        if event.shift:
            self.adjusting_all = True
            offset = transform.location - self.workplane.backup_location
            for workplane in self.workplanes:
                if workplane.index != self.workplane.index:
                    start_location = workplane.backup_location
                    workplane.transform.location = start_location + offset

        return True


    def invoke(self, context, event):
        if not self.modal_generic_invoke(context):
            return {'CANCELLED'}

        if not self.main_local_space(context, event):
            return {'CANCELLED'}

        self.setup_ghost()

        transform = self.workplane.transform
        help_msgs = [
            ("RMB"  , "Cancel"),
            ("SHIFT", "Move all Visible"),
            ("CTRL" , "Round"),]
        status_msgs = [("Offset", f"{transform.location.x:.03f}"),]
        self.modal_labels_controller(context, register_callback=True, unregister_callback=False, help_msgs=help_msgs, status_msgs=status_msgs)

        return {'RUNNING_MODAL'}


    def modal(self, context, event, tweak):
        if self.main_local_space(context, event):
            if not event.ctrl:
                self.draw_ghost(mode='FADE_ACTIVE_BORDER')
            transform = self.workplane.transform
            distance = (transform.location - self.workplane.backup_location).length
            status_msgs = [("Offset", f"{distance:.03f}"),]
            self.modal_labels_controller(context, status_msgs=status_msgs)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def exit(self, context, cancel):
        self.modal_generic_exit(context, cancel)


    def draw_2d(self):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()


    def draw(self, context):
        self.draw_gizmos(context)
        if self.is_modal:
            self.draw_ghost()
            if self.adjusting_all:
                self.draw_workplanes_border()


class PS_GT_Razor_Workplane_LOC_X(PS_Gizmo_LOC):
    bl_idname = "PS_GT_Razor_Workplane_LOC_X"
class PS_GT_Razor_Workplane_LOC_Y(PS_Gizmo_LOC):
    bl_idname = "PS_GT_Razor_Workplane_LOC_Y"
class PS_GT_Razor_Workplane_LOC_Z(PS_Gizmo_LOC):
    bl_idname = "PS_GT_Razor_Workplane_LOC_Z"
class PS_GT_Razor_Workplane_LOC_XY(PS_Gizmo_LOC):
    bl_idname = "PS_GT_Razor_Workplane_LOC_XY"

# --- ROTATIONS --- #

class PS_Gizmo_ROT(PS_Gizmo):

    def main_local_space(self, context, event):
        # --- EVENT --- #
        self.adjusting_all = False

        # --- WORKPLANE --- #
        transform = self.workplane.transform
        backup_rot_mat = self.workplane.backup_rotation.to_matrix().to_4x4()
        backup_loc_rot_mat = Matrix.LocRotScale(self.workplane.backup_location, self.workplane.backup_rotation, Vector((1,1,1))).to_4x4()
        backup_loc_rot_mat_inv = backup_loc_rot_mat.inverted_safe()

        if self.gizmo_axis == 'X':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=transform.location, plane_no=transform.get_x_tangent(), fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = backup_loc_rot_mat_inv @ hit_point_ws

            rot = Matrix.Rotation(math.pi/2, 4, 'Y')
            hit_point_ls = rot @ hit_point_ls
            hit_point_ls.normalize()
            terminator = rot @ Vector((0,0,1))
            terminator.normalize()

            # --- ANGLES --- #
            direction = hit_point_ls.normalized().to_2d()
            terminator = terminator.to_2d()
            angle = terminator.angle_signed(direction, 0)

            # --- FLAGS --- #
            if not self.workplane.ops_float_a_set:
                self.workplane.ops_float_a_set = True
                self.workplane.ops_float_a = angle

            # --- ROTATION --- #
            angle -= self.workplane.ops_float_a
            if event.ctrl:
                snapped_angle = utils.math3.round_to_increment(angle, increment=(math.pi/12))
                backup_rot_mat = backup_rot_mat @ Matrix.Rotation(angle - snapped_angle, 4, 'X').inverted_safe()
                self.angle = round(math.degrees(snapped_angle),3)
            else:
                self.angle = round(math.degrees(angle),3)
            rot = backup_rot_mat @ Matrix.Rotation(angle, 4, 'X')
            euler = rot.to_euler()
            transform.rotation = (round(euler.x, 6), round(euler.y, 6), round(euler.z, 6))

        elif self.gizmo_axis == 'Y':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=transform.location, plane_no=transform.get_y_tangent(), fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = backup_loc_rot_mat_inv @ hit_point_ws

            rot = Matrix.Rotation(math.pi/2, 4, 'X')
            hit_point_ls = rot @ hit_point_ls
            hit_point_ls.normalize()
            terminator = rot @ Vector((1,0,0))
            terminator.normalize()

            # --- ANGLES --- #
            direction = hit_point_ls.normalized().to_2d()
            terminator = terminator.to_2d()
            angle = terminator.angle_signed(direction, 0) * -1

            # --- FLAGS --- #
            if not self.workplane.ops_float_a_set:
                self.workplane.ops_float_a_set = True
                self.workplane.ops_float_a = angle

            # --- ROTATION --- #
            angle -= self.workplane.ops_float_a
            if event.ctrl:
                snapped_angle = utils.math3.round_to_increment(angle, increment=(math.pi/12))
                backup_rot_mat = backup_rot_mat @ Matrix.Rotation(angle - snapped_angle, 4, 'Y').inverted_safe()
                self.angle = round(math.degrees(snapped_angle),3)
            else:
                self.angle = round(math.degrees(angle),3)
            rot = backup_rot_mat @ Matrix.Rotation(angle, 4, 'Y')
            euler = rot.to_euler()
            transform.rotation = (round(euler.x, 6), round(euler.y, 6), round(euler.z, 6))

        elif self.gizmo_axis == 'Z':
            # --- HIT --- #
            hit_point_ws = utils.ray.cast_onto_plane(context, event, plane_co=transform.location, plane_no=transform.get_normal(), fallback=None)
            if hit_point_ws is None: return False
            hit_point_ls = backup_loc_rot_mat_inv @ hit_point_ws

            # --- ANGLES --- #
            direction = hit_point_ls.normalized().to_2d()
            terminator = Vector((1,0))
            angle = terminator.angle_signed(direction, 0) * -1

            # --- FLAGS --- #
            if not self.workplane.ops_float_a_set:
                self.workplane.ops_float_a_set = True
                self.workplane.ops_float_a = angle

            # --- ROTATION --- #
            angle -= self.workplane.ops_float_a
            if event.ctrl:
                snapped_angle = utils.math3.round_to_increment(angle, increment=(math.pi/12))
                backup_rot_mat = backup_rot_mat @ Matrix.Rotation(angle - snapped_angle, 4, 'Z').inverted_safe()
                self.angle = round(math.degrees(snapped_angle),3)
            else:
                self.angle = round(math.degrees(angle),3)
            rot = backup_rot_mat @ Matrix.Rotation(angle, 4, 'Z')
            euler = rot.to_euler()
            transform.rotation = (round(euler.x, 6), round(euler.y, 6), round(euler.z, 6))

        # Move All
        if event.shift:
            self.adjusting_all = True

            mat_ws = transform.get_matrix()
            mat_ws_inv = mat_ws.inverted_safe()
            rot_quat = transform.get_rot_quat()

            for workplane in self.workplanes:
                if workplane.index != self.workplane.index:
                    TRS = workplane.transform

                    loc = rot_quat @ workplane.backup_location

                    utils.vec_fade.init(points=[loc])

                    TRS.location = loc

        return True


    def invoke(self, context, event):
        if not self.modal_generic_invoke(context):
            return {'CANCELLED'}

        self.angle = 0

        if not self.main_local_space(context, event):
            return {'CANCELLED'}

        self.setup_ghost()

        help_msgs = [
            ("RMB" , "Cancel"),
            ("CTRL", "Snap")]
        status_msgs = [("Rotation", str(self.angle)),]
        self.modal_labels_controller(context, register_callback=True, unregister_callback=False, help_msgs=help_msgs, status_msgs=status_msgs)

        return {'RUNNING_MODAL'}


    def modal(self, context, event, tweak):
        if self.main_local_space(context, event):
            if not event.ctrl:
                self.draw_ghost(mode='FADE_ACTIVE_BORDER')
            status_msgs = [("Rotation", str(self.angle)),]
            self.modal_labels_controller(context, status_msgs=status_msgs)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def exit(self, context, cancel):
        self.modal_generic_exit(context, cancel)


    def draw_2d(self):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()


    def draw(self, context):
        self.draw_gizmos(context)
        if self.is_modal:
            transform = self.workplane.transform
            radius = transform.scale.length / 4
            res = 38
            if self.gizmo_axis == 'X':
                rot = Matrix((transform.get_normal(), transform.get_y_tangent(), transform.get_x_tangent(), (0, 0, 0))).to_4x4().transposed()
                utils.graphics.draw_circle_3d(radius=radius, res=res, line_width=3, color=self.gizmo_color, center=transform.location, rot=rot)
            elif self.gizmo_axis == 'Y':
                rot = Matrix((transform.get_normal(), transform.get_x_tangent(), transform.get_y_tangent(), (0, 0, 0))).to_4x4().transposed()
                utils.graphics.draw_circle_3d(radius=radius, res=res, line_width=3, color=self.gizmo_color, center=transform.location, rot=rot)
            elif self.gizmo_axis == 'Z':
                utils.graphics.draw_circle_3d(radius=radius, res=res, line_width=3, color=self.gizmo_color, center=transform.location, rot=transform.get_rot_mat())
            if self.adjusting_all:
                self.draw_workplanes_border()


class PS_GT_Razor_Workplane_ROT_X(PS_Gizmo_ROT):
    bl_idname = "PS_GT_Razor_Workplane_ROT_X"
class PS_GT_Razor_Workplane_ROT_Y(PS_Gizmo_ROT):
    bl_idname = "PS_GT_Razor_Workplane_ROT_Y"
class PS_GT_Razor_Workplane_ROT_Z(PS_Gizmo_ROT):
    bl_idname = "PS_GT_Razor_Workplane_ROT_Z"

# --- SCALE --- #

class PS_GT_Razor_Workplane_SCALE(PS_Gizmo):
    bl_idname = "PS_GT_Razor_Workplane_SCALE"

    def invoke(self, context, event):
        if not self.modal_generic_invoke(context):
            return {'CANCELLED'}

        self.setup_ghost()

        transform = self.workplane.transform
        self.start_scale = transform.uniform_scale
        self.start_pos = event.mouse_region_x

        help_msgs = [
            ("RMB"  , "Cancel"),
            ("LEFT" , "Sub"),
            ("RIGHT", "Add"),
            ("SHIFT", "Match All Visible"),
            ("CTRL" , "Round"),
            ]
        status_msgs = [("Scale", f"{transform.uniform_scale:.02f}"),]
        self.modal_labels_controller(context, register_callback=True, unregister_callback=False, help_msgs=help_msgs, status_msgs=status_msgs)

        return {'RUNNING_MODAL'}


    def modal(self, context, event, tweak):
        # --- EVENT --- #
        self.adjusting_all = False

        # --- WORKPLANE --- #
        razor = context.scene.razor
        transform = self.workplane.transform
        offset = event.mouse_region_x - self.start_pos
        offset *= (1 / 64) * utils.screen.screen_factor()
        value = self.start_scale + offset
        value = utils.math3.round_to_increment(value, increment=0.25) if event.ctrl else value
        scale = Vector((value, value, value))

        if event.shift:
            self.adjusting_all = True
            for workplane in self.workplanes:
                workplane.transform.scale = scale
        else:
            transform.scale = scale

        self.draw_ghost(mode='FADE_ACTIVE_BORDER')

        status_msgs = [("Scale", f"{max(transform.scale):.02f}"),]
        self.modal_labels_controller(context, status_msgs=status_msgs)

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def exit(self, context, cancel):
        self.modal_generic_exit(context, cancel)


    def draw_2d(self):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()


    def draw(self, context):
        self.draw_gizmos(context)
        if self.is_modal:
            self.draw_ghost()
            if self.adjusting_all:
                self.draw_workplanes_border()

# --- RESOLUTION --- #

class PS_GT_Razor_Workplane_RES(PS_Gizmo):
    bl_idname = "PS_GT_Razor_Workplane_RES"

    def invoke(self, context, event):
        if not self.modal_generic_invoke(context):
            return {'CANCELLED'}

        self.start_res = self.workplane.resolution
        self.start_pos = event.mouse_region_x

        help_msgs = [
            ("RMB"  , "Cancel"),
            ("LEFT" , "Sub"),
            ("RIGHT", "Add"),
            ("SHIFT", "Match All Visible"),
            ]
        status_msgs = [("Resolution", f"{self.workplane.resolution}"),]
        self.modal_labels_controller(context, register_callback=True, unregister_callback=False, help_msgs=help_msgs, status_msgs=status_msgs)

        return {'RUNNING_MODAL'}


    def modal(self, context, event, tweak):
        # --- EVENT --- #
        self.adjusting_all = False

        # --- WORKPLANE --- #
        razor = context.scene.razor
        offset = event.mouse_region_x - self.start_pos
        offset *= (1 / 32) * utils.screen.screen_factor()

        value = int(self.start_res + offset)

        if event.shift:
            self.adjusting_all = True
            workplanes = razor.workplanes
            for workplane in self.workplanes:
                workplane.resolution = value
        else:
            self.workplane.resolution = value

        status_msgs = [("Resolution", f"{self.workplane.resolution}"),]
        self.modal_labels_controller(context, status_msgs=status_msgs)

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}


    def exit(self, context, cancel):
        self.modal_generic_exit(context, cancel)


    def draw_2d(self):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()


    def draw(self, context):
        self.draw_gizmos(context)
        if self.is_modal:
            if self.adjusting_all:
                self.draw_workplanes_border()

########################•########################
"""                GIZMO GROUP                """
########################•########################

class PS_GGT_Razor_Workplane(GizmoGroup):
    bl_idname = "PS_GGT_Razor_Workplane"
    bl_label = "PS_GGT_Razor_Workplane"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'SCALE', 'DEPTH_3D', 'PERSISTENT', 'SHOW_MODAL_ALL'}
    INSTANCE = None

    @classmethod
    def poll(cls, context):
        return context.scene.razor.is_tool_active()


    def setup(self, context):
        global GIZMO_GROUP_INSTANCE
        GIZMO_GROUP_INSTANCE = self
        unregister_pixel_shader()
        self.grids_map = dict()
        self.gizmos.clear()
        self.refresh(context)


    def refresh(self, context):
        global GIZMO_GROUP_INSTANCE
        GIZMO_GROUP_INSTANCE = self

        razor = bpy.context.scene.razor
        workplanes = razor.workplanes

        workplane_indices = {workplane.index for workplane in razor.workplanes}
        gizmos_to_remove = set()
        for gizmo in self.gizmos:
            if not hasattr(gizmo, 'workplane') or not isinstance(gizmo.workplane, PS_PROPS_Razor_Workplane):
                gizmos_to_remove.add(gizmo)
            elif gizmo.workplane.index not in workplane_indices:
                gizmos_to_remove.add(gizmo)
        for gizmo in gizmos_to_remove:
            if gizmo in self.grids_map:
                del self.grids_map[gizmo]
            self.gizmos.remove(gizmo)

        gizmo_workplane_indices = {gizmo.workplane.index for gizmo in self.gizmos}
        for workplane in workplanes:
            if workplane.index not in gizmo_workplane_indices:
                grid_gizmo = self.gizmos.new(PS_GT_Razor_Workplane_Grid.bl_idname)
                grid_gizmo.setup_widgets(workplane)
                grid_gizmo.use_event_handle_all = True
                self.grids_map[grid_gizmo] = []

                gizmo_types = {
                    PS_GT_Razor_Workplane_Sketch,
                    PS_GT_Razor_Workplane_LOC_X,
                    PS_GT_Razor_Workplane_LOC_XY,
                    PS_GT_Razor_Workplane_LOC_Y,
                    PS_GT_Razor_Workplane_LOC_Z,
                    PS_GT_Razor_Workplane_ROT_X,
                    PS_GT_Razor_Workplane_ROT_Y,
                    PS_GT_Razor_Workplane_ROT_Z,
                    PS_GT_Razor_Workplane_SCALE,
                    PS_GT_Razor_Workplane_RES}
                for widget in gizmo_types:
                    gizmo = self.gizmos.new(widget.bl_idname)
                    gizmo.setup_widgets(workplane)
                    self.grids_map[grid_gizmo].append(gizmo)

        for grid_gizmo, gizmos in self.grids_map.items():
            if grid_gizmo.workplane.hide:
                for gizmo in gizmos:
                    gizmo.hide = gizmo.workplane.hide
            else:
                transform = grid_gizmo.workplane.transform
                matrix = transform.get_matrix()
                grid_gizmo.matrix_basis = matrix
                for gizmo in gizmos:
                    gizmo.matrix_basis = matrix
                    gizmo.hide = False

        context.area.tag_redraw()


    def draw_prepare(self, context):
        for grid_gizmo, gizmos in self.grids_map.items():
            # Hide
            if grid_gizmo.workplane.hide:
                grid_gizmo.hide = True
                for gizmo in gizmos:
                    gizmo.hide = True
            # Active
            elif context.scene.razor.ops.active:
                for gizmo in gizmos:
                    gizmo.hide = True
            # Update
            else:
                transform = grid_gizmo.workplane.transform
                matrix = transform.get_matrix()
                grid_gizmo.matrix_basis = matrix
                grid_gizmo.hide = False
                for gizmo in gizmos:
                    gizmo.matrix_basis = matrix
                    gizmo.hide = False
