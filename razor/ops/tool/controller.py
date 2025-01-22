########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from . import sketch
from .data import DB
from . import interface
from .graphics import setup_help_panel, setup_status_panel
from ....utils import debug_print
from .... import utils


def setup(context, event, op):
    DB.init(context, event)
    DB.update(context, event)
    prefs = DB.prefs
    razor = DB.razor

    # Error
    if prefs is None or razor is None or DB.runtime is None:
        bpy.context.scene.razor.ops.status = 'ERROR'
        debug_print("Error : None type found")
        return

    # Surface : Operator : Workplane
    if op.surface_type == 'WORKPLANE':
        workplane = razor.get_workplane(op.workplane_uuid)
        if workplane is not None:
            if not workplane.hide:
                razor.ops.surface = 'WORKPLANE'
                DB.surface.setup_for_workplane(workplane)

    # Surface : Operator : Object
    elif op.surface_type == 'OBJECT':
        if op.object_name in bpy.data.objects:
            obj = bpy.data.objects[op.object_name]
            if utils.mesh.mesh_obj_is_valid(context, obj, check_visible=True, check_select=True, check_has_polys=True):
                razor.ops.surface = 'OBJECT'
                DB.surface.setup_for_obj(obj)

    # Surface : Object
    if razor.ops.surface == 'NONE':
        obj = context.active_object
        if utils.mesh.mesh_obj_is_valid(context, obj, check_visible=True, check_select=True, check_has_polys=True):
            razor.ops.surface = 'OBJECT'
            DB.surface.setup_for_obj(obj)

    # Surface : World
    if razor.ops.surface == 'NONE':
        razor.ops.surface = 'WORLD'
        DB.surface.setup_for_world(axis='XY')

    # Error
    if razor.ops.surface == 'NONE':
        razor.ops.status = 'ERROR'
        debug_print("Error : Surface setup")
        return

    # Shape
    valid = DB.graph.setup()

    # Error
    if not valid:
        razor.ops.status = 'ERROR'
        debug_print("Error : Graph setup")
        return

    # Part
    DB.part.setup()

    # Error
    items = (DB.part.obj, DB.part.mesh, DB.part.bm)
    if any(item is None for item in items):
        razor.ops.status = 'ERROR'
        debug_print("Error : Part Error")
        return

    # GUI
    interface.setup()

    # Status
    razor.ops.status = 'RUNNING'


def update(context, event, op):
    prefs = DB.prefs
    razor = DB.razor

    # Status
    razor.ops.status = 'RUNNING'

    # Runtime
    DB.update(context, event)

    # GUI
    interface.update()
    if razor.ops.status in {'FINISHED', 'CANCELLED', 'ERROR'}:
        return
    if razor.ops.in_menu:
        return

    # Sketch
    if razor.ops.tool == 'SKETCH':
        # World Space
        if razor.ops.space == 'VIEW_3D':
            sketch.update_WS()
        # Screen Space
        elif razor.ops.space == 'VIEW_2D':
            sketch.update_SS()

    # Exit
    if razor.ops.status in {'FINISHED', 'CANCELLED', 'ERROR'}:
        return
    # Confirm
    elif event.type in {'SPACE'}:
        razor.ops.status = 'FINISHED'
    # Cancel
    elif event.type in {'ESC', 'RIGHTMOUSE'}:
        razor.ops.status = 'CANCELLED'
    # Pass Through
    elif utils.event.pass_through(event, with_scoll=True, with_numpad=True, with_shading=True):
        razor.ops.status = 'PASS_THROUGH'
    # Help
    elif event.type == 'H' and event.value == 'PRESS':
        prefs.settings.show_modal_help = not prefs.settings.show_modal_help
        setup_help_panel()


def exit_modal(context):
    interface.close()
    DB.close()
