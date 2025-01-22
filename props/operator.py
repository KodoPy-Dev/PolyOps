########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from math import radians, pi
from bpy.types import PropertyGroup
from bpy.props import PointerProperty, BoolProperty, FloatProperty, EnumProperty, IntProperty, FloatVectorProperty, StringProperty


class PS_PROPS_EEVEE(PropertyGroup):

    HQ_vp_samples: IntProperty(name="HQ Viewport Samples", min=1, default=26)
    LQ_vp_samples: IntProperty(name="LQ Viewport Samples", min=1, default=8)

    HQ_vp_reprojection: BoolProperty(name="HQ Viewport Temporal Reprojection", default=True)
    LQ_vp_reprojection: BoolProperty(name="LQ Viewport Temporal Reprojection", default=False)

    HQ_vp_jitter_shadows: BoolProperty(name="HQ Viewport Jitter Shadows", default=True)
    LQ_vp_jitter_shadows: BoolProperty(name="LQ Viewport Jitter Shadows", default=False)

    HQ_render_samples: IntProperty(name="HQ Render Samples", min=1, default=124)
    LQ_render_samples: IntProperty(name="LQ Render Samples", min=1, default=16)

    HQ_use_shadows: BoolProperty(name="HQ Use Shadows", default=True)
    LQ_use_shadows: BoolProperty(name="LQ Use Shadows", default=False)

    HQ_shadow_rays: IntProperty(name="HQ Shadow Rays", min=1, default=3)
    LQ_shadow_rays: IntProperty(name="LQ Shadow Rays", min=1, default=1)

    HQ_shadow_ray_steps: IntProperty(name="HQ Shadow Ray Steps", min=1, default=10)
    LQ_shadow_ray_steps: IntProperty(name="LQ Shadow Ray Steps", min=1, default=3)

    HQ_use_volumetric_shadows: BoolProperty(name="HQ Use Volumetric Shadows", default=True)
    LQ_use_volumetric_shadows: BoolProperty(name="LQ Use Volumetric Shadows", default=False)

    HQ_volumetric_shadow_steps: IntProperty(name="HQ Volumetric Shadow Steps", min=1, default=18)
    LQ_volumetric_shadow_steps: IntProperty(name="LQ Volumetric Shadow Steps", min=1, default=6)

    HQ_volumetric_shadow_res: FloatProperty(name="HQ Volumetric Shadow Resolution", min=0, max=1.0, default=.75)
    LQ_volumetric_shadow_res: FloatProperty(name="LQ Volumetric Shadow Resolution", min=0, max=1.0, default=0.25)

    HQ_use_raytracing: BoolProperty(name="HQ Use Raytracing", default=True)
    LQ_use_raytracing: BoolProperty(name="LQ Use Raytracing", default=False)

    trace_method_opts = (
        ('PROBE', "PROBE", ""),
        ('SCREEN', "SCREEN", ""),
    )
    HQ_raytrace_method: EnumProperty(name="HQ Raytrace Method", items=trace_method_opts, default='SCREEN')
    LQ_raytrace_method: EnumProperty(name="LQ Raytrace Method", items=trace_method_opts, default='PROBE')

    trace_scale_opts = (
        ('1', "1", ""),
        ('2', "2", ""),
        ('4', "4", ""),
        ('8', "8", ""),
        ('16', "16", ""),
    )
    HQ_raytrace_scale: EnumProperty(name="HQ Ray Trace Scale", items=trace_scale_opts, default='1')
    LQ_raytrace_scale: EnumProperty(name="LQ Ray Trace Scale", items=trace_scale_opts, default='16')

    HQ_raytrace_quality: FloatProperty(name="HQ Raytrace Quality", min=0, max=1.0, default=1.0)
    LQ_raytrace_quality: FloatProperty(name="LQ Raytrace Quality", min=0, max=1.0, default=0.25)

    HQ_use_denoise: BoolProperty(name="HQ Use Denoise", default=True)
    LQ_use_denoise: BoolProperty(name="LQ Use Denoise", default=False)

    HQ_denoise_spatial_reuse: BoolProperty(name="HQ Denoise Spatial Reuse", default=False)
    LQ_denoise_spatial_reuse: BoolProperty(name="LQ Denoise Spatial Reuse", default=True)

    fast_gi_method_opts = (
        ('AMBIENT_OCCLUSION_ONLY', "AMBIENT_OCCLUSION_ONLY", ""),
        ('GLOBAL_ILLUMINATION', "GLOBAL_ILLUMINATION", ""),
    )
    HQ_fast_gi_method: EnumProperty(name="HQ Fast GI Method", items=fast_gi_method_opts, default='GLOBAL_ILLUMINATION')
    LQ_fast_gi_method: EnumProperty(name="LQ Fast GI Method", items=fast_gi_method_opts, default='AMBIENT_OCCLUSION_ONLY')

    fast_gi_resolution_opts = (
        ('1', "1", ""),
        ('2', "2", ""),
        ('4', "4", ""),
        ('8', "8", ""),
        ('16', "16", ""),
    )
    HQ_fast_gi_resolution: EnumProperty(name="HQ Fast GI Resolution", items=fast_gi_resolution_opts, default='1')
    LQ_fast_gi_resolution: EnumProperty(name="LQ Fast GI Resolution", items=fast_gi_resolution_opts, default='16')

    HQ_fast_gi_ray_count: IntProperty(name="HQ Fast GI Ray Count", min=1, max=16, default=3)
    LQ_fast_gi_ray_count: IntProperty(name="LQ Fast GI Ray Count", min=1, max=16, default=1)

    HQ_fast_gi_step_count: IntProperty(name="HQ Fast GI Step Count", min=1, max=64, default=12)
    LQ_fast_gi_step_count: IntProperty(name="LQ Fast GI Step Count", min=1, max=64, default=3)

    HQ_fast_gi_quality: FloatProperty(name="HQ Fast GI Precision", min=0, max=1.0, default=1.0)
    LQ_fast_gi_quality: FloatProperty(name="LQ Fast GI Precision", min=0, max=1.0, default=0.125)

    volumetric_tile_size_opts = (
        ('1', "1", ""),
        ('2', "2", ""),
        ('4', "4", ""),
        ('8', "8", ""),
        ('16', "16", ""),
    )
    HQ_volumetric_tile_size: EnumProperty(name="HQ Volumetric Tile Size", items=volumetric_tile_size_opts, default='8')
    LQ_volumetric_tile_size: EnumProperty(name="LQ Volumetric Tile Size", items=volumetric_tile_size_opts, default='16')

    HQ_volumetric_samples: IntProperty(name="HQ Volumetric Samples", min=1, max=256, default=64)
    LQ_volumetric_samples: IntProperty(name="HQ Volumetric Samples", min=1, max=256, default=32)

    HQ_volumetric_sample_distribution: FloatProperty(name="HQ Volumetric Sample Distribution", min=0, max=1.0, default=0.8)
    LQ_volumetric_sample_distribution: FloatProperty(name="LQ Volumetric Sample Distribution", min=0, max=1.0, default=1)

    HQ_volumetric_ray_depth: IntProperty(name="HQ Volumetric Ray Depth", min=1, max=16, default=12)
    LQ_volumetric_ray_depth: IntProperty(name="HQ Volumetric Ray Depth", min=1, max=16, default=8)

    HQ_use_high_quality_normals: BoolProperty(name="HQ High Quality Normals", default=True)
    LQ_use_high_quality_normals: BoolProperty(name="LQ High Quality Normals", default=False)

    shadow_pool_size_opts = (
        ('16', "16", ""),
        ('32', "32", ""),
        ('64', "64", ""),
        ('128', "128", ""),
        ('256', "256", ""),
        ('512', "512", ""),
        ('1024', "1024", ""),
    )
    HQ_shadow_pool_size: EnumProperty(name="HQ Shadow Pool Size", items=shadow_pool_size_opts, default='512')
    LQ_shadow_pool_size: EnumProperty(name="LQ Shadow Pool Size", items=shadow_pool_size_opts, default='128')

    gi_irradiance_pool_size_opts = (
        ('16', "16", ""),
        ('32', "32", ""),
        ('64', "64", ""),
        ('128', "128", ""),
        ('256', "256", ""),
        ('512', "512", ""),
        ('1024', "1024", ""),
    )
    HQ_gi_irradiance_pool_size: EnumProperty(name="HQ GI Irradiance Pool Size", items=gi_irradiance_pool_size_opts, default='64')
    LQ_gi_irradiance_pool_size: EnumProperty(name="LQ GI Irradiance Pool Size", items=gi_irradiance_pool_size_opts, default='16')

    preview_pixel_size_opts = (
        ('AUTO', "AUTO", ""),
        ('1', "1", ""),
        ('2', "2", ""),
        ('4', "4", ""),
        ('8', "8", ""),
    )
    HQ_preview_pixel_size: EnumProperty(name="HQ Preview Pixel Size", items=preview_pixel_size_opts, default='AUTO')
    LQ_preview_pixel_size: EnumProperty(name="LQ Preview Pixel Size", items=preview_pixel_size_opts, default='AUTO')

    compositor_precision_opts = (
        ('AUTO', "AUTO", ""),
        ('FULL', "FULL", ""),
    )
    HQ_compositor_precision: EnumProperty(name="HQ Compositor Precision", items=compositor_precision_opts, default='FULL')
    LQ_compositor_precision: EnumProperty(name="LQ Compositor Precision", items=compositor_precision_opts, default='AUTO')

    hair_type_opts = (
        ('STRIP', "STRIP", ""),
        ('STRAND', "STRAND", ""),
    )
    HQ_hair_type: EnumProperty(name="HQ Hair Type", items=hair_type_opts, default='STRIP')
    LQ_hair_type: EnumProperty(name="LQ Hair Type", items=hair_type_opts, default='STRIP')

    HQ_hair_subdiv: IntProperty(name="HQ Hair Subdiv", min=0, max=3, default=1)
    LQ_hair_subdiv: IntProperty(name="HQ Hair Subdiv", min=0, max=3, default=0)


class PS_PROPS_Cycles(PropertyGroup):

    HQ_render_samples: IntProperty(name="HQ Render Samples", min=1, default=800)
    LQ_render_samples: IntProperty(name="LQ Render Samples", min=1, default=150)

    HQ_vp_samples: IntProperty(name="HQ Viewport Samples", min=1, default=62)
    LQ_vp_samples: IntProperty(name="LQ Viewport Samples", min=1, default=16)

    HQ_max_light_bounces: IntProperty(name="HQ Max Light Bounces", min=1, default=16)
    LQ_max_light_bounces: IntProperty(name="LQ Max Light Bounces", min=1, default=6)

    HQ_adaptive_threshold: FloatProperty(name="HQ Adaptive threshold", min=0, max=1.0, default=0.01)
    LQ_adaptive_threshold: FloatProperty(name="LQ Adaptive threshold", min=0, max=1.0, default=0.05)


class PS_PROPS_Workbench(PropertyGroup):
    render_opts = (
        ('OFF',  'OFF', ""),
        ('FXAA',  'FXAA', ""),
        ('5',  '5', ""),
        ('8',  '8', ""),
        ('11',  '11', ""),
        ('16',  '16', ""),
        ('32',  '32', "")
    )
    PRESET_1_render_samples: EnumProperty(name="Render Samples", items=render_opts, default='32')
    PRESET_2_render_samples: EnumProperty(name="Render Samples", items=render_opts, default='FXAA')

    PRESET_1_vp_samples: EnumProperty(name="Viewport Samples", items=render_opts, default='32')
    PRESET_2_vp_samples: EnumProperty(name="Viewport Samples", items=render_opts, default='FXAA')

    color_opts = (
        ('MATERIAL', "MATERIAL", ""),
        ('OBJECT', "OBJECT", ""),
        ('VERTEX', "VERTEX", ""),
        ('SINGLE', "SINGLE", ""),
        ('RANDOM', "RANDOM", ""),
        ('TEXTURE', "TEXTURE", "")
    )
    PRESET_1_shading_color: EnumProperty(name="Shading Color", items=color_opts, default='MATERIAL')
    PRESET_2_shading_color: EnumProperty(name="Shading Color", items=color_opts, default='MATERIAL')

    PRESET_1_shadows: BoolProperty(name="Shadows", default=True)
    PRESET_2_shadows: BoolProperty(name="Shadows", default=True)

    PRESET_1_cavity: BoolProperty(name="Shadows", default=True)
    PRESET_2_cavity: BoolProperty(name="Shadows", default=True)


class PS_PROPS_SliceAndKnife(PropertyGroup):
    flip : BoolProperty(name="flip", default=False)
    mirror_x : BoolProperty(name="mirror_x", default=False)
    mirror_y : BoolProperty(name="mirror_y", default=False)
    mirror_z : BoolProperty(name="mirror_z", default=False)
    create_faces : BoolProperty(name="create_faces", default=True)
    only_selected : BoolProperty(name="only_selected", default=False)
    multi_mode : BoolProperty(name="multi_mode", default=False)
    cut_mode_opts = (
        ('Slice', "Slice", ""),
        ('Knife', "Knife", ""),
    )
    cut_mode : EnumProperty(name="cut_modes", items=cut_mode_opts, default='Slice')


class PS_PROPS_MirrorAndWeld(PropertyGroup):
    tool_opts = (
        ('SLICE_AND_WELD', "Slice & Weld (No Modifier)", ""),
        ('MIRROR_SEL_GEO', "Mirror Sel Geo (No Modifier)", ""),
        ('SLICE_AND_MIRROR', "Slice & Mirror (Adds Modifier)", ""),
        ('MIRROR_AND_BISECT', "Mirror & Bisect (Adds Modifier)", ""),
        ('MIRROR_OVER_CURSOR', "Mirror Over Cursor (Adds Modifier)", ""),
        ('MIRROR_OVER_ACTIVE', "Mirror Over Active (Adds Modifier)", ""),
    )
    tool: EnumProperty(name="tool", items=tool_opts, default='SLICE_AND_WELD')
    multi_obj_mode: BoolProperty(name="multi_obj_mode", default=False)


class PS_PROPS_LoopSelect(PropertyGroup):
    angle_limit : FloatProperty(name="angle_limit", default=radians(30), min=0, max=pi, subtype='ANGLE')
    step_limit : IntProperty(name="step_limit", min=1, default=70)
    break_at_boundary : BoolProperty(name="break_at_boundary", default=True)
    break_at_intersections : BoolProperty(name="break_at_intersections", default=True)


class PS_PROPS_BLoop(PropertyGroup):
    ray_mode : StringProperty(name='ray_mode', default='Edge')
    cut_through_mode : StringProperty(name='cut_through_mode', default='Island')
    edge_angle_mode : StringProperty(name='edge_angle_mode', default='Perpendicular')
    vert_angle_mode : StringProperty(name='vert_angle_mode', default='Adjacent-V')


class PS_PROPS_Merge(PropertyGroup):
    merge_mode : StringProperty(name='ray_mode', default='Radial')


class PS_PROPS_Operator(PropertyGroup):
    eevee : PointerProperty(type=PS_PROPS_EEVEE)
    cycles : PointerProperty(type=PS_PROPS_Cycles)
    workbench : PointerProperty(type=PS_PROPS_Workbench)
    slice_and_knife : PointerProperty(type=PS_PROPS_SliceAndKnife)
    mirror_and_weld : PointerProperty(type=PS_PROPS_MirrorAndWeld)
    loop_select : PointerProperty(type=PS_PROPS_LoopSelect)
    bloop : PointerProperty(type=PS_PROPS_BLoop)
    merge : PointerProperty(type=PS_PROPS_Merge)
