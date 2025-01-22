########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from bpy.props import BoolProperty, IntProperty, StringProperty, EnumProperty, FloatProperty
from ..gizmos.workplane import refresh_workplane_gizmo_group
from ... import utils


class PS_OT_Razor_Workplane_Coll_Ed(bpy.types.Operator):
    bl_idname      = "ps.razor_workplane_coll_ed"
    bl_label       = "Razor Workplane Data Edit"
    bl_description = "Workplane Activation"
    bl_options     = {'REGISTER'}

    edit_opts = (
        ('REFRESH'   , "REFRESH"   , ""),
        ('ADD'       , "ADD"       , ""),
        ('DEL_ALL'   , "DEL_ALL"   , ""),
        ('DEL_HIDDEN', "DEL_HIDDEN", ""),
        ('DEL_SEL'   , "DEL_SEL"   , ""),
        ('SET_ACTIVE', "SET_ACTIVE", ""),
        ('HIDE'      , "HIDE"      , ""),
        ('UNHIDE'    , "UNHIDE"    , ""),
        ('PRESET_BOX', "PRESET_BOX", ""),
    )
    edit  : EnumProperty(name="Edit Options", items=edit_opts, default='REFRESH')
    uuid : StringProperty(name="UUID", default="")
    scale : FloatProperty(name="Scale", default=5, min=1, max=100)
    resolution : IntProperty(name="Resolution", default=24, min=6, max=250)

    @classmethod
    def poll(cls, context):
        return context.scene.razor.is_tool_active()


    def invoke(self, context, event):
        razor = bpy.context.scene.razor
        workplanes = razor.workplanes
        needs_refresh = False

        if self.edit == 'REFRESH':
            needs_refresh = True

        elif self.edit == 'ADD':
            workplane = razor.new_workplane(name="", set_active=True)
            if workplane is None:
                utils.notifications.init(context, messages=[("$Error", f"Workplane limit reached : {razor.settings.max_workplanes}")])
            else:
                needs_refresh = True

        elif self.edit == 'DEL_ALL':
            if workplanes:
                return context.window_manager.invoke_confirm(self, event, title='Delete All Workplanes', message='Are you sure you want to delete all Workplanes?', confirm_text='Delete', icon='WARNING')
            else:
                utils.notifications.init(context, messages=[("$Error", "No Workplanes to Delete")])

        elif self.edit == 'DEL_HIDDEN':
            if any(workplane.hide for workplane in workplanes):
                return context.window_manager.invoke_confirm(self, event, title='Delete Hidden Workplanes', message='Are you sure you want to delete hidden Workplanes?', confirm_text='Delete', icon='WARNING')
            else:
                utils.notifications.init(context, messages=[("$Error", "No Hidden Workplanes to Delete")])

        elif self.edit == 'DEL_SEL':
            if any(workplane.uuid == self.uuid for workplane in workplanes):
                return context.window_manager.invoke_confirm(self, event, title='Delete Selected Workplane', message='Are you sure you want to delete selected Workplane?', confirm_text='Delete', icon='WARNING')
            else:
                utils.notifications.init(context, messages=[("$Error", "No Selected Workplanes to Delete")])

        elif self.edit == 'SET_ACTIVE':
            if razor.set_active_workplane(self.uuid):
                needs_refresh = True

        elif self.edit == 'HIDE':
            if razor.set_hide_workplane(self.uuid, hide=True, set_active=False):
                needs_refresh = True

        elif self.edit == 'UNHIDE':
            if razor.set_hide_workplane(self.uuid, hide=False, set_active=True):
                needs_refresh = True

        elif self.edit == 'PRESET_BOX':
            if len(workplanes) + 3 > razor.settings.max_workplanes:
                utils.notifications.init(context, messages=[("$Error", f"Workplane limit reached : {razor.settings.max_workplanes}")])
            else:
                needs_refresh = True
                offset = self.scale / 2
                scale = Vector((self.scale, self.scale, self.scale))

                workplane = razor.new_workplane(name="Front", set_active=True)
                workplane.resolution = self.resolution
                transform = workplane.transform
                transform.location = Vector((0, -offset, offset))
                transform.rotation = Euler((math.radians(90), 0, 0))
                transform.scale = scale

                workplane = razor.new_workplane(name="Side", set_active=False)
                workplane.resolution = self.resolution
                transform = workplane.transform
                transform.location = Vector((offset, 0, offset))
                transform.rotation = Euler((math.radians(90), 0, math.radians(90)))
                transform.scale = scale

                workplane = razor.new_workplane(name="Bottom", set_active=False)
                workplane.resolution = self.resolution
                transform = workplane.transform
                transform.location = Vector((0, 0, 0))
                transform.rotation = Euler((0, 0, 0))
                transform.scale = scale

        if needs_refresh:
            refresh_workplane_gizmo_group(context)
        return {'FINISHED'}


    def execute(self, context):
        razor = bpy.context.scene.razor

        if self.edit == 'DEL_ALL':
            razor.del_all_workplanes()

        elif self.edit == 'DEL_HIDDEN':
            razor.del_hidden_workplanes()

        elif self.edit == 'DEL_SEL':
            razor.del_workplane(self.uuid)

        refresh_workplane_gizmo_group(context)
        return {'FINISHED'}
