########################•########################
"""                   KodoPy                  """
########################•########################

POLY_OPS_VERSION = (1, 0)
RAZOR_VERSION = (1, 0)

bl_info = {
    "name": "PolyOps",
    "description": "Blender Workflow Utilities",
    "author": "KodoPy",
    "version": (1, 0),
    "blender": (4, 3, 0),
    "location": "View3D",
    "category": "3D View"}


def register():
    from .registration import register_addon
    register_addon()


def unregister():
    from .registration import unregister_addon
    unregister_addon()