########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import gpu
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from .hud_gizmos import PS_GIZMO_HUD
from .. import utils
from ..utils.modal_status import MODAL_STATUS, UX_STATUS
from ..gizmos.hud_gizmos import get_operators, get_icon_offset, get_icon_scale, get_icon_row_width, get_icon_row_location
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Edit HUD Gizmos\n
• (LMB)
\t\t→ Turn On HUD Gizmos\n
• (SHIFT)
\t\t→ Turn Off HUD Gizmos\n
• (CTRL)
\t\t→ Adjust HUD Placement\n
• (ALT)
\t\t→ Turn On HUD Gizmos
\t\t→ Set Default Location\n
• TIP
\t\t→ Press (SHIFT + ALT + D) to toggle HUD
\t\t→ For use outside of modal!\n"""

class PS_OT_HudGizmosEditor(bpy.types.Operator):
    bl_idname      = "ps.hud_gizmos_editor"
    bl_label       = "HUD Gizmos Editor"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        # Gizmo Prefs
        self.prefs = utils.addon.user_prefs().hud_gizmos
        PS_GIZMO_HUD.RECALC = True
        # Turn Off
        if event.shift:
            self.prefs.show_gizmos = False
            context.area.tag_redraw()
            return {'FINISHED'}
        # Turn On & Default
        elif event.alt:
            bpy.context.space_data.show_gizmo = True
            self.prefs.show_gizmos = True
            self.prefs.align_horizontal = True
            self.prefs.offset_x = 0
            self.prefs.offset_y = 4000
            context.area.tag_redraw()
            return {'FINISHED'}
        # Turn On
        elif not event.ctrl:
            bpy.context.space_data.show_gizmo = True
            self.prefs.show_gizmos = True
            context.area.tag_redraw()
            return {'FINISHED'}
        # Icon Row Adjust
        self.prefs.show_gizmos = False
        self.icon_offset = get_icon_offset()
        self.icon_scale = get_icon_scale()
        self.icon_row_width = get_icon_row_width(context)
        self.icon_row_x = 0
        self.icon_row_y = 0
        self.is_horizontal = self.prefs.align_horizontal
        self.operators = get_operators(context)
        # Modal Setup
        self.setup_status_and_help_panels(context)
        utils.modal_ops.standard_modal_setup(self, context, event, utils)
        return {"RUNNING_MODAL"}


    def modal(self, context, event):
        except_guard_prop_set(self.update, (context, event), self, 'modal_status', MODAL_STATUS.ERROR)
        # Catch Error / Cancelled
        if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
            self.exit_modal(context)
            return {'CANCELLED'}
        # Finished
        if self.modal_status == MODAL_STATUS.CONFIRM:
            self.exit_modal(context)
            return {'FINISHED'}
        # View Movement
        if self.modal_status == MODAL_STATUS.PASS:
            context.area.tag_redraw()
            return {'PASS_THROUGH'}
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}


    def update(self, context, event):
        self.modal_status = MODAL_STATUS.RUNNING
        # Flip
        if event.type == 'V' and event.value == 'PRESS':
            self.is_horizontal = not self.is_horizontal
            self.prefs.align_horizontal = self.is_horizontal
        # View Movement
        if utils.event.pass_through(event, with_scoll=True, with_numpad=True, with_shading=True):
            self.modal_status = MODAL_STATUS.PASS
        # Finished
        elif utils.event.confirmed(event):
            self.modal_status = MODAL_STATUS.CONFIRM
        # Cancelled
        elif utils.event.cancelled(event):
            self.modal_status = MODAL_STATUS.CANCEL
        # Calc Offset
        self.prefs.offset_x = int(event.mouse_region_x) - int(context.area.width / 2)
        self.prefs.offset_y = int(event.mouse_region_y) - int(context.area.height / 2)
        self.is_horizontal, self.icon_row_x, self.icon_row_y = get_icon_row_location(context)


    def exit_modal(self, context):
        utils.modal_ops.standard_modal_shutdown(self, context, utils)
        bpy.context.space_data.show_gizmo = True
        self.prefs.show_gizmos = True
        context.area.tag_redraw()

    # --- SHADER --- #

    def draw_post_view(self, context):
        pass


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        x = self.icon_row_x
        y = self.icon_row_y
        center = Vector((x, y))
        for color_type, icon, operator in self.operators:
            color = (0,0,0)
            if color_type == 'COL_SEL':
                color = self.prefs.select_color
            elif color_type == 'COL_EDI':
                color = self.prefs.edit_color
            elif color_type == 'COL_MAR':
                color = self.prefs.marks_color
            elif color_type == 'COL_RAZ':
                color = self.prefs.razor_color
            color = (color[0], color[1], color[2], 0.75)
            utils.graphics.draw_rectangle_2d(width=self.icon_scale*2, height=self.icon_scale*2, center=center, poly_color=color, line_color=(0,0,0,1), line_width=1)
            if self.is_horizontal:
                center.x += self.icon_offset
            else:
                center.y += self.icon_offset

    # --- MENUS --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [
            ("LMB", "Finish"),
            ("RMB", "Cancel"),
            ("V"  , "Flip (Vertical / Horizontal)")]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)

