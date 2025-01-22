########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty
from ... import utils

class PS_OT_Razor_Popup(bpy.types.Operator):
    bl_idname      = "ps.razor_popup"
    bl_label       = "Razor Popup"
    bl_description = "Razor Popup"

    popup_tab_opts = (
        ('WORKPLANE', "Workplane", ""),
        ('SKETCH', "Sketch", ""),
        ('FEATURES', "Features", ""),
        ('SETTINGS', "Settings", ""),
    )
    popup_tabs : EnumProperty(name="popup_tabs", items=popup_tab_opts, default='WORKPLANE')
    resolution : IntProperty(name="Resolution", default=32, min=6, max=256)
    scale : FloatProperty(name="Scale", default=5, min=1, max=100)

    @classmethod
    def poll(cls, context):
        return context.scene.razor.is_tool_active()


    def invoke(self, context, event):
        self.popup_tabs = 'WORKPLANE'
        return context.window_manager.invoke_popup(self, width=375)


    def execute(self, context):
        return {'FINISHED'}


    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)

        formcraft_label = utils.addon.version(opt='POLY_OPS', as_label=True)
        razor_label = utils.addon.version(opt='RAZOR', as_label=True)
        info = f"{formcraft_label} • {razor_label}"
        row.label(text=info)

        row = layout.row(align=True)
        row.prop(self, 'popup_tabs', expand=True)

        if self.popup_tabs == 'WORKPLANE':
            self.draw_workplanes(context, layout)
        elif self.popup_tabs == 'SKETCH':
            self.draw_sketch(context, layout)
        elif self.popup_tabs == 'FEATURES':
            self.draw_features(context, layout)
        elif self.popup_tabs == 'SETTINGS':
            self.draw_settings(context, layout)

        context.area.tag_redraw()


    def draw_workplanes(self, context, layout):
        row = layout.row(align=True)
        row.label(text="Workplanes", icon='SNAP_GRID')
        razor = context.scene.razor
        workplanes = razor.workplanes
        # ------------------------ Workplanes ------------------------ #

        # Edit
        box = layout.box()
        row = box.row(align=False)
        row.label(text="Edit")
        row = box.row(align=False)
        props = row.operator('ps.razor_workplane_coll_ed', text='Add', icon='PLUS')
        props.edit = 'ADD'
        props = row.operator('ps.razor_workplane_coll_ed', text='Hidden', icon='TRASH')
        props.edit = 'DEL_HIDDEN'
        props = row.operator('ps.razor_workplane_coll_ed', text='All', icon='TRASH')
        props.edit = 'DEL_ALL'

        # Workplanes
        box = layout.box()
        if workplanes:
            for workplane in workplanes:
                transform = workplane.transform
                is_active = workplane.uuid == razor.active_workplane
                row = box.row()
                if is_active:
                    row.alert = True
                row.prop(workplane, 'name', text='')
                row.prop(workplane, 'resolution', text='Res')
                row.prop(transform, 'uniform_scale', text='Sca')
                icon = 'RESTRICT_SELECT_OFF' if is_active else 'RESTRICT_SELECT_ON'
                props = row.operator('ps.razor_workplane_coll_ed', text='', icon=icon)
                props.edit = 'SET_ACTIVE'
                props.uuid = workplane.uuid
                if workplane.hide:
                    props = row.operator('ps.razor_workplane_coll_ed', text='', icon='HIDE_ON')
                    props.edit = 'UNHIDE'
                    props.uuid = workplane.uuid
                else:
                    props = row.operator('ps.razor_workplane_coll_ed', text='', icon='HIDE_OFF')
                    props.edit = 'HIDE'
                    props.uuid = workplane.uuid
                props = row.operator('ps.razor_workplane_coll_ed', text='', icon='TRASH')
                props.edit = 'DEL_SEL'
                props.uuid = workplane.uuid
        else:
            row = box.row()
            row.label(text="No Workplanes")

        # Presets
        box = layout.box()
        row = box.row()
        row.label(text="Preset Box")
        row = box.row()
        props = row.operator('ps.razor_workplane_coll_ed', text='Generate', icon='MOD_EXPLODE')
        row.prop(self, 'resolution', text="Resolution")
        row.prop(self, 'scale', text="Scale")
        props.edit = 'PRESET_BOX'
        props.scale = self.scale
        props.resolution = self.resolution


    def draw_sketch(self, context, layout):
        row = layout.row(align=True)
        row.label(text="Sketchs", icon='GREASEPENCIL')
        box = layout.box()
        razor = context.scene.razor
        sketches = razor.sketches
        # ------------------------ Sketches ------------------------ #
        for sketch in sketches:
            is_active = sketch.uuid == razor.active_sketch
            row = box.row()
            if is_active:
                row.alert = True
            row.prop(sketch, 'name', text='')


    def draw_features(self, context, layout):
        row = layout.row(align=True)
        row.label(text="Features", icon='MODIFIER')
        box = layout.box()
        razor = context.scene.razor
        features = razor.features
        # ------------------------ Features ------------------------ #
        row = box.row(align=True)
        row.prop(features, 'use_extrude')
        row = box.row(align=True)
        row.prop(features, 'use_mirror')
        row = box.row(align=True)
        row.prop(features, 'use_array')


    def draw_settings(self, context, layout):
        row = layout.row(align=True)
        row.label(text="General", icon='TOOL_SETTINGS')
        razor = context.scene.razor
        settings = razor.settings
        # ------------------------ Settings ------------------------ #

        # Booleans
        box = layout.box()
        row = box.row(align=False)
        row.label(text="Booleans")
        row = box.row(align=False)
        row.prop(settings, 'is_destructive_mode')
        row = box.row(align=False)
        row.prop(settings, 'boolean_solver_mode', expand=True)

        # Workplanes
        box = layout.box()
        row = box.row(align=False)
        row.label(text="Workplanes")
        row = box.row(align=False)
        row.prop(settings, 'max_workplanes')

        row = box.row(align=False)
        row.prop(settings, 'grid_active_color')
        row = box.row(align=False)
        row.prop(settings, 'grid_inactive_color')
        row = box.row(align=False)
        row.prop(settings, 'workplane_modal_color')
        row = box.row(align=False)
        row.prop(settings, 'workplane_select_color')
        row = box.row(align=False)
        row.prop(settings, 'workplane_active_color')
        row = box.row(align=False)
        row.prop(settings, 'workplane_inactive_color')
