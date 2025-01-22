########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils


class PS_OT_Razor_Workplane_Popup(bpy.types.Operator):
    bl_idname      = "ps.razor_workplane_popup"
    bl_label       = "Razor Workplane Popup"
    bl_description = "Razor Workplane Popup"

    @classmethod
    def poll(cls, context):
        return context.scene.razor.is_tool_active()


    def invoke(self, context, event):
        self.workplane = None
        razor = bpy.context.scene.razor
        workplanes = razor.workplanes
        active_uuid = razor.active_workplane
        for workplane in workplanes:
            if workplane.uuid == active_uuid:
                self.workplane = workplane
                return context.window_manager.invoke_popup(self, width=300)
        return {'CANCELLED'}


    def execute(self, context):
        return {'FINISHED'}


    def draw(self, context):
        if not self.workplane: return
        layout = self.layout
        row = layout.row(align=True)
        row.label(text='Edit Workplane')

        row = layout.row(align=False)
        if self.workplane.hide:
            props = row.operator('ps.razor_workplane_coll_ed', text='Unhide', icon='HIDE_ON')
            props.edit = 'SET_ACTIVE'
            props.uuid = self.workplane.uuid
        else:
            props = row.operator('ps.razor_workplane_coll_ed', text='Hide', icon='HIDE_OFF')
            props.edit = 'HIDE'
            props.uuid = self.workplane.uuid
        props = row.operator('ps.razor_workplane_coll_ed', text='', icon='TRASH')
        props.edit = 'DEL_SEL'
        props.uuid = self.workplane.uuid

        row = layout.row(align=True)
        row.label(text='Name')
        row = layout.row(align=True)
        row.prop(self.workplane, 'name', text='')

        row = layout.row(align=True)
        row.label(text='Settings')

        row = layout.row(align=True)
        box = row.box()
        row = box.row(align=True)
        row.prop(self.workplane, 'resolution')

        row = layout.row(align=True)
        box = row.box()

        transform = self.workplane.transform

        col = box.column()
        col.use_property_split = True
        row = col.row(align=True)
        row.prop(transform, 'location')

        col = box.column()
        col.use_property_split = True
        row = col.row(align=True)
        row.prop(transform, 'rotation')

        col = box.column()
        col.use_property_split = True
        row = col.row(align=True)
        row.prop(transform, 'uniform_scale', text='Scale')
