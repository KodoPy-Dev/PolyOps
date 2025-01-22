########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils

DESC = """EEVEE Settings\n
• HQ (LMB)
\t\t→ High Quality Settings\n
• LQ (SHIFT)
\t\t→ Low Quality Settings\n"""

class PS_OT_EEVEE(bpy.types.Operator):
    bl_idname      = "ps.eevee_settings"
    bl_label       = "EEVEE Settings"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.render.has_multiple_engines


    def invoke(self, context, event):
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
        self.use_HQ = not event.shift
        return self.execute(context)


    def execute(self, context):
        prefs = utils.addon.user_prefs()
        props = prefs.operator.eevee
        eevee = context.scene.eevee
        render = context.scene.render
        if self.use_HQ:
            eevee.light_threshold = 0.01
            eevee.taa_samples = props.HQ_vp_samples
            eevee.use_taa_reprojection = props.HQ_vp_reprojection
            eevee.use_shadow_jitter_viewport = props.HQ_vp_jitter_shadows
            eevee.taa_render_samples = props.HQ_render_samples
            eevee.use_shadows = props.HQ_use_shadows
            eevee.shadow_ray_count = props.HQ_shadow_rays
            eevee.shadow_step_count = props.HQ_shadow_ray_steps
            eevee.use_volumetric_shadows = props.HQ_use_volumetric_shadows
            eevee.volumetric_shadow_samples = props.HQ_volumetric_shadow_steps
            eevee.shadow_resolution_scale = props.HQ_volumetric_shadow_res
            eevee.use_raytracing = props.HQ_use_raytracing
            eevee.ray_tracing_method = props.HQ_raytrace_method
            eevee.ray_tracing_options.resolution_scale = props.HQ_raytrace_scale
            eevee.ray_tracing_options.screen_trace_quality = props.HQ_raytrace_quality
            eevee.ray_tracing_options.use_denoise = props.HQ_use_denoise
            eevee.ray_tracing_options.denoise_spatial = props.HQ_denoise_spatial_reuse
            eevee.fast_gi_method = props.HQ_fast_gi_method
            eevee.fast_gi_resolution = props.HQ_fast_gi_resolution
            eevee.fast_gi_ray_count = props.HQ_fast_gi_ray_count
            eevee.fast_gi_step_count = props.HQ_fast_gi_step_count
            eevee.fast_gi_quality = props.HQ_fast_gi_quality
            eevee.volumetric_tile_size = props.HQ_volumetric_tile_size
            eevee.volumetric_samples = props.HQ_volumetric_samples
            eevee.volumetric_sample_distribution = props.HQ_volumetric_sample_distribution
            eevee.volumetric_ray_depth = props.HQ_volumetric_ray_depth
            render.use_high_quality_normals = props.HQ_use_high_quality_normals
            eevee.shadow_pool_size = props.HQ_shadow_pool_size
            eevee.gi_irradiance_pool_size = props.HQ_gi_irradiance_pool_size
            render.preview_pixel_size = props.HQ_preview_pixel_size
            render.compositor_precision = props.HQ_compositor_precision
            render.hair_type = props.HQ_hair_type
            render.hair_subdiv = props.HQ_hair_subdiv
        else:
            eevee.light_threshold = 0.01
            eevee.taa_samples = props.LQ_vp_samples
            eevee.use_taa_reprojection = props.LQ_vp_reprojection
            eevee.use_shadow_jitter_viewport = props.LQ_vp_jitter_shadows
            eevee.taa_render_samples = props.LQ_render_samples
            eevee.use_shadows = props.LQ_use_shadows
            eevee.shadow_ray_count = props.LQ_shadow_rays
            eevee.shadow_step_count = props.LQ_shadow_ray_steps
            eevee.use_volumetric_shadows = props.LQ_use_volumetric_shadows
            eevee.volumetric_shadow_samples = props.LQ_volumetric_shadow_steps
            eevee.shadow_resolution_scale = props.LQ_volumetric_shadow_res
            eevee.use_raytracing = props.LQ_use_raytracing
            eevee.ray_tracing_method = props.LQ_raytrace_method
            eevee.ray_tracing_options.resolution_scale = props.LQ_raytrace_scale
            eevee.ray_tracing_options.screen_trace_quality = props.LQ_raytrace_quality
            eevee.ray_tracing_options.use_denoise = props.LQ_use_denoise
            eevee.ray_tracing_options.denoise_spatial = props.LQ_denoise_spatial_reuse
            eevee.fast_gi_method = props.LQ_fast_gi_method
            eevee.fast_gi_resolution = props.LQ_fast_gi_resolution
            eevee.fast_gi_ray_count = props.LQ_fast_gi_ray_count
            eevee.fast_gi_step_count = props.LQ_fast_gi_step_count
            eevee.fast_gi_quality = props.LQ_fast_gi_quality
            eevee.volumetric_tile_size = props.LQ_volumetric_tile_size
            eevee.volumetric_samples = props.LQ_volumetric_samples
            eevee.volumetric_sample_distribution = props.LQ_volumetric_sample_distribution
            eevee.volumetric_ray_depth = props.LQ_volumetric_ray_depth
            render.use_high_quality_normals = props.LQ_use_high_quality_normals
            eevee.shadow_pool_size = props.LQ_shadow_pool_size
            eevee.gi_irradiance_pool_size = props.LQ_gi_irradiance_pool_size
            render.preview_pixel_size = props.LQ_preview_pixel_size
            render.compositor_precision = props.LQ_compositor_precision
            render.hair_type = props.LQ_hair_type
            render.hair_subdiv = props.LQ_hair_subdiv

        msgs = [
            ("Engine", "EEVEE : HQ" if self.use_HQ else "EEVEE : LQ"),
            ("Raytracing", "On" if eevee.use_raytracing else "Off")]
        utils.notifications.init(context, messages=msgs)

        return {'FINISHED'}


    def draw(self, context):
        prefs = utils.addon.user_prefs()
        props = prefs.operator.eevee
        box = self.layout.box()

        if self.use_HQ:
            row = box.row(align=True)
            row.prop(props, 'HQ_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'HQ_vp_reprojection')
            row = box.row(align=True)
            row.prop(props, 'HQ_vp_jitter_shadows')
            row = box.row(align=True)
            row.prop(props, 'HQ_render_samples')
            row = box.row(align=True)
            row.prop(props, 'HQ_use_shadows')
            row = box.row(align=True)
            row.prop(props, 'HQ_shadow_rays')
            row = box.row(align=True)
            row.prop(props, 'HQ_shadow_ray_steps')
            row = box.row(align=True)
            row.prop(props, 'HQ_use_volumetric_shadows')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_shadow_steps')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_shadow_res')
            row = box.row(align=True)
            row.prop(props, 'HQ_use_raytracing')
            row = box.row(align=True)
            row.prop(props, 'HQ_raytrace_method')
            row = box.row(align=True)
            row.prop(props, 'HQ_raytrace_scale')
            row = box.row(align=True)
            row.prop(props, 'HQ_raytrace_quality')
            row = box.row(align=True)
            row.prop(props, 'HQ_use_denoise')
            row = box.row(align=True)
            row.prop(props, 'HQ_denoise_spatial_reuse')
            row = box.row(align=True)
            row.prop(props, 'HQ_fast_gi_method')
            row = box.row(align=True)
            row.prop(props, 'HQ_fast_gi_resolution')
            row = box.row(align=True)
            row.prop(props, 'HQ_fast_gi_ray_count')
            row = box.row(align=True)
            row.prop(props, 'HQ_fast_gi_step_count')
            row = box.row(align=True)
            row.prop(props, 'HQ_fast_gi_quality')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_tile_size')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_samples')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_sample_distribution')
            row = box.row(align=True)
            row.prop(props, 'HQ_volumetric_ray_depth')
            row = box.row(align=True)
            row.prop(props, 'HQ_use_high_quality_normals')
            row = box.row(align=True)
            row.prop(props, 'HQ_shadow_pool_size')
            row = box.row(align=True)
            row.prop(props, 'HQ_gi_irradiance_pool_size')
            row = box.row(align=True)
            row.prop(props, 'HQ_preview_pixel_size')
            row = box.row(align=True)
            row.prop(props, 'HQ_compositor_precision')
            row = box.row(align=True)
            row.prop(props, 'HQ_hair_type')
            row = box.row(align=True)
            row.prop(props, 'HQ_hair_subdiv')
        else:
            row = box.row(align=True)
            row.prop(props, 'LQ_vp_samples')
            row = box.row(align=True)
            row.prop(props, 'LQ_vp_reprojection')
            row = box.row(align=True)
            row.prop(props, 'LQ_vp_jitter_shadows')
            row = box.row(align=True)
            row.prop(props, 'LQ_render_samples')
            row = box.row(align=True)
            row.prop(props, 'LQ_use_shadows')
            row = box.row(align=True)
            row.prop(props, 'LQ_shadow_rays')
            row = box.row(align=True)
            row.prop(props, 'LQ_shadow_ray_steps')
            row = box.row(align=True)
            row.prop(props, 'LQ_use_volumetric_shadows')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_shadow_steps')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_shadow_res')
            row = box.row(align=True)
            row.prop(props, 'LQ_use_raytracing')
            row = box.row(align=True)
            row.prop(props, 'LQ_raytrace_method')
            row = box.row(align=True)
            row.prop(props, 'LQ_raytrace_scale')
            row = box.row(align=True)
            row.prop(props, 'LQ_raytrace_quality')
            row = box.row(align=True)
            row.prop(props, 'LQ_use_denoise')
            row = box.row(align=True)
            row.prop(props, 'LQ_denoise_spatial_reuse')
            row = box.row(align=True)
            row.prop(props, 'LQ_fast_gi_method')
            row = box.row(align=True)
            row.prop(props, 'LQ_fast_gi_resolution')
            row = box.row(align=True)
            row.prop(props, 'LQ_fast_gi_ray_count')
            row = box.row(align=True)
            row.prop(props, 'LQ_fast_gi_step_count')
            row = box.row(align=True)
            row.prop(props, 'LQ_fast_gi_quality')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_tile_size')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_samples')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_sample_distribution')
            row = box.row(align=True)
            row.prop(props, 'LQ_volumetric_ray_depth')
            row = box.row(align=True)
            row.prop(props, 'LQ_use_high_quality_normals')
            row = box.row(align=True)
            row.prop(props, 'LQ_shadow_pool_size')
            row = box.row(align=True)
            row.prop(props, 'LQ_gi_irradiance_pool_size')
            row = box.row(align=True)
            row.prop(props, 'LQ_preview_pixel_size')
            row = box.row(align=True)
            row.prop(props, 'LQ_compositor_precision')
            row = box.row(align=True)
            row.prop(props, 'LQ_hair_type')
            row = box.row(align=True)
            row.prop(props, 'LQ_hair_subdiv')
