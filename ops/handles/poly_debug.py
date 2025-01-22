########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gpu
import traceback
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from ... import utils

DESC = """Poly Debug\n
Highlights Triangles (Red) and NGons (Blue)\n
• (LMB) Enable / Disable
\t\t→ Edit Mode Only"""

class PS_OT_PolyDebug(bpy.types.Operator):
    bl_idname      = "ps.poly_debug"
    bl_label       = "Poly Debug"
    bl_description = DESC
    bl_options     = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        if DRAW_HANDLE:
            remove_poly_debug_handle()
            utils.notifications.init(context, messages=[("Poly Debug", "Disabled")])
            return {'FINISHED'}
        objs = utils.context.get_meshes_from_edit_or_from_selected(context)
        if not objs:
            remove_poly_debug_handle()
            utils.notifications.init(context, messages=[("Poly Debug", "Setup Error")])
            return {'FINISHED'}
        assign_poly_debug_handle(context, objs)
        if DRAW_HANDLE:
            utils.notifications.init(context, messages=[("Poly Debug", "Enabled"), ("Object Count", str(len(DRAW_DATAS)))])
        else:
            remove_poly_debug_handle()
            utils.notifications.init(context, messages=[("Poly Debug", "Setup Error"), ("Prefs Polygon Limit", f"{utils.addon.user_prefs().settings.poly_debug_display_limit}")])
        return {'FINISHED'}

########################•########################
"""               HANDLE DATA                 """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
DRAW_HANDLE = None
DRAW_DATAS = []

class Data:
    def __init__(self, obj_name=""):
        self.obj_name = obj_name
        self.tri_color = (1, 0.25, 0, 0.125)
        self.tri_batch = None
        self.ngon_color = (0, 0.25, 1, 0.125)
        self.ngon_batch = None


    def gen_batches(self, scene):
        self.tri_batch = None
        self.ngon_batch = None
        obj = None
        if self.obj_name in scene.objects:
            obj = scene.objects[self.obj_name]
        if not (isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh)):
            return False
        # Limit does not consider it invalid
        if len(obj.data.polygons) >= utils.addon.user_prefs().settings.poly_debug_display_limit:
            return True
        if obj.data.is_editmode:
            obj.update_from_editmode()
        tris = []
        ngons = []
        mesh = obj.data
        mat_ws = obj.matrix_world
        mesh.calc_loop_triangles()
        loop_triangles = mesh.loop_triangles
        loops = mesh.loops
        verts = mesh.vertices
        polygons = mesh.polygons
        for triangle_loops in loop_triangles:
            polygon_vert_count = len(polygons[triangle_loops.polygon_index].vertices)
            if polygon_vert_count == 3:
                tris.extend(mat_ws @ (verts[loops[loop_index].vertex_index].co + (triangle_loops.normal * 0.0005)) for loop_index in triangle_loops.loops)
            elif polygon_vert_count > 4:
                ngons.extend(mat_ws @ (verts[loops[loop_index].vertex_index].co + (triangle_loops.normal * 0.0005)) for loop_index in triangle_loops.loops)
        # Batches
        if tris:
            self.tri_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": tris}, indices=[(i, i+1, i+2) for i in range(0, len(tris), 3)])
        if ngons:
            self.ngon_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": ngons}, indices=[(i, i+1, i+2) for i in range(0, len(ngons), 3)])
        return True


    def draw(self):
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.depth_mask_set(True)
        gpu.state.blend_set('ALPHA')
        if self.tri_batch:
            UNIFORM_COLOR.uniform_float("color", self.tri_color)
            self.tri_batch.draw(UNIFORM_COLOR)
        if self.ngon_batch:
            UNIFORM_COLOR.uniform_float("color", self.ngon_color)
            self.ngon_batch.draw(UNIFORM_COLOR)
        gpu.state.depth_test_set('NONE')
        gpu.state.depth_mask_set(False)
        gpu.state.blend_set('NONE')

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_poly_debug_handle(null=''):
    # Remove Deps
    if depsgraph_update_handle in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handle)
    # Remove Shader
    global DRAW_HANDLE, DRAW_DATAS
    if DRAW_HANDLE:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(DRAW_HANDLE, "WINDOW")
        except Exception as e:
            print("Poly Debug: Did not remove draw handle")
            traceback.print_exc()
    # Clear Data
    DRAW_HANDLE = None
    DRAW_DATAS.clear()


def assign_poly_debug_handle(context, objs):
    # Remove
    remove_poly_debug_handle()
    # Obj Check
    poly_debug_display_limit = utils.addon.user_prefs().settings.poly_debug_display_limit
    objs = [obj for obj in objs if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh) and len(obj.data.polygons) <= poly_debug_display_limit]
    if not objs:
        return
    # Assign Deps
    assigned_deps_handle = False
    if depsgraph_update_handle not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handle)
        assigned_deps_handle = True
    if not assigned_deps_handle:
        return
    # Assign Shader
    global DRAW_HANDLE, DRAW_DATAS
    if DRAW_HANDLE is None:
        try:
            DRAW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", "POST_VIEW")
        except Exception as e:
            remove_poly_debug_handle()
            print("Poly Debug: Did not assign draw handle")
            traceback.print_exc()
            return
    # Data Setup
    obj_names = {obj.name for obj in objs}
    DRAW_DATAS = [Data(obj_name=name) for name in obj_names]
    depsgraph_update_handle(context.scene)

########################•########################
"""                 CALLBACKS                 """
########################•########################

def depsgraph_update_handle(scene):
    global DRAW_DATAS
    if bpy.context.mode != 'EDIT_MESH':
        remove_poly_debug_handle()
        return
    for data in DRAW_DATAS[:]:
        try:
            if not data.gen_batches(scene):
                DRAW_DATAS.remove(data)
        except Exception as e:
            print("Poly Debug: Batch Error")
            traceback.print_exc()
            DRAW_DATAS.remove(data)
    if not DRAW_DATAS:
        remove_poly_debug_handle()


def draw():
    if DRAW_HANDLE:
        for data in DRAW_DATAS[:]:
            try:
                data.draw()
            except Exception as e:
                print("Poly Debug: Draw Error")
                traceback.print_exc()
                DRAW_DATAS.remove(data)
    if not DRAW_DATAS:
        remove_poly_debug_handle()
