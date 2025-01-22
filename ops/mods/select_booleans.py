########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS, OPS_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set
ModType = utils.modifiers.TYPES

DESC = """Select Booleans\n
(LMB)
\t\t→ Boolean Search System\n
(SHIFT)
\t\t→ Quick select last"""

class PS_OT_SelectBooleans(bpy.types.Operator):
    bl_idname      = "ps.select_booleans"
    bl_label       = "Select Booleans"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        obj = utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)
        if obj:
            return any([mod.type == ModType.BOOLEAN for mod in obj.modifiers])
        return False


    def invoke(self, context, event):
        # Quick Select
        if event.shift:
            self.quick_select_last(context)
            return {'FINISHED'}
        # Data
        self.obj = utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)
        if self.obj is None:
            return {'CANCELLED'}
        self.obj.select_set(False)
        self.boolean_mods = [mod for mod in self.obj.modifiers if type(mod) == bpy.types.BooleanModifier]
        if len(self.boolean_mods) == 0:
            utils.notifications.init(context, messages=[("Error", "No Booleans found")])
            return {'CANCELLED'}
        self.boolean_objs = utils.modifiers.boolean_objs_from_mods(self.obj)
        self.recursive_objs = []
        self.recursive_objs_map = {}
        for obj in self.boolean_objs:
            objs = utils.modifiers.referenced_booleans(obj)
            if objs:
                self.recursive_objs.append(obj)
                self.recursive_objs.extend(objs)
                self.recursive_objs_map[obj] = objs
        # Revert Data
        self.mod_vis_map = utils.modifiers.vp_visibility_map(self.obj)
        self.bool_vis_map = {obj: obj.visible_get(view_layer=context.view_layer) for obj in self.boolean_objs}
        self.bool_recursive_vis_map = {obj: obj.visible_get(view_layer=context.view_layer) for obj in self.recursive_objs if obj not in self.boolean_objs}
        # Ensure Objects Visible in Scene
        all_boolean_objs = self.boolean_objs[:] + self.recursive_objs[:]
        for obj in all_boolean_objs:
            if obj.name not in context.view_layer.objects:
                utils.collections.ensure_object_collections_visible(context, obj)
        # State
        self.index = 0
        self.append_mode = False
        self.recursive_mode = False
        self.viewport_mode = True
        self.deselect = not self.obj.select_get(view_layer=context.view_layer)
        self.all_booleans_showing = all([obj.visible_get(view_layer=context.view_layer) for obj in self.boolean_objs])
        # Menus
        self.menu_setup(context, event)
        self.setup_status_and_help_panels(context)
        # Init Scroll
        self.reveal_upto_index(context, event)
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

        self.menu.update(context, event)
        # Set from callback
        if self.modal_status in {MODAL_STATUS.CONFIRM, MODAL_STATUS.CANCEL}:
            return
        if self.menu.status == UX_STATUS.ACTIVE:
            self.modal_status = MODAL_STATUS.RUNNING
            return

        self.modal_status = MODAL_STATUS.RUNNING

        increment = utils.event.increment_value(event)
        if abs(increment) > 0:
            self.index = utils.algos.index_wrap(self.index - increment, sequence=self.boolean_mods)
            self.reveal_upto_index(context, event)
            self.setup_status_and_help_panels(context)

        # Append Mode
        if event.type == 'A' and event.value == 'PRESS':
            self.append_mode = not self.append_mode
            self.setup_status_and_help_panels(context)

        # Recursive Mode
        if event.type == 'S' and event.value == 'PRESS':
            self.recursive_mode = not self.recursive_mode
            self.setup_status_and_help_panels(context)

        # Recursive Mode
        if event.type == 'D' and event.value == 'PRESS':
            self.viewport_mode = not self.viewport_mode
            self.setup_status_and_help_panels(context)

        # Finished
        if utils.event.confirmed(event):
            self.modal_status = MODAL_STATUS.CONFIRM
        # Cancelled
        elif utils.event.cancelled(event, value='PRESS'):
            self.modal_status = MODAL_STATUS.CANCEL
        # View Movement
        elif utils.event.pass_through(event):
            self.modal_status = MODAL_STATUS.PASS  


    def exit_modal(self, context):
        def shut_down():
            # Revert
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                utils.modifiers.set_vp_visibility_from_map(self.obj, vis_map=self.mod_vis_map)
                for obj, state in self.bool_vis_map.items():
                    obj.hide_set(not state, view_layer=context.view_layer)
                for obj, state in self.bool_recursive_vis_map.items():
                    obj.hide_set(not state, view_layer=context.view_layer)
            self.menu.close(context)
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)

    # --- MENUS --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [
            ("LMB", "Finish"),
            ("RMB", "Cancel"),
            ("Scroll", "Next"),
        ]
        status_msgs = [
            ("Select Boolean"),
            ("Object", self.obj.name),
            ("Modifier", self.boolean_mods[self.index].name),
        ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def menu_setup(self, context, event):

        # Modal UX Menu
        PropMap = utils.modal_ux.PropMap
        Row = utils.modal_ux.Row
        Container = utils.modal_ux.Container
        Menu = utils.modal_ux.Menu

        # --- EXIT --- #
        map_1 = PropMap(label="Cancel" , instance=self, prop_name='menu_callback', box_len=6)
        map_2 = PropMap(label="Confirm", instance=self, prop_name='menu_callback', box_len=6)
        row = Row(label="", prop_maps=[map_1, map_2], min_borders=True)
        cont_1 = Container(label="", rows=[row])

        # --- MOD ROWS --- #
        rows = []
        for index, mod in enumerate(self.boolean_mods):
            map_1 = PropMap(label="V", tip="Modifier : Show Viewport", instance=mod, prop_name='show_viewport', box_len=3, call_back=self.menu_callback, user_data={'MOD': mod})
            map_2 = PropMap(label="R", tip="Modifier : Show Render", instance=mod, prop_name='show_render', box_len=3, call_back=self.menu_callback, user_data={'MOD': mod})
            map_3 = PropMap(label="B", tip="Booleans : Reveal & Select / Hide", instance=self, prop_name='menu_callback', box_len=3, user_data={'MOD': mod}, highlight_callback=self.sel_and_rev_callback)
            row = Row(label=mod.name, prop_maps=[map_1, map_2, map_3], min_label_height=True, highlight_id=index, highlight_callback=self.row_highlight_callback)
            rows.append(row)
        cont_2 = Container(label="Boolean Modifiers", rows=rows)

        # --- SCROLL SETTINGS --- #
        map_1 = PropMap(label="Append", tip="Show all up to the current modifier", instance=self, prop_name='append_mode', box_len=10, call_back=self.menu_callback)
        row_1 = Row(label="", prop_maps=[map_1], min_borders=True)
        map_1 = PropMap(label="Recursive", tip="Reveal all the recursive booleans", instance=self, prop_name='recursive_mode', box_len=10, call_back=self.menu_callback)
        row_2 = Row(label="", prop_maps=[map_1], min_borders=True)
        # map_1 = PropMap(label="Show Viewport", tip="Enable / Disable viewport display up to the current modifier", instance=self, prop_name='viewport_mode', box_len=10, call_back=self.menu_callback)
        # row_3 = Row(label="", prop_maps=[map_1], min_borders=True)
        # cont_3 = Container(label="Scroll", rows=[row_1, row_2, row_3])
        cont_3 = Container(label="Scroll", rows=[row_1, row_2])

        # --- GLOBAL --- #
        map_1 = PropMap(label="Modifiers", tip="(Hide / Show) Boolean Modifiers", instance=self, prop_name='menu_callback', box_len=10, highlight_callback=self.all_mods_visible_callback)
        row_1 = Row(label="", prop_maps=[map_1], min_borders=True)
        map_1 = PropMap(label="Booleans", tip="(Hide / Show) Boolean Objects", instance=self, prop_name='menu_callback', box_len=10, highlight_callback=self.all_booleans_visible_callback)
        row_2 = Row(label="", prop_maps=[map_1], min_borders=True)
        map_1 = PropMap(label="Recursive", tip="(Hide / Show) Booleans of Booleans", instance=self, prop_name='menu_callback', box_len=10, highlight_callback=self.all_recursive_visible_callback)
        row_3 = Row(label="", prop_maps=[map_1], min_borders=True)
        map_1 = PropMap(label="Deselect", tip="Select / Descelect the main object", instance=self, prop_name='deselect', box_len=10, call_back=self.menu_callback)
        row_4 = Row(label="", prop_maps=[map_1], min_borders=True)
        cont_4 = Container(label="Global", rows=[row_1, row_2, row_3, row_4])

        self.menu = Menu(context, event, containers=[cont_1, cont_2, cont_3, cont_4])


    def menu_callback(self, context, event, prop_map):
        label = prop_map.label
        # --- UPDATE INDEX --- #
        if label in {'V', 'R', 'B'}:
            for i, mod in enumerate(self.boolean_mods):
                if 'MOD' in prop_map.user_data:
                    if prop_map.user_data['MOD'] == mod:
                        self.index = i
                        self.setup_status_and_help_panels(context)
                        break
        # --- EXIT --- #
        if label == "Confirm":
            self.modal_status = MODAL_STATUS.CONFIRM
        elif label == "Cancel":
            self.modal_status = MODAL_STATUS.CANCEL
        # --- MOD ROWS --- #
        elif label == "B":
            if 'MOD' in prop_map.user_data:
                mod = prop_map.user_data['MOD']
                if type(mod) == bpy.types.BooleanModifier and hasattr(mod, 'object') and type(mod.object) == bpy.types.Object:
                    obj = mod.object
                    if self.sel_and_rev_callback(context, event, prop_map):
                        obj.select_set(False)
                        obj.hide_set(True)
                    else:
                        utils.object.unhide(context, obj)
                        utils.object.select_obj(context, obj, make_active=False)
                        utils.poly_fade.init(obj=obj)
        # --- SCROLL SETTINGS --- #
        # elif label == "Show Viewport":
        #     # Reveal the modifier
        #     if self.viewport_mode and self.index < len(self.boolean_mods) and self.index > -1:
        #         mod = self.boolean_mods[self.index]
        #         mod.show_viewport = True
        elif label == "Recursive" and prop_map.prop_name == 'recursive_mode':
            # Reveal the current objs recursive objects
            if self.recursive_mode and self.index < len(self.boolean_mods) and self.index > -1:
                mod = self.boolean_mods[self.index]
                if type(mod.object) == bpy.types.Object:
                    if mod.object in self.recursive_objs_map:
                        for recursive_obj in self.recursive_objs_map[mod.object]:
                            utils.object.unhide(context, recursive_obj)
                            recursive_obj.select_set(True)
                            utils.poly_fade.init(obj=recursive_obj)
        # --- GLOBAL --- #
        elif label == "Modifiers":
            if all([mod.show_viewport for mod in self.boolean_mods]):
                for mod in self.boolean_mods: mod.show_viewport = False
            else:
                for mod in self.boolean_mods: mod.show_viewport = True
        elif label == "Booleans":
            if self.all_booleans_showing:
                self.all_booleans_showing = False
                for obj in self.boolean_objs:
                    obj.hide_set(True)
            else:
                self.all_booleans_showing = True
                for obj in self.boolean_objs:
                    if obj.visible_get(view_layer=context.view_layer) == False:
                        utils.object.unhide(context, obj)
        elif label == "Recursive" and prop_map.prop_name == 'menu_callback':
            if self.all_recursive_visible_callback(context, None, None):
                for obj in self.recursive_objs:
                    obj.hide_set(True)
            else:
                for obj in self.recursive_objs:
                    if obj.visible_get(view_layer=context.view_layer) == False:
                        utils.object.unhide(context, obj)
        elif label == "Deselect":
            self.obj.select_set(not self.deselect)


    def sel_and_rev_callback(self, context, event, prop_map):
        if 'MOD' in prop_map.user_data:
            mod = prop_map.user_data['MOD']
            if type(mod) == bpy.types.BooleanModifier and hasattr(mod, 'object') and type(mod.object) == bpy.types.Object:
                if mod.object.visible_get(view_layer=context.view_layer):
                    if mod.object.select_get(view_layer=context.view_layer):
                        return True
        return False


    def all_mods_visible_callback(self, context, event, prop_map):
        if all([mod.show_viewport for mod in self.boolean_mods]):
            return True
        return False


    def all_booleans_visible_callback(self, context, event, prop_map):
        if all([obj.visible_get(view_layer=context.view_layer) for obj in self.boolean_objs]):
            return True
        return False


    def all_recursive_visible_callback(self, context, event, prop_map):
        if all([obj.visible_get(view_layer=context.view_layer) for obj in self.recursive_objs]):
            return True
        return False


    def row_highlight_callback(self, row):
        return row.highlight_id == self.index

    # --- SHADER --- #

    def draw_post_view(self, context):
        pass
        

    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.menu.draw()

    # --- UTILS --- #

    def reveal_upto_index(self, context, event):
        focus_mod = None
        # Loop over boolean modifiers
        for i, mod in enumerate(self.boolean_mods):
            obj = None
            if type(mod.object) == bpy.types.Object:
                obj = mod.object
            # Active Modifier
            if i == self.index:
                focus_mod = mod
                # Reveal the modifier
                if self.viewport_mode:
                    mod.show_viewport = True
                # Reveal the object
                if obj:
                    utils.object.unhide(context, obj)
                    utils.object.select_obj(context, obj, make_active=True)
                    utils.poly_fade.init(obj=obj)

                    # Show the recursive objs
                    if self.recursive_mode and obj in self.recursive_objs_map:
                        for recursive_obj in self.recursive_objs_map[obj]:
                            utils.object.unhide(context, recursive_obj)
                            recursive_obj.select_set(True)
                            utils.poly_fade.init(obj=obj)
            # Not the active mod
            else:
                # Hide the others if not appending
                if self.append_mode == False:
                    if obj:
                        obj.select_set(False)
                        obj.hide_set(True)
                        # Hide the recursive
                        if obj in self.recursive_objs_map:
                            for recursive_obj in self.recursive_objs_map[obj]:
                                recursive_obj.select_set(False)
                                recursive_obj.hide_set(True)
        # Scroll menu to index
        if focus_mod:
            self.menu.focus_to_row_by_prop(instance=focus_mod, prop_name='show_viewport')
            self.menu.update(context, event)


    def quick_select_last(self, context):
        def get_last(obj):
            for mod in reversed(obj.modifiers):
                if mod.type == ModType.BOOLEAN:
                    for item in dir(mod):
                        attr = getattr(mod, item)
                        if type(attr) == bpy.types.Object:
                            if attr.type == 'MESH':
                                return attr
            return None
        obj = utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)
        boolean_obj = get_last(obj)
        if boolean_obj:
            utils.object.select_none(context)
            utils.object.select_obj(context, boolean_obj, make_active=True)
            utils.poly_fade.init(boolean_obj, bounding_box_only=True)
            utils.modal_labels.fade_label_init(context, text=boolean_obj.name, coord_ws=boolean_obj.matrix_world.translation)
