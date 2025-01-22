########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty, FloatVectorProperty


class PS_PROPS_Drawing(PropertyGroup):
    
    # --- PAD --- #
    padding: IntProperty(
        name="UI Padding", description="UI Padding",
        min=3, max=10, default=6)
    screen_padding: IntProperty(
        name="Screen Padding", description="Panel offset from screen boundary",
        min=15, max=150, default=24)
    slide_menu_padding: IntProperty(
        name="Slide Menu Padding", description="Slide Menu Padding",
        min=64, default=64)

    # --- FONT --- #
    font_size: IntProperty(
        name="Font Size", description="Font Size",
        min=10, max=32, default=12)
    font_primary_color: FloatVectorProperty(
        name="Font Primary Color", description="Font Primary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(1, 1, 1, 1))
    font_secondary_color: FloatVectorProperty(
        name="Font Secondary Color", description="Font Secondary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(.25, 1, .25, 1))
    font_tertiary_color: FloatVectorProperty(
        name="Font Tertiary Color", description="Font Tertiary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(1, 1, .25, 1))

    # --- BACKGROUND --- #
    background_color: FloatVectorProperty(
        name="Background Color", description="Background Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0, 0, 0, 0.875))
    background_highlight_color: FloatVectorProperty(
        name="Background Highlight Color", description="Background Highlight Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0, 0, 0, 1))
    background_submenu_color: FloatVectorProperty(
        name="Background SubMenu Color", description="Background SubMenu Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0.375, 0.375, 0.375, 0.375))

    # --- BORDER --- #
    border_primary_color: FloatVectorProperty(
        name="Border Primary Color", description="Border Primary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0, 0, 0, 1))
    border_secondary_color: FloatVectorProperty(
        name="Border Secondary Color", description="Border Secondary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0.800662, 0.159738, 0, 1))
    border_tertiary_color: FloatVectorProperty(
        name="Border Tertiary Color", description="Border Tecondary Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(.8, .5, 0, 1))

    # --- SLIDER --- #
    slider_negative_color: FloatVectorProperty(
        name="Slider Negative Color", description="Slider Negative Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(0, 0, 0, 1))
    slider_positive_color: FloatVectorProperty(
        name="Slider Positive Color", description="Slider Positive Color",
        size=4, min=0, max=1,
        subtype='COLOR', default=(1, 1, 1, .75))
