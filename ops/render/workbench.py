########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils

DESC = """Workbench Settings\n
• Preset 1 (LMB)
• Preset 2 (SHIFT)"""

class PS_OT_Workbench(bpy.types.Operator):
    bl_idname      = "ps.workbench_settings"
    bl_label       = "Workbench Settings"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.render.has_multiple_engines


    def invoke(self, context, event):
        bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
        self.use_preset_1 = not event.shift
        return self.execute(context)


    def execute(self, context):

        prefs = utils.addon.user_prefs()
        props = prefs.operator.workbench
        scene = context.scene
        display = scene.display

        if self.use_preset_1:
            display.render_aa = props.PRESET_1_render_samples
            display.viewport_aa = props.PRESET_1_vp_samples
            display.shading.color_type = props.PRESET_1_shading_color
            display.shading.show_shadows = props.PRESET_1_shadows
            display.shading.show_cavity = props.PRESET_1_cavity
        else:
            display.render_aa = props.PRESET_2_render_samples
            display.viewport_aa = props.PRESET_2_vp_samples
            display.shading.color_type = props.PRESET_2_shading_color
            display.shading.show_shadows = props.PRESET_2_shadows
            display.shading.show_cavity = props.PRESET_2_cavity

        msgs = [
            ("Workbench", "Preset 1" if self.use_preset_1 else "Preset 2"),
            ("Render Samples", str(display.render_aa)),
            ("Viewport Samples", str(display.viewport_aa)),
            ("Shading Color", str(display.shading.color_type)),
            ("Shadows", "On" if display.shading.show_shadows else "Off"),
            ("Cavity", "On" if display.shading.show_cavity else "Off"),
            ]
        utils.notifications.init(context, messages=msgs)

        return {'FINISHED'}


    def draw(self, context):
        prefs = utils.addon.user_prefs()
        props = prefs.operator.workbench
        box = self.layout.box()
        if self.use_preset_1:
            row = box.row(align=True)
            row.prop(props, 'PRESET_1_render_samples')
            row = box.row(align=True)
            row.prop(props, 'PRESET_1_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'PRESET_1_shading_color')
            row = box.row(align=True)
            row.prop(props, 'PRESET_1_shadows')
            row = box.row(align=True)
            row.prop(props, 'PRESET_1_cavity')
        else:
            row = box.row(align=True)
            row.prop(props, 'PRESET_2_render_samples')
            row = box.row(align=True)
            row.prop(props, 'PRESET_2_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'PRESET_2_shading_color')
            row = box.row(align=True)
            row.prop(props, 'PRESET_2_shadows')
            row = box.row(align=True)
            row.prop(props, 'PRESET_2_cavity')

