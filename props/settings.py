########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty


def update_hotkeys(self, context):
    from ..registration import unregister_keymaps, register_keymaps
    unregister_keymaps()
    register_keymaps()


class PS_PROPS_Settings(PropertyGroup):
    main_menu_hotkey_opts = (
        ('Q', "Q", ""),
        ('W', "W", ""),
        ('Y', "Y", ""),
    )
    main_menu_hot_key : EnumProperty(name="Main Menu Hotkey", items=main_menu_hotkey_opts, default='Q', update=update_hotkeys)
    display_notify : BoolProperty(name="Display Notifications", default=True)
    notify_duration : FloatProperty(name="Notify Duration", default=5.0, min=1.0, max=30.0)
    mesh_fade_geo_limit : IntProperty(name="Mesh Fade Geo Limit", description="Don't display mesh fade if geometry is to high", default=10_000, min=0)
    mesh_fade_duration : FloatProperty(name="Mesh Fade Duration", default=0.875, min=0.125, max=6.0)
    destructive_mode : BoolProperty(name="Destructive Mode", default=False)
    del_booleans_if_destructive : BoolProperty(name="Delete Booleans if Destructive", default=False)
    boolean_solver_opts = (
        ('EXACT', "EXACT", ""),
        ('FAST', "FAST", ""),
    )
    boolean_solver_mode : EnumProperty(name="Boolean Solver", items=boolean_solver_opts, default='FAST')
    display_virtual_keyboard : BoolProperty(name="Virtual Keyboard", default=True)
    undo_limit : IntProperty(name="Undo Limit", description="Max mesh copies that can be saved in RAM during mesh editing tools\n(The tools delete the data on modal exit)", default=12, min=2, max=32)
    poly_debug_display_limit : IntProperty(name="Poly Debug Display Limit", description="Omit Object from Poly Debug when the Polygon Count is reached", default=1500, min=100)
    show_modal_help : BoolProperty(name="Show Modal Help", default=False)
