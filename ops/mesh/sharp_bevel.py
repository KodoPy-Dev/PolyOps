########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gc
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Sharp Bevel\n
• Edit Mode
\t\t→ Bevel selected edges"""

class PS_OT_SharpBevel(bpy.types.Operator):
    bl_idname      = "ps.sharp_bevel"
    bl_label       = "Sharp Bevel"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        self.prefs = utils.addon.user_prefs()

        # BME
        OPTIONS = utils.bme.OPTIONS
        self.bme_ray_options = OPTIONS.NONE
        self.bme_add_options = OPTIONS.USE_BME | OPTIONS.ONLY_VISIBLE | OPTIONS.IGNORE_HIDDEN_GEO
        self.bmeCON = utils.bme.BmeshController()
        objs = utils.context.get_mesh_objs_from_edit_mode_if_edges_selected(context)
        if not objs:
            utils.notifications.init(context, messages=[("$Error", "Are any edges selected?")])
            self.bmeCON.close(context, revert=True)
            return {'CANCELLED'}
        for obj in objs:
            self.bmeCON.add_obj(context, obj, self.bme_add_options)
        self.objs = self.bmeCON.available_objs(ensure_bmeditor=True, ensure_ray=False)
        if not self.objs:
            utils.notifications.init(context, messages=[("$Error", "Are the mesh objects visible?")])
            self.bmeCON.close(context, revert=True)
            return {'CANCELLED'}

        # Props
        self.bevel_width = 0
        self.clamp = False
        self.segments = 2
        self.miter_index = 2
        self.miter_outer = ['SHARP', 'PATCH', 'ARC']
        # Graphics
        self.obj_count_str = str(len(objs))
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.objs)
        self.setup_status_and_help_panels(context)
        self.setup_slide_menu(context, event)
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
        self.slide_menu.update(context, event)
        if self.slide_menu.status == UX_STATUS.ACTIVE:
            return
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_status_and_help_panels(context)
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        self.modal_status = self.std_ops.status


    def exit_modal(self, context):
        def shut_down():
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                self.std_ops.close(context, revert=True)
                self.bmeCON.close(context, revert=True)
            else:
                self.std_ops.close(context, revert=False)
                self.bmeCON.close(context, revert=False)
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)
        self.std_ops = None
        self.bmeCON = None
        del self.std_ops
        del self.bmeCON
        gc.collect()
        toggle = utils.context.object_mode_toggle_start(context)
        if toggle: utils.context.object_mode_toggle_end(context)

    # --- MENU --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [("H", "Toggle Help")]
        if self.prefs.settings.show_modal_help:
            help_msgs = [
                ("H"          , "Toggle Help"),
                ("RET / SPACE", "Confirm"),
                ("RMB / ESC"  , "Cancel"),
                ("SHIFT + Z"  , "VP Display"),]
        status_msgs = [
            ("Sharp Bevel",),
            ("Objects" , self.obj_count_str),
        ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_slide_menu(self, context, event):
        SlideProp = utils.modal_ux.SlideProp
        SlideMenu = utils.modal_ux.SlideMenu
        # Slides
        callback = self.slide_menu_callback
        props = [
            SlideProp(as_slider=True, label="Segments", label_len=6, label_tip="", instance=self, prop_type=int, prop_name='segments', prop_len=4, min_val=1, max_val=6, soft_max=True, callback=callback),
            SlideProp(as_slider=True, label="Width", label_len=6, label_tip="", instance=self, prop_type=float, prop_name='bevel_width', prop_len=4, min_val=0, max_val=1, soft_max=True, callback=callback),
            SlideProp(as_slider=False, label="Miter Outer", label_len=7, label_tip="", instance=self, prop_type=list, prop_name='miter_outer', prop_len=7, callback=callback, index=self.miter_index),
            SlideProp(as_slider=False, label="Clamp", label_len=7, instance=self, prop_type=bool , prop_name='clamp', prop_len=7, callback=callback),
        ]
        # Menu
        self.slide_menu = SlideMenu(context, event, slide_props=props)


    def slide_menu_callback(self, context, event, slide_prop):
        label = slide_prop.label
        if label == "Miter Outer":
            self.miter_index = slide_prop.index
        self.update_bmesh_ops(context)

    # --- SHADER --- #

    def draw_post_view(self, context):
        self.bmeCON.mesh_graphics.draw_3d(verts=True, edges=True, faces=True)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.slide_menu.draw()

    # --- UTILS --- #

    def update_bmesh_ops(self, context):
        # Graphics
        self.bmeCON.mesh_graphics.clear_batches(verts=True, edges=True, faces=True)
        # Bmesh Editors
        for bmed in self.bmeCON.iter_bmeditors():
            bmed.restore()
            obj = bmed.obj
            bm = bmed.BM
            sel_edges = [edge for edge in bm.edges if edge.select]
            if sel_edges:
                ret = bmesh.ops.bevel(bm,
                    geom=sel_edges,
                    offset=self.bevel_width,
                    offset_type='OFFSET',
                    profile_type='SUPERELLIPSE',
                    segments=self.segments,
                    profile=1,
                    affect='EDGES',
                    clamp_overlap=self.clamp,
                    material=0,
                    loop_slide=True,
                    mark_seam=False,
                    mark_sharp=False,
                    harden_normals=False,
                    face_strength_mode='NONE',
                    miter_outer=self.miter_outer[self.miter_index],
                    miter_inner='SHARP',
                    spread=0,
                    vmesh_method='ADJ')
                # Graphics
                self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=ret['verts'] + ret['edges'] + ret['faces'], use_depth_test=True, point_size=1, line_width=3, face_cull=False)
                # Update
                bmed.update()
