########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..utils.addon import user_prefs
from ..utils.screen import screen_factor

OPERATORS_EDIT_MODE = [
    # Select
    ('COL_SEL', 'UV_EDGESEL'    , 'ps.loop_select'),
    ('COL_SEL', 'EDGESEL'       , 'ps.select_mark'),
    ('COL_SEL', 'PIVOT_BOUNDBOX', 'ps.select_boundary'),
    # Edit
    ('COL_EDI', 'SCULPTMODE_HLT'  , 'ps.slice_and_knife'),
    ('COL_EDI', 'MESH_GRID'       , 'ps.clean_mesh'),
    ('COL_EDI', 'MOD_DISPLACE'    , 'ps.flatten'),
    ('COL_EDI', 'FACE_CORNER'     , 'ps.sharp_bevel'),
    ('COL_EDI', 'CON_TRACKTO'     , 'ps.join'),
    ('COL_EDI', 'POINTCLOUD_POINT', 'ps.merge'),
    ('COL_EDI', 'MOD_SIMPLIFY'    , 'ps.bisect_loop'),
    ('COL_EDI', 'CON_STRETCHTO'   , 'ps.dissolve'),
    # Mark
    ('COL_MAR', 'EDGESEL'    , 'ps.edge_mark'),
    ('COL_MAR', 'VERTEXSEL'  , 'ps.vert_mark'),
    ('COL_MAR', 'IMAGE_ALPHA', 'ps.poly_debug'),
]

OPERATORS_OBJECT_MODE = [
    # Select
    ('COL_SEL', 'UV_EDGESEL' , 'ps.select_objects'),
    ('COL_SEL', 'MOD_BOOLEAN', 'ps.select_booleans'),
    # Edit
    ('COL_EDI', 'SCULPTMODE_HLT'  , 'ps.slice_and_knife'),
    ('COL_EDI', 'MESH_GRID'       , 'ps.clean_mesh'),
    ('COL_EDI', 'MOD_BEVEL'       , 'ps.bevel'),
    ('COL_EDI', 'MOD_SOLIDIFY'    , 'ps.solidify'),
    ('COL_EDI', 'MOD_SIMPLEDEFORM', 'ps.deform'),
    # Mark
    ('COL_MAR', 'MESH_CUBE'  , 'ps.obj_shade'),
    ('COL_MAR', 'EDGESEL'    , 'ps.edge_mark'),
    ('COL_MAR', 'VERTEXSEL'  , 'ps.vert_mark'),
]

OPERATORS_RAZOR = [
    # Razor
    ('COL_RAZ', 'SETTINGS'  , 'ps.razor_popup'),
    # Select
    ('COL_SEL', 'MOD_BOOLEAN', 'ps.select_booleans'),
    # Edit
    ('COL_EDI', 'MESH_GRID'   , 'ps.clean_mesh'),
    ('COL_EDI', 'MOD_BEVEL'   , 'ps.bevel'),
    ('COL_EDI', 'MOD_SOLIDIFY', 'ps.solidify'),
    # Mark
    ('COL_MAR', 'MESH_CUBE', 'ps.obj_shade'),
    ('COL_MAR', 'EDGESEL'  , 'ps.edge_mark'),
]

def get_operators(context):
    # razor = context.scene.razor
    # if razor.is_tool_active():
    #     global OPERATORS_RAZOR
    #     return OPERATORS_RAZOR
    if context.mode == 'EDIT_MESH':
        global OPERATORS_EDIT_MODE
        return OPERATORS_EDIT_MODE
    elif context.mode == 'OBJECT':
        global OPERATORS_OBJECT_MODE
        return OPERATORS_OBJECT_MODE
    return []


def get_icon_scale():
    return 15


def get_icon_offset():
    padding = user_prefs().drawing.padding
    icon_scale = get_icon_scale()
    factor = screen_factor()
    return (icon_scale * factor * 2) + (padding * factor)


def get_icon_row_width(context):
    return get_icon_offset() * (len(get_operators(context)) - 1)


def get_icon_row_location(context):
    prefs = user_prefs().hud_gizmos
    icon_scale = get_icon_scale()
    row_width = get_icon_row_width(context)
    horizontal = prefs.align_horizontal
    screen_padding = prefs.screen_padding

    area_w = context.area.width
    area_h = context.area.height
    x = prefs.offset_x
    y = prefs.offset_y

    if horizontal:
        x += (area_w - row_width) / 2
        if x + row_width + screen_padding > area_w:
            x = area_w - row_width - screen_padding

        y += area_h / 2
        if y + screen_padding > area_h:
            y = area_h - screen_padding

    else:
        x += (area_w / 2) - icon_scale
        if x + screen_padding > area_w:
            x = area_w - screen_padding

        y += (area_h - row_width) / 2
        if y + row_width + screen_padding > area_h:
            y = area_h - row_width - screen_padding

    x = screen_padding if x < screen_padding else x
    y = screen_padding if y < screen_padding else y
    return horizontal, x, y


class PS_GIZMO_HUD(bpy.types.GizmoGroup):
    bl_idname = "PS_GIZMO_HUD"
    bl_label = "PolyOps HUD Gizmos"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {'PERSISTENT', 'SCALE', 'EXCLUDE_MODAL'}
    RECALC = True

    @classmethod
    def poll(cls, context):
        return context.mode in {'EDIT_MESH', 'OBJECT'} and user_prefs().hud_gizmos.show_gizmos


    def setup(self, context):
        self.gizmos.clear()
        self.refresh(context)


    def refresh(self, context):
        # self.razor = context.scene.razor
        # self.razor_tool_active_state = self.razor.is_tool_active()

        self.mode = context.mode
        self.gizmos.clear()
        icon_scale = get_icon_scale()
        prefs = user_prefs().hud_gizmos
        for color_type, icon, operator in get_operators(context):
            gizmo = self.gizmos.new("GIZMO_GT_button_2d")
            gizmo.draw_options = {'BACKDROP', 'OUTLINE'}
            gizmo.icon = icon
            gizmo.scale_basis = icon_scale
            gizmo.target_set_operator(operator)
            gizmo.use_tooltip = True
            gizmo.show_drag = False
            gizmo.use_draw_value = True
            if color_type == 'COL_SEL':
                gizmo.color = prefs.select_color
                gizmo.color_highlight = prefs.select_color
            elif color_type == 'COL_EDI':
                gizmo.color = prefs.edit_color
                gizmo.color_highlight = prefs.edit_color
            elif color_type == 'COL_MAR':
                gizmo.color = prefs.marks_color
                gizmo.color_highlight = prefs.marks_color
            elif color_type == 'COL_RAZ':
                gizmo.color = prefs.razor_color
                gizmo.color_highlight = prefs.razor_color
            gizmo.alpha = .875
            gizmo.alpha_highlight = 0.5
            gizmo.use_grab_cursor = False


    def draw_prepare(self, context):
        # if self.razor.ops.active:
        #     for gizmo in self.gizmos:
        #         gizmo.hide = True
        #     return

        if PS_GIZMO_HUD.RECALC:
            PS_GIZMO_HUD.RECALC = False
            self.setup(context)
        if self.mode != context.mode:
            self.setup(context)

        # if self.razor_tool_active_state != self.razor.is_tool_active():
        #     self.setup(context)

        icon_scale = get_icon_scale()
        icon_offset = get_icon_offset()
        horizontal, x, y = get_icon_row_location(context)
        for gizmo in self.gizmos:
            gizmo.hide = False
            gizmo.scale_basis = icon_scale
            gizmo.matrix_basis[0][3] = x
            gizmo.matrix_basis[1][3] = y
            if horizontal:
                x += icon_offset
            else:
                y += icon_offset
