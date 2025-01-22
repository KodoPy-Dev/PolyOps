########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import math
import numpy as np
import heapq
import time
import ctypes
import gc
from collections import deque
from random import randint
from math import cos, sin, radians, degrees, pi
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from mathutils.geometry import tessellate_polygon, interpolate_bezier
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from ... import utils


class PS_OT_StaticTesting(bpy.types.Operator):
    bl_idname      = "ps.static_testing"
    bl_label       = "Static Testing"
    bl_description = "Static Testinging"
    bl_options     = {'REGISTER', 'UNDO'}

    # Settings
    test : IntProperty(name="Test", default=3, min=0)

    # Props
    bool_1  : BoolProperty(name="Bool 1", default=False)
    int_1   : IntProperty(name="Int 1", default=12)
    float_1 : FloatProperty(name="Float 1", default=0.0)
    rot_1   : FloatVectorProperty(name="Rot 1", default=(0.0, 0.0, 0.0), precision=3, subtype='EULER', size=3)
    vec_1   : FloatVectorProperty(name="Vec 1", default=(1.0, 0.0, 0.0), precision=3, subtype='TRANSLATION', size=3)
    vec_2   : FloatVectorProperty(name="Vec 2", default=(-1.0, 0.0, 0.0), precision=3, subtype='TRANSLATION', size=3)
    vec_3   : FloatVectorProperty(name="Vec 3", default=(0.0, 1.0, 0.0), precision=3, subtype='TRANSLATION', size=3)

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        utils.modal_ops.reset_and_clear_handles()
        return self.execute(context)


    def execute(self, context):
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>> TEST >>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if self.test == 1:
            test_1(self, context)
        elif self.test == 2:
            test_2(self, context)
        elif self.test == 3:
            test_3(self, context)
        return {'FINISHED'}


    def draw(self, context):
        # Settings
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'test', text="Test")

        # Props
        box = self.layout.box()
        props = ['bool_1', 'int_1', 'float_1', 'rot_1', 'vec_1', 'vec_2', 'vec_3']
        for prop in props:
            row = box.row()
            row.prop(self, prop, text=prop.title())

########################•########################
"""                   TEST                    """
########################•########################

def test_1(self, context):

    p1 = Vector((-2,0,0))
    p2 = Vector((0,2,0))
    p3 = Vector((2,0,0))

    l1 = p1.lerp(p2, self.float_1)
    l2 = p2.lerp(p3, self.float_1)
    l3 = l1.lerp(l2, self.float_1)

    utils.vec_fade.init(points=[p1, p2, p3], lines=[p1, p2, p2, p3], color_a=(1,0,0), color_b=(1,0,0))
    utils.vec_fade.init(points=[l1, l2], lines=[l1, l2], color_a=(0,0,1), color_b=(0,0,1), duration=.75)
    utils.vec_fade.init(points=[l3], color_a=(0,1,0), color_b=(0,1,0), point_size=8, duration=1.5)


def test_2(self, context):

    duration = 12

    rot = self.rot_1.to_quaternion()

    zero = Vector((0,0,0))
    vec_1 = self.vec_1
    vec_2 = rot @ self.vec_2

    utils.vec_fade.init(points=[zero], color_a=(1,1,1), color_b=(1,1,1), duration=duration)
    utils.vec_fade.init(lines=[zero, vec_1], color_a=(1,0,0), color_b=(1,0,0), duration=duration)
    utils.vec_fade.init(lines=[zero, vec_2], color_a=(0,1,0), color_b=(0,1,0), duration=duration)

    dot = vec_1.dot(vec_2)
    vec_3 = vec_1 * dot

    utils.vec_fade.init(lines=[zero, vec_3], line_width=8, color_a=(1,1,1), color_b=(1,1,1), duration=duration)
    utils.vec_fade.init(lines=[vec_2, vec_3], line_width=8, color_a=(1,0,1), color_b=(1,0,1), duration=duration)
    utils.modal_labels.fade_label_init(context, text=f"{dot:.03f}", coord_ws=vec_3, remove_previous=True, duration=duration)


def test_3(self, context):

    duration = 12
    res = self.int_1 if self.int_1 >= 3 else 3

    direction = self.vec_1 - self.vec_2
    length = direction.length
    normal = direction.normalized()
    offset = length * normal.orthogonal().normalized()

    handle_1 = self.vec_1 + offset
    handle_2 = self.vec_2 + offset

    VERTS = interpolate_bezier(self.vec_1, handle_1, handle_2, self.vec_2, res)
    count = len(VERTS) - 1
    EDGES = [(i, i + 1) for i in range(count)]
    lines = [VERTS[index] for edge in EDGES for index in edge]

    utils.vec_fade.init(points=VERTS, lines=lines, point_size=6, line_width=2, color_a=(1,1,1), color_b=(1,1,1), duration=duration)
    utils.vec_fade.init(points=[self.vec_1, self.vec_2, handle_1, handle_2], point_size=8, color_a=(1,0,1), color_b=(1,0,1), duration=duration)

