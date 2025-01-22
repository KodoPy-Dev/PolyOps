########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty


class PS_PROPS_Dev(PropertyGroup):
    debug_mode : BoolProperty(name="Debug Mode", default=True)
    data_write_type_opts = (
        ('VERTS_INDICES_JS', "VERTS_INDICES_JS", ""),
        ('VERTS_INDICES_PY', "VERTS_INDICES_PY", ""),
        ('LINES_PY'        , "LINES_PY"        , ""),
        ('ICON_DAT'        , "ICON_DAT"        , ""),
    )
    data_write_type : EnumProperty(name="data_write_type", items=data_write_type_opts, default='LINES_PY')

