########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from math import cos, sin, radians, degrees
from bpy.props import EnumProperty, BoolProperty
from ... import utils

DESC = """Select Objects\n
• (LMB)
\t\t→ Children + Parents + Modifier Objects (All)\n
• (SHIFT)
\t\t→ Modifier Objects\n
• (CTRL)
\t\t→ Children\n
• (SHIFT + CTRL)
\t\t→ Children + Parents"""

class PS_OT_SelectObjects(bpy.types.Operator):
    bl_idname      = "ps.select_objects"
    bl_label       = "Select Objects"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    select_opts = (
        ('CHILD'       , "Children", ""),
        ('CHILD_PARENT', "Children + Parents", ""),
        ('MOD_OBJECTS' , "Modifier Objects", ""),
        ('ALL'         , "Children + Parents + Modifier Objects", ""),
    )
    selection_opt : EnumProperty(name="Select Option", items=select_opts, description="Settings for the selection", default='CHILD')
    deselect_original_selection : BoolProperty(name="Deselect Original Selection", default=False)

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects_selected_or_in_mode(context)


    def invoke(self, context, event):
        if event.shift and event.ctrl:
            self.selection_opt = 'CHILD_PARENT'
        elif event.shift:
            self.selection_opt = 'MOD_OBJECTS'
        elif event.ctrl:
            self.selection_opt = 'CHILD'
        else:
            self.selection_opt = 'ALL'
        return self.execute(context)


    def execute(self, context):
        selected_objs = utils.context.get_objects_selected_or_in_mode(context)
        found_objs = set()
        for obj in selected_objs:
            found_objs.add(obj)
            if self.selection_opt == 'CHILD':
                found_objs.update(utils.object.obj_children(obj))
            elif self.selection_opt == 'CHILD_PARENT':
                found_objs.update(utils.object.objs_parents_and_children(obj))
            elif self.selection_opt == 'MOD_OBJECTS':
                found_objs.update(utils.modifiers.referenced_objects(obj))
            elif self.selection_opt == 'ALL':
                found_objs.update(utils.modifiers.referenced_objects(obj))
                selected = utils.object.objs_parents_and_children(obj)
                if selected:
                    found_objs.update(selected)
                    for selected_obj in selected:
                        found_objs.update(utils.modifiers.referenced_objects(selected_obj))
        for obj in found_objs:
            if not obj.visible_get(view_layer=context.view_layer):
                utils.collections.ensure_object_collections_visible(context, obj)
                obj.hide_set(False)
            obj.select_set(True)
        if self.deselect_original_selection:
            for obj in selected_objs:
                obj.select_set(False, view_layer=context.view_layer)
        msgs = []
        if self.selection_opt == 'CHILD':
            msgs.append(("Selection", "Children"))
        elif self.selection_opt == 'CHILD_PARENT':
            msgs.append(("Selection", "Children + Parents"))
        elif self.selection_opt == 'MOD_OBJECTS':
            msgs.append(("Selection", "Modifier Objects"))
        elif self.selection_opt == 'ALL':
            msgs.append(("Selection", "Children + Parents + Modifier Objects"))
        msgs.append(("Objects", str(len(found_objs))))
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'selection_opt', text="")
        row = box.row()
        row.prop(self, 'deselect_original_selection')

