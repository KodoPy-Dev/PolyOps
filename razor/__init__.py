########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.props import PointerProperty
from bpy.utils import register_class, unregister_class

########################•########################
"""                   PROPS                   """
########################•########################

from .props import PS_PROPS_Razor_Transform
from .props.entity import PS_PROPS_Razor_Vertex
from .props.entity import PS_PROPS_Razor_Edge
from .props.entity import PS_PROPS_Razor_Triangle
from .props.entity import PS_PROPS_Razor_Entity
from .props.workplane import PS_PROPS_Razor_Workplane
from .props.sketch import PS_PROPS_Razor_Sketch
from .props.features import PS_PROPS_Razor_Edit_Features
from .props.features import PS_PROPS_Razor_Part_Features
from .props.settings import PS_PROPS_Razor_Settings
from .props.ops import PS_PROPS_Razor_Ops
from .props.razor import PS_PROPS_Razor

########################•########################
"""                    OPS                    """
########################•########################

from .ops.tool.operator import PS_OT_Razor
from .ops.workplane import PS_OT_Razor_Workplane_Coll_Ed

########################•########################
"""                   GIZMO                   """
########################•########################

from .gizmos.workplane import PS_GT_Razor_Workplane_Grid
from .gizmos.workplane import PS_GT_Razor_Workplane_Sketch
from .gizmos.workplane import PS_GT_Razor_Workplane_LOC_X
from .gizmos.workplane import PS_GT_Razor_Workplane_LOC_Y
from .gizmos.workplane import PS_GT_Razor_Workplane_LOC_Z
from .gizmos.workplane import PS_GT_Razor_Workplane_LOC_XY
from .gizmos.workplane import PS_GT_Razor_Workplane_ROT_X
from .gizmos.workplane import PS_GT_Razor_Workplane_ROT_Y
from .gizmos.workplane import PS_GT_Razor_Workplane_ROT_Z
from .gizmos.workplane import PS_GT_Razor_Workplane_SCALE
from .gizmos.workplane import PS_GT_Razor_Workplane_RES
from .gizmos.workplane import PS_GGT_Razor_Workplane

########################•########################
"""                 INTERFACES                """
########################•########################

from .interfaces.main import PS_OT_Razor_Popup
from .interfaces.workplane import PS_OT_Razor_Workplane_Popup

########################•########################
"""                  REGISTER                 """
########################•########################

classes = (
    # --- PROPS --- #
    PS_PROPS_Razor_Transform,
    PS_PROPS_Razor_Vertex,
    PS_PROPS_Razor_Edge,
    PS_PROPS_Razor_Triangle,
    PS_PROPS_Razor_Entity,
    PS_PROPS_Razor_Workplane,
    PS_PROPS_Razor_Edit_Features,
    PS_PROPS_Razor_Part_Features,
    PS_PROPS_Razor_Sketch,
    PS_PROPS_Razor_Settings,
    PS_PROPS_Razor_Ops,
    PS_PROPS_Razor,
    # --- OPS --- #
    PS_OT_Razor,
    PS_OT_Razor_Workplane_Coll_Ed,
    # --- GIZMOS --- #
    PS_GT_Razor_Workplane_Grid,
    PS_GT_Razor_Workplane_Sketch,
    PS_GT_Razor_Workplane_LOC_X,
    PS_GT_Razor_Workplane_LOC_Y,
    PS_GT_Razor_Workplane_LOC_Z,
    PS_GT_Razor_Workplane_LOC_XY,
    PS_GT_Razor_Workplane_ROT_X,
    PS_GT_Razor_Workplane_ROT_Y,
    PS_GT_Razor_Workplane_ROT_Z,
    PS_GT_Razor_Workplane_SCALE,
    PS_GT_Razor_Workplane_RES,
    PS_GGT_Razor_Workplane,
    # --- INTERFACES --- #
    PS_OT_Razor_Popup,
    PS_OT_Razor_Workplane_Popup,
)

def register():

    # BPY Types
    for cls in classes:
        register_class(cls)

    # Pointers
    bpy.types.Scene.razor = PointerProperty(name="PolyOps Props", type=PS_PROPS_Razor)

    # Tool
    from .tool import PS_WT_RazorTool
    bpy.utils.register_tool(PS_WT_RazorTool, after="builtin.cursor", separator=True, group=False)


def unregister():

    # Tool
    from .tool import PS_WT_RazorTool
    bpy.utils.unregister_tool(PS_WT_RazorTool)

    # Graphics
    from .ops.tool import graphics
    graphics.unregister_shader_handles()

    # Pointers
    del bpy.types.Scene.razor

    # BPY Types
    for cls in reversed(classes):
        unregister_class(cls)
