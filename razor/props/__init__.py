########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
from uuid import uuid4
from bpy.props import *
from bpy.types import PropertyGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from gpu_extras.batch import batch_for_shader

########################•########################
"""                  OPTIONS                  """
########################•########################

GET_TYPE_SET = lambda opts : {opt[0] for opt in opts}

STATUS_OPTS = (
    ('RUNNING'     , "RUNNING"     , ""),
    ('MENU'        , "MENU"        , ""),
    ('FINISHED'    , "FINISHED"    , ""),
    ('CANCELLED'   , "CANCELLED"   , ""),
    ('ERROR'       , "ERROR"       , ""),
    ('PASS_THROUGH', "PASS_THROUGH", ""),
)

SPACE_OPTS = (
    ('VIEW_3D' , "VIEW_3D" , ""),
    ('VIEW_2D' , "VIEW_2D" , ""),
)

SURFACE_OPTS = (
    ('NONE'     , "NONE"     , ""),
    ('WORKPLANE', "WORKPLANE", ""),
    ('OBJECT'   , "OBJECT"   , ""),
    ('WORLD'    , "WORLD"    , ""),
    ('SCREEN'   , "SCREEN"   , ""),
)

TOOL_OPTS = (
    ('SKETCH'   , "SKETCH"   , ""),
    ('TRANSFORM', "TRANSFORM", ""),
)

SHAPE_OPTS = (
    ('POINT'    , "POINT"    , ""),
    ('LINE'     , "LINE"     , ""),
    ('CIRCLE'   , "CIRCLE"   , ""),
    ('RECTANGLE', "RECTANGLE", ""),
    ('NGON'     , "NGON"     , ""),
    ('ARC'      , "ARC"      , ""),
    ('ELLIPSE'  , "ELLIPSE"  , ""),
)

ENTITY_EDIT_OPTS = (
    ('NONE'  , "NONE"  , ""),
    ('TRIM'  , "TRIM"  , ""),
    ('ARRAY' , "ARRAY" , ""),
    ('MIRROR', "MIRROR", ""),
    ('DELETE', "DELETE", ""),
)

BOOLEAN_SOLVER_OPTS = (
    ('EXACT', "EXACT", ""),
    ('FAST' , "FAST" , ""),
)

UNDO_TYPE_OPTS = (
    ('NEW_SKETCH', "NEW_SKETCH", ""),
    ('NEW_ENTITY', "NEW_ENTITY", ""),
    ('OPS_POINT' , "OPS_POINT" , ""),
)

########################•########################
"""                  LOOKUPS                  """
########################•########################

ENTITY_POINT_COUNT_NEEDED = {
    'POINT'     : 1,
    'LINE'      : 2,
    'CIRCLE'    : 2,
    'RECTANGLE' : 2,
    'NGON'      : 3,
    'ELLIPSE'   : 3,
    'ARC'       : 4,
}

ENTITY_TRIS_NEEDED = {'CIRCLE', 'RECTANGLE', 'NGON', 'ELLIPSE'}

########################•########################
"""                   SUPER                   """
########################•########################

class PROPS_BASE(PropertyGroup):
    ''' name | index | hide '''

    name  : StringProperty(name="Name", default="")
    index : IntProperty(name="Index", default=0, min=0)
    hide  : BoolProperty(name="Hide", default=True)


class PROPS_INDEXER(PropertyGroup):
    ''' last_index | next_index '''

    def __get_next_index(self):
        self.last_index += 1
        return self.last_index
    last_index : IntProperty(name="last_index", default=0, min=0)
    next_index : IntProperty(name="next_index", default=0, min=0, get=__get_next_index)


class PROPS_UUID(PropertyGroup):
    ''' uuid '''

    def __get_uuid(self):
        if not self.private_uuid:
            self.private_uuid = str(uuid4())
        return self.private_uuid
    private_uuid : StringProperty(name="Private UUID", default="")
    uuid : StringProperty(name="UUID", default="", get=__get_uuid)

########################•########################
"""                  COMMON                   """
########################•########################

class PS_PROPS_Razor_Transform(PROPS_BASE):

    def __get_uniform_scale(self):
        return max(self.scale)

    def __set_uniform_scale(self, value):
        self.scale = Vector((value, value, value))

    location : FloatVectorProperty(name="Location", default=(0.0, 0.0, 0.0), precision=3, subtype='TRANSLATION', size=3)
    rotation : FloatVectorProperty(name="Rotation", default=(0.0, 0.0, 0.0), precision=3, subtype='EULER', size=3)
    scale    : FloatVectorProperty(name="Scale"   , default=(1.0, 1.0, 1.0), precision=3, subtype='TRANSLATION', size=3)
    uniform_scale : FloatProperty(name="uniform_scale", default=1.0, get=__get_uniform_scale, set=__set_uniform_scale)


    def get_matrix(self):
        return Matrix.LocRotScale(self.location, self.rotation, self.scale)


    def get_matrix_inverted(self):
        return Matrix.LocRotScale(self.location, self.rotation, self.scale).inverted_safe()


    def set_matrix(self, matrix):
        loc, rot, sca = matrix.decompose()
        self.location = loc
        self.rotation = rot.to_euler()
        self.scale = sca


    def get_normal(self):
        return (self.rotation.to_quaternion() @ Vector((0,0,1))).normalized()


    def get_rot_mat(self):
        return self.rotation.to_matrix().to_4x4()


    def get_rot_quat(self):
        return self.rotation.to_quaternion()


    def get_x_tangent(self):
        return (self.rotation.to_quaternion() @ Vector((1,0,0))).normalized()


    def get_y_tangent(self):
        return (self.rotation.to_quaternion() @ Vector((0,1,0))).normalized()


    def get_scale_mat(self):
        return Matrix.Diagonal(self.scale)


    def get_transposed(self):
        return self.rotation.to_matrix().transposed()


    def get_loc_mat(self):
        return Matrix.Translation(self.location)


    def get_loc_rot_mat(self):
        return Matrix.LocRotScale(self.location, self.rotation, Vector((1, 1, 1)))
