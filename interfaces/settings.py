########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.props import EnumProperty
from ..resources.icon import icon_id
from ..utils.addon import user_prefs, version
from ..utils.screen import screen_factor

DESC = """Settings Menu\n
(LMB)
\t\t→ Opens General Tab\n
(SHIFT)
\t\t→ Opens Object Tab\n
(CTRL)
\t\t→ Opens Sorting Tab"""

class PS_OT_SettingsPopup(bpy.types.Operator):
    bl_idname      = "ps.settings_popup"
    bl_label       = "Settings Menu"
    bl_description = DESC

    popup_tab_opts = (
        ('GENERAL', "General", ""),
        ('OBJECT', "Object", ""),
        ('SORTING', "Sorting", ""),
    )
    popup_tabs: EnumProperty(name="popup_tabs", items=popup_tab_opts, default='GENERAL')

    sort_tab_opts = (
        ('TOP', "Top", ""),
        ('MIDDLE', "Middle", ""),
        ('BOTTOM', "Bottom", ""),
    )
    sort_tabs: EnumProperty(name="sort_tabs", items=sort_tab_opts, default='TOP')

    msgs_001 = [
        "Modifiers that unsorted booleans should sort to",
        "This is for Modifiers *AFTER* the top sort",
        "If a boolean is below all of these types",
        "It will place it above the first one it finds"]
    msgs_002 = [
        "Sort these types to the bottom",
        "This is for Modifiers *AFTER* the top sort",
        "Booleans will be sorted above these types",
        "It only uses the *LAST* one from the stack",
        "Example : If you have 3 Mirror Modifiers",
        "If 1 sorts TOP and 1 sorts BOTTOM",
        "The MIDDLE Mirror Modifier wont be sorted"]

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        self.prefs = user_prefs()
        self.popup_tabs = 'GENERAL'
        if event.shift:
            self.popup_tabs = 'OBJECT'
        elif event.ctrl:
            self.popup_tabs = 'SORTING'
        return context.window_manager.invoke_popup(self, width=300)


    def execute(self, context):
        return {'FINISHED'}


    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.label(text=version(as_label=True))
        row = layout.row(align=True)
        row.prop(self, 'popup_tabs', expand=True)

        if self.popup_tabs == 'GENERAL':
            self.general_settings(context, layout)
        elif self.popup_tabs == 'OBJECT':
            self.object_settings(context, layout)
        elif self.popup_tabs == 'SORTING':
            self.sorting_rules(context, layout)


    def general_settings(self, context, layout):
        row = layout.row(align=True)
        row.label(text="Work Flow", icon='TOOL_SETTINGS')
        settings = self.prefs.settings
        # ------------------------ BOOLEANS ------------------------ #
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Booleans", icon='MOD_BOOLEAN')
        row = box.row(align=True)
        row.prop(settings, 'destructive_mode')
        if settings.destructive_mode:
            row = box.row(align=True)
            row.prop(settings, 'del_booleans_if_destructive')
        row = box.row(align=True)
        row.prop(settings, 'boolean_solver_mode', text="")
        # ------------------------ SYSTEMS ------------------------ #
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Tools", icon='EXPERIMENTAL')
        row = box.row(align=True)
        row.prop(settings, 'undo_limit')
        row = box.row(align=True)
        row.prop(settings, 'mesh_fade_geo_limit')
        row = box.row(align=True)
        row.prop(settings, 'poly_debug_display_limit')
        # ------------------------ MIRROR AND WELD ------------------------ #
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Mirror and Weld", icon_value=icon_id("mirror_and_weld"))
        row = box.row(align=True)
        row.prop(self.prefs.operator.mirror_and_weld, 'tool', text="")
        # ------------------------ DEVELOPMENT ------------------------ #
        dev = self.prefs.dev
        box = layout.box()
        row = box.row(align=True)
        row.label(text="Developer Mode", icon='FILE_SCRIPT')
        row.prop(dev, 'debug_mode', text='',)
        if dev.debug_mode:
            row = box.row(align=True)
            row.prop(dev, 'data_write_type', text='Writer')


    def object_settings(self, context, layout):
        obj = context.active_object
        layout.label(text="Current Active Object", icon='MESH_CUBE')
        row = layout.row(align=True)
        if context.active_object:
            row.label(text=f"→ {obj.name}")
        else:
            row.label(text="No Active Object")
            return
        if obj.type in {'MESH', 'CURVE'}:
            box = layout.box()
            row = box.row(align=True)
            row.prop(obj, 'show_wire', text="Show Wire")
            row = box.row(align=True)
            row.prop(obj, 'display_type', text="")


    def sorting_rules(self, context, layout):
        options = self.prefs.sort
        # ------------------------ HEADER ------------------------ #
        box = layout.box()
        row = box.row(align=True)
        row.prop(options, 'sort_enabled', text="Sort On" if options.sort_enabled else "Sort Off")
        row.prop(self, 'sort_tabs', expand=True)
        if not options.sort_enabled:
            return
        row = box.row(align=True)
        row.prop(options, 'ignore_sort_str', text="Ignore")
        # ------------------------ TOP ------------------------ #
        if self.sort_tabs == 'TOP':
            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_mirror', text="Mirror")
            row.label(text="", icon='MOD_MIRROR')
            if options.top_mirror:
                row = box.row(align=True)
                row.prop(options, 'top_mirror_check_no_bisect', text="Check No Bisect")
                row.prop(options, 'top_mirror_check_no_object', text="Check No Object")
                row = box.row(align=True)
                row.prop(options, 'top_mirror_count', text="Sort Limit")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_bevel', text="Bevel")
            row.label(text="", icon='MOD_BEVEL')
            if options.top_bevel:
                row = box.row(align=True)
                row.prop(options, 'top_bevel_require_vgroup', text="V-Group")
                row.prop(options, 'top_bevel_count', text="Sort Limit")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_solidify', text="Solidify")
            row.label(text="", icon='MOD_SOLIDIFY')
            if options.top_solidify:
                row = box.row(align=True)
                row.prop(options, 'top_solidify_require_vgroup', text="V-Group")
                row.prop(options, 'top_solidify_count', text="Sort Limit")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_deform', text="Simple Deform")
            row.label(text="", icon='MOD_SIMPLEDEFORM')
            if options.top_deform:
                row = box.row(align=True)
                row.prop(options, 'top_deform_require_vgroup', text="V-Group")
                row.prop(options, 'top_deform_count', text="Sort Limit")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_edge_split', text="Edge Split")
            row.label(text="", icon='MOD_EDGESPLIT')
            if options.top_edge_split:
                row = box.row(align=True)
                row.prop(options, 'top_edge_split_require_sharp', text="Edge Sharp")
                row.prop(options, 'top_edge_split_count', text="Sort Limit")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'top_subsurf', text="Sub-Surf")
            row.label(text="", icon='MOD_SUBSURF')
            if options.top_subsurf:
                row = box.row(align=True)
                row.prop(options, 'top_subsurf_count', text="Sort Limit")
        # ------------------------ MIDDLE ------------------------ #
        elif self.sort_tabs == 'MIDDLE':
            box = layout.box()
            for msg in self.msgs_001:            
                row = box.row(align=True)
                row.label(text=msg)
            row = box.row(align=True)
            row.prop(options, 'boolean_to_bevel', text="Bevel")
            row.prop(options, 'boolean_to_solidify', text="Solidify")
            row = box.row(align=True)
            row.prop(options, 'boolean_to_subsurf', text="SubSurf")
            row.prop(options, 'boolean_to_mirror', text="Mirror")
            row = box.row(align=True)
            row.prop(options, 'boolean_to_array', text="Array")
        # ------------------------ BOTTOM ------------------------ #
        elif self.sort_tabs == 'BOTTOM':
            box = layout.box()
            for msg in self.msgs_002:            
                row = box.row(align=True)
                row.label(text=msg)

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'bottom_mirror', text="Mirror")
            row.prop(options, 'bottom_weld', text="Weld")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'bottom_autosmooth', text="AutoSmooth")
            row.prop(options, 'bottom_weighted_normal', text="Weighted Normal")

            box = layout.box()
            row = box.row(align=True)
            row.prop(options, 'bottom_array', text="Array")
            row.prop(options, 'bottom_deform', text="Deform")
            row.prop(options, 'bottom_triangulate', text="Triangulate")
