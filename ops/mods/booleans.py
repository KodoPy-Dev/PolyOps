########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils

DESC_INTERSECT = """Boolean Intersect\n
• Subtract selected mesh(s) from the active object"""

DESC_SLICE = """Boolean Slice
• Create a difference object in place"""

DESC_UNION = """Boolean Union
• Join selected mesh(s) with the active object"""

DESC_DIFFERENCE = """Boolean Difference
• The intersection volume of the mesh(s) from the active object"""

class PS_OT_BooleanDifference(bpy.types.Operator):
    bl_idname      = "ps.boolean_difference"
    bl_label       = "Boolean Difference"
    bl_description = DESC_DIFFERENCE
    bl_options     = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True)


    def invoke(self, context, event):
        target = context.active_object
        booleans = utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True, exclude=[target])
        bool_ops = utils.modifiers.BOOLEAN_OPS
        utils.modifiers.boolean_operations(context, target, booleans, boolean_ops=bool_ops.DIFFERENCE)
        if not utils.modifiers.delete_booleans_if_valid(boolean_objs=booleans):
            set_boolean_to_active_object(context, target, booleans)
        bool_notify(context, booleans, op_name="Difference")
        return {'FINISHED'}


class PS_OT_BooleanSlice(bpy.types.Operator):
    bl_idname      = "ps.boolean_slice"
    bl_label       = "Boolean Slice"
    bl_description = DESC_SLICE
    bl_options     = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True)


    def invoke(self, context, event):
        target = context.active_object
        booleans = utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True, exclude=[target])
        bool_ops = utils.modifiers.BOOLEAN_OPS
        utils.modifiers.boolean_operations(context, target, booleans, boolean_ops=bool_ops.SLICE)
        if not utils.modifiers.delete_booleans_if_valid(boolean_objs=booleans):
            set_boolean_to_active_object(context, target, booleans)
        bool_notify(context, booleans, op_name="Slice")
        return {'FINISHED'}


class PS_OT_BooleanUnion(bpy.types.Operator):
    bl_idname      = "ps.boolean_union"
    bl_label       = "Boolean Union"
    bl_description = DESC_UNION
    bl_options     = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True)


    def invoke(self, context, event):
        target = context.active_object
        booleans = utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True, exclude=[target])
        bool_ops = utils.modifiers.BOOLEAN_OPS
        utils.modifiers.boolean_operations(context, target, booleans, boolean_ops=bool_ops.UNION)
        if not utils.modifiers.delete_booleans_if_valid(boolean_objs=booleans):
            set_boolean_to_active_object(context, target, booleans)
        bool_notify(context, booleans, op_name="Union")
        return {'FINISHED'}


class PS_OT_BooleanIntersect(bpy.types.Operator):
    bl_idname      = "ps.boolean_intersect"
    bl_label       = "Boolean Intersect"
    bl_description = DESC_INTERSECT
    bl_options     = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True)


    def invoke(self, context, event):
        target = context.active_object
        booleans = utils.context.get_objects(context, types={'MESH'}, min_objs=2,  active_required=True, exclude=[target])
        bool_ops = utils.modifiers.BOOLEAN_OPS
        utils.modifiers.boolean_operations(context, target, booleans, boolean_ops=bool_ops.INTERSECT)
        if not utils.modifiers.delete_booleans_if_valid(boolean_objs=booleans):
            set_boolean_to_active_object(context, target, booleans)
        bool_notify(context, booleans, op_name="Intersect")
        return {'FINISHED'}


def set_boolean_to_active_object(context, target, booleans):
    if len(booleans) == 1:
        target.select_set(False)
        booleans[0].select_set(True)
        context.view_layer.objects.active = booleans[0]


def bool_notify(context, booleans, op_name=""):
    settings = utils.addon.user_prefs().settings
    msgs = [
        ("Operation", op_name),
        ("Applied", "True" if settings.destructive_mode else "False"),
        ("Deleted", "True" if settings.destructive_mode and settings.del_booleans_if_destructive else "False"),
        ("Objects", f'{len(booleans)}')]
    utils.notifications.init(context, messages=msgs)



