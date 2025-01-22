########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
import traceback
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from . import controller
from . import graphics
from .... import utils

DESC = """Razor\n
• Mesh Drawing System
"""

class PS_OT_Razor(bpy.types.Operator):
    bl_idname      = "ps.razor_ops"
    bl_label       = "Razor"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    surface_type_opts = (
        ('NONE'     , "NONE"     , ""),
        ('WORKPLANE', "WORKPLANE", ""),
        ('OBJECT'   , "OBJECT"   , ""),
    )
    surface_type    : EnumProperty(name="Shape", items=surface_type_opts, default='NONE')
    workplane_uuid  : StringProperty(name="Workplane UUID", default="")
    object_name     : StringProperty(name="Object Name", default="")

    @classmethod
    def poll(cls, context):
        razor = context.scene.razor
        if razor.ops.active:
            return False
        if razor.is_tool_active():
            return True
        return False


    def invoke(self, context, event):
        # Clean
        utils.modal_ops.reset_and_clear_handles()
        razor = context.scene.razor
        razor.ops.reset()

        # Controller
        try: controller.setup(context, event, self)
        except Exception as e:
            traceback.print_exc()
            self.exit_modal(context)
            return {'CANCELLED'}

        # Error
        if razor.ops.status != 'RUNNING':
            razor.ops.status = 'ERROR'
            self.exit_modal(context)
            return {'CANCELLED'}

        # Graphics
        graphics.register_shader_handles()
        graphics.setup_help_panel()
        graphics.setup_status_panel()

        # Panels
        utils.context.hide_3d_panels(context)

        # Modal
        razor.ops.active = True
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}


    def modal(self, context, event):
        # Update
        razor = context.scene.razor
        try: controller.update(context, event, self)
        except Exception as e:
            traceback.print_exc()
            razor.ops.status = 'ERROR'
            self.exit_modal(context)
            return {'CANCELLED'}

        # Catch Error / Cancelled
        if razor.ops.status in {'ERROR', 'CANCELLED'}:
            self.exit_modal(context)
            return {'CANCELLED'}
        # Finished
        elif razor.ops.status == 'FINISHED':
            self.exit_modal(context)
            return {'FINISHED'}
        # View Movement
        elif razor.ops.status == 'PASS_THROUGH':
            context.area.tag_redraw()
            return {'PASS_THROUGH'}

        context.area.tag_redraw()
        return {"RUNNING_MODAL"}


    def exit_modal(self, context):

        # Shader Handles
        graphics.unregister_shader_handles()

        # Controller
        try: controller.exit_modal(context)
        except Exception as e:
            traceback.print_exc()

        # Razor
        razor = context.scene.razor
        razor.ops.active = False
        status = razor.ops.status
        razor.ops.status = 'FINISHED'

        # Modal
        self.surface_type = 'NONE'
        self.workplane_index = 0
        self.object_name = ""

        # Panels
        utils.context.restore_3d_panels(context)

        # Redraw
        context.area.tag_redraw()

        # Data
        gc.collect()

        # Notify
        if status == 'ERROR':
            utils.notifications.init(context, messages=[("Operation", "Error")])
        elif status == 'CANCELLED':
            utils.notifications.init(context, messages=[("Operation", "Cancelled")])
        elif status == 'FINISHED':
            utils.notifications.init(context, messages=[("Operation", "Completed")])
