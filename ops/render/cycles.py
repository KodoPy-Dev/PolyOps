########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils

DESC = """Cycles Settings\n
• HQ (LMB)
\t\t→ High Quality Settings\n
• LQ (SHIFT)
\t\t→ Low Quality Settings\n"""

class PS_OT_Cycles(bpy.types.Operator):
    bl_idname      = "ps.cycles_settings"
    bl_label       = "Cycles Settings"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.render.has_multiple_engines


    def invoke(self, context, event):
        bpy.context.scene.render.engine = 'CYCLES'
        self.use_HQ = not event.shift
        return self.execute(context)


    def execute(self, context):

        prefs = utils.addon.user_prefs()
        props = prefs.operator.cycles
        cycles = context.scene.cycles

        if self.use_HQ:
            cycles.samples = props.HQ_render_samples
            cycles.use_denoising = True
            cycles.adaptive_threshold = props.HQ_adaptive_threshold
            cycles.preview_samples = props.HQ_vp_samples
            cycles.use_preview_denoising = True
            cycles.max_bounces = props.HQ_max_light_bounces
            cycles.use_fast_gi = False

        else:
            cycles.samples = props.LQ_render_samples
            cycles.use_denoising = True
            cycles.adaptive_threshold = props.LQ_adaptive_threshold
            cycles.preview_samples = props.LQ_vp_samples
            cycles.use_preview_denoising = True
            cycles.max_bounces = props.LQ_max_light_bounces
            cycles.use_fast_gi = False

        msgs = [
            ("Engine"        , "Cycles : HQ" if self.use_HQ else "Cycles : LQ"),
            ("Render Samples", str(cycles.samples)),
            ("Adaptive Threshold", f"{cycles.adaptive_threshold:.03f}"),
            ("Viewport Samples", str(cycles.preview_samples)),
            ("Max Light Bounces", str(cycles.max_bounces)),
            ]
        utils.notifications.init(context, messages=msgs)

        return {'FINISHED'}


    def draw(self, context):
        prefs = utils.addon.user_prefs()
        props = prefs.operator.cycles
        box = self.layout.box()
        if self.use_HQ:
            row = box.row(align=True)
            row.prop(props, 'HQ_render_samples')
            row = box.row(align=True)
            row.prop(props, 'HQ_adaptive_threshold')
            row = box.row(align=True)
            row.prop(props, 'HQ_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'HQ_max_light_bounces')
        else:
            row = box.row(align=True)
            row.prop(props, 'LQ_render_samples')
            row = box.row(align=True)
            row.prop(props, 'LQ_adaptive_threshold')
            row = box.row(align=True)
            row.prop(props, 'LQ_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'LQ_max_light_bounces')