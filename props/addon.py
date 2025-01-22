########################•########################
"""                   KodoPy                  """
########################•########################

from bpy.types import AddonPreferences
from bpy.props import PointerProperty, EnumProperty
from ..utils.addon import addon_name, user_prefs
from .dev import PS_PROPS_Dev
from .drawing import PS_PROPS_Drawing
from .settings import PS_PROPS_Settings
from .sort import PS_PROPS_Sort
from .operator import PS_PROPS_Operator
from .gizmos import PS_PROPS_HUD_Gizmo


class PS_ADDON_Prefs(AddonPreferences):
    bl_idname = addon_name
    dev        : PointerProperty(type=PS_PROPS_Dev)
    drawing    : PointerProperty(type=PS_PROPS_Drawing)
    settings   : PointerProperty(type=PS_PROPS_Settings)
    sort       : PointerProperty(type=PS_PROPS_Sort)
    operator   : PointerProperty(type=PS_PROPS_Operator)
    hud_gizmos : PointerProperty(type=PS_PROPS_HUD_Gizmo)

    tab_opts = (
        ('SETTINGS' , "Settings" , ""),
        ('INTERFACE', "Interface", ""),
        ('GIZMO'    , "Gizmo"    , ""),
        ('INFO'     , "Info"     , ""),
    )
    tabs: EnumProperty(name="tabs", items=tab_opts, default='SETTINGS')

    def draw(self, context):
        layout = self.layout
        prefs = user_prefs()
        row = layout.row()
        row.prop(self, 'tabs', expand=True)
        if self.tabs == 'SETTINGS':
            draw_settings(context, layout, prefs)
        elif self.tabs == 'INTERFACE':
            draw_interface(context, layout, prefs)
        elif self.tabs == 'GIZMO':
            draw_gizmos(context, layout, prefs)
        elif self.tabs == 'INFO':
            draw_info(context, layout, prefs)


def draw_settings(context, layout, prefs):
    box = layout.box()
    box.label(text="Settings", icon='TOOL_SETTINGS')

    row = box.row(align=True)
    row.prop(prefs.settings, 'main_menu_hot_key')

    row = box.row(align=True)
    row.prop(prefs.settings, 'display_notify')

    row = box.row(align=True)
    row.label(text="Notification Duration in Seconds")
    row.prop(prefs.settings, 'notify_duration')

    row = box.row(align=True)
    row.label(text="Mesh Fade Geometry Limit")
    row.prop(prefs.settings, 'mesh_fade_geo_limit')

    row = box.row(align=True)
    row.label(text="Mesh Fade Duration in Seconds")
    row.prop(prefs.settings, 'mesh_fade_duration')

    row = box.row(align=True)
    row.label(text="Max polygon count for Poly Debug Display")
    row.prop(prefs.settings, 'poly_debug_display_limit')

    row = box.row(align=True)
    row.prop(prefs.settings, 'destructive_mode')

    if prefs.settings.destructive_mode:
        row = box.row(align=True)
        row.prop(prefs.settings, 'del_booleans_if_destructive')

    row = box.row(align=True)
    row.prop(prefs.settings, 'boolean_solver_mode')


def draw_interface(context, layout, prefs):
    box = layout.box()
    box.label(text="Interface", icon='COLOR')
    row = box.row(align=True)
    row.label(text="Screen Padding")
    row.prop(prefs.drawing, 'screen_padding', text="Screen Padding")
    row = box.row(align=True)
    row.label(text="UI Padding")
    row.prop(prefs.drawing, 'padding', text="Padding")
    row = box.row(align=True)
    row.label(text="Font Size")
    row.prop(prefs.drawing, 'font_size', text="Font Size")

    font_box = box.box()
    font_box.label(text="Font Colors")
    row = font_box.row(align=True)
    row.prop(prefs.drawing, 'font_primary_color', text="Primary")
    row = font_box.row(align=True)
    row.prop(prefs.drawing, 'font_secondary_color', text="Secondary")
    row = font_box.row(align=True)
    row.prop(prefs.drawing, 'font_tertiary_color', text="Tertiary")

    bg_box = box.box()
    bg_box.label(text="Background Colors")
    row = bg_box.row(align=True)
    row.prop(prefs.drawing, 'background_color', text="Primary")
    row = bg_box.row(align=True)
    row.prop(prefs.drawing, 'background_highlight_color', text="Highlight")
    row = bg_box.row(align=True)
    row.prop(prefs.drawing, 'background_submenu_color', text="Sub-Menu")

    border_box = box.box()
    border_box.label(text="Border Colors")
    row = border_box.row(align=True)
    row.prop(prefs.drawing, 'border_primary_color', text="Primary")
    row = border_box.row(align=True)
    row.prop(prefs.drawing, 'border_secondary_color', text="Secondary")
    row = border_box.row(align=True)
    row.prop(prefs.drawing, 'border_tertiary_color', text="Tertiary")

    slider_box = box.box()
    slider_box.label(text="Slider Colors")
    row = slider_box.row(align=True)
    row.prop(prefs.drawing, 'slider_negative_color', text="Negative")
    row = slider_box.row(align=True)
    row.prop(prefs.drawing, 'slider_positive_color', text="Positive")


def draw_gizmos(context, layout, prefs):
    box = layout.box()
    box.label(text="Gizmos", icon='ONIONSKIN_ON')

    hud_box = box.box()
    hud_box.label(text="HUD Colors")
    row = hud_box.row(align=True)
    row.prop(prefs.hud_gizmos, 'razor_color')
    row = hud_box.row(align=True)
    row.prop(prefs.hud_gizmos, 'select_color')
    row = hud_box.row(align=True)
    row.prop(prefs.hud_gizmos, 'edit_color')
    row = hud_box.row(align=True)
    row.prop(prefs.hud_gizmos, 'marks_color')


def draw_info(context, layout, prefs):
    box = layout.box()
    box.label(text="Info", icon='INFO')

    web_box = box.box()
    web_box.label(text="Web Pages", icon='WORLD')
    web_pages = [
        ("YouTube", "https://www.youtube.com/@KodoPy"),
        ("GumRoad", "https://kodopy.gumroad.com/l/PolyOps"),
    ]
    for page_name, page_link in web_pages:
        row = web_box.row(align=True)
        row.operator("wm.url_open", text=page_name).url = page_link

    email_box = box.box()
    row = email_box.row()
    row.label(text="Contact")
    row = email_box.row()
    row.label(text="kodopy.dev@gmail.com")

    hotkey_box = box.box()
    hotkey_box.label(text="Hot Keys", icon='KEYINGSET')
    msgs = [
        f"Main Menu ({prefs.settings.main_menu_hot_key})",
        "Mirror and Weld (ALT + X)",
        "Slice and Knife (SHIFT + ALT + X)",
        "HUD Gizmos Toggle (SHIFT + ALT + D)",
        "Boolean Difference (CTRL + Numpad Minus)",
        "Boolean Slice (CTRL + Numpad Slash)",
        "Boolean Union (CTRL + Numpad Plus)",
        "Boolean Intersect (CTRL + Numpad Asterix)",
        ]
    for msg in msgs:            
        row = hotkey_box.row(align=True)
        row.label(text=msg)
