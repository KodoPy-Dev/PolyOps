########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
from bpy.props import *
from bpy.types import PropertyGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from gpu_extras.batch import batch_for_shader
from . import PROPS_BASE, PROPS_UUID, PS_PROPS_Razor_Transform

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')


class PS_PROPS_Razor_Workplane(PROPS_BASE, PROPS_UUID):
    transform  : PointerProperty(type=PS_PROPS_Razor_Transform)
    resolution : IntProperty(name="Resolution", default=32, min=6, max=256)

    # --- GRID --- #

    def get_grid_data(self, gen_batches=False, corners=False, axis_lines=False, axis_points=False, central_lines=False, origin=False):
        GRID = {}
        res = self.resolution
        mat_ws = self.transform.get_matrix()
        BL = mat_ws @ Vector((-0.5, -0.5, 0))
        BR = mat_ws @ Vector(( 0.5, -0.5, 0))
        TL = mat_ws @ Vector((-0.5,  0.5, 0))
        TR = mat_ws @ Vector(( 0.5,  0.5, 0))
        if corners:
            GRID['CORNERS'] = (BL, BR, TL, TR)
            if gen_batches:
                GRID['CORNERS_BATCH'] = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": (BL, TL, TL, TR, TR, BR, BR, BL)})
        if axis_lines:
            res = self.resolution
            step = 1 / res
            GRID['AXIS_LINES_X'] = [p for i in range(res + 1) for p in (BL.lerp(TL, step * i), BR.lerp(TR, step * i))]
            GRID['AXIS_LINES_Y'] = [p for i in range(res + 1) for p in (BL.lerp(BR, step * i), TL.lerp(TR, step * i))]
            if gen_batches:
                GRID['AXIS_LINES_X_BATCH'] = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": GRID['AXIS_LINES_X']})
                GRID['AXIS_LINES_Y_BATCH'] = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": GRID['AXIS_LINES_Y']})
        if axis_points:
            GRID['AXIS_POINTS'] = [mat_ws @ Vector((round(i/res-0.5, 6), round(j/res-0.5, 6), 0)) for i in range(res+1) for j in range(res+1)]
            if gen_batches:
                GRID['AXIS_POINTS_BATCH'] = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": GRID['AXIS_POINTS']})
        if central_lines:
            CL = BL.lerp(TL, 0.5)
            CR = BR.lerp(TR, 0.5)
            CT = TL.lerp(TR, 0.5)
            CB = BL.lerp(BR, 0.5)
            GRID['CENTRAL_LINES_X'] = [CL, CR]
            GRID['CENTRAL_LINES_Y'] = [CT, CB]
            if gen_batches:
                color_x = (1,0,0,1)
                color_y = (0,1,0,1)
                color_c = (0,0,0,0)
                GC = (BL + TR) / 2
                GRID['CENTRAL_LINES_X_BATCH'] = batch_for_shader(SMOOTH_COLOR, 'LINES', {"pos": (CL, GC, GC, CR), "color": (color_x, color_c, color_c, color_x)})
                GRID['CENTRAL_LINES_Y_BATCH'] = batch_for_shader(SMOOTH_COLOR, 'LINES', {"pos": (CT, GC, GC, CB), "color": (color_y, color_c, color_c, color_y)})
        if origin:
            GC = (BL + TR) / 2
            GRID['ORIGIN'] = GC
            if gen_batches:
                GRID['ORIGIN_BATCH'] = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": (GC,)})
        return GRID

    # --- BACKUP DATA --- #

    backup_resolution : IntProperty(name="backup_resolution"      , default=24, min=6, max=250)
    backup_location   : FloatVectorProperty(name="backup_location", default=(0.0, 0.0, 0.0), precision=3, subtype='TRANSLATION', size=3, min=-100_000, max=100_000)
    backup_rotation   : FloatVectorProperty(name="backup_rotation", default=(0.0, 0.0, 0.0), precision=3, subtype='EULER', size=3, min=-math.pi, max=math.pi)
    backup_scale      : FloatVectorProperty(name="backup_scale"   , default=(1.0, 1.0, 1.0), precision=3, subtype='TRANSLATION', size=3)

    def set_backup_data(self):
        self.backup_resolution = self.resolution
        self.backup_location = self.transform.location.copy()
        self.backup_rotation = self.transform.rotation.copy()
        self.backup_scale = self.transform.scale.copy()


    def restore_from_backup_data(self):
        self.resolution = self.backup_resolution
        self.transform.location = self.backup_location.copy()
        self.transform.rotation = self.backup_rotation.copy()
        self.transform.scale = self.backup_scale.copy()

    #--- OPS DATA ---#

    ops_float_a_set : BoolProperty(name="ops_float_a_set" , default=False)
    ops_vec_a_set   : BoolProperty(name="ops_vec_a_set"   , default=False)
    ops_rot_a_set   : BoolProperty(name="ops_rot_a_set"   , default=False)
    ops_float_a     : FloatProperty(name="ops_float_a"    , default=0.0)
    ops_vec_a       : FloatVectorProperty(name="ops_vec_a", default=(0.0, 0.0, 0.0), precision=3, subtype='TRANSLATION', size=3, min=-100_000, max=100_000)
    ops_rot_a       : FloatVectorProperty(name="ops_rot_a", default=(0.0, 0.0, 0.0), precision=3, subtype='EULER', size=3, min=-math.pi, max=math.pi)

    def reset_ops_data(self):
        self.ops_float_a_set = False
        self.ops_vec_a_set = False
        self.ops_rot_a_set = False
        self.ops_float_a = 0
        self.ops_vec_a = (0.0, 0.0, 0.0)
        self.ops_rot_a = (0.0, 0.0, 0.0)
