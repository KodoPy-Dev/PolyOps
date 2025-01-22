########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gpu
import gc
import math
import enum
from gpu import state
from gpu_extras.batch import batch_for_shader
from collections.abc import Iterable
from mathutils import Vector, Matrix
from mathutils.geometry import distance_point_to_plane, intersect_line_plane, intersect_point_line
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d, region_2d_to_location_3d
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from . import math3
from .addon import user_prefs
from .bmu import ensure_bmesh_type_tables_normals_selections, ensure_bmesh_normals_selections
from .context import object_mode_toggle_reset, object_mode_toggle_start, object_mode_toggle_end
from .graphics import COLORS
from .vec_fade import init as init_vec_fade

########################•########################
"""                  OPTIONS                  """
########################•########################

class OPTIONS(enum.Flag):
    NONE = enum.auto()
    REVERT = enum.auto()
    USE_RAY = enum.auto()
    USE_BME = enum.auto()
    USE_EVAL = enum.auto()
    ONLY_VISIBLE = enum.auto()
    ONLY_SPECIFIED = enum.auto()
    IGNORE_HIDDEN_GEO = enum.auto()
    CHECK_OBSTRUCTIONS = enum.auto()

########################•########################
"""                  INTERNAL                 """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
EPSILON = 0.0001
MOUSE = Vector((0,0))
RAY_ORIGIN = Vector((0,0,0))
RAY_NORMAL = Vector((0,0,0))
RAY_END = Vector((0,0,0))
RAY_STEP = Vector((0,0,0))

def update_ray_info(context, event):
    global MOUSE, RAY_ORIGIN, RAY_NORMAL, RAY_END, RAY_STEP
    MOUSE = Vector((event.mouse_region_x, event.mouse_region_y))
    RAY_ORIGIN = region_2d_to_origin_3d(context.region, context.region_data, MOUSE)
    RAY_NORMAL = region_2d_to_vector_3d(context.region, context.region_data, MOUSE)
    RAY_END = RAY_ORIGIN + (RAY_NORMAL * context.space_data.clip_end)
    RAY_STEP = RAY_NORMAL * EPSILON


def is_obj_valid(obj):
    if isinstance(obj, bpy.types.Object):
        if obj.name in bpy.data.objects:
            if obj.type == 'MESH':
                return True
    return False


def is_obj_visible(context, obj):
    if is_obj_valid(obj):
        view_layer = context.view_layer
        if obj.name in view_layer.objects:
            space = context.space_data
            if space.type == 'VIEW_3D':
                if obj.visible_get(view_layer=view_layer, viewport=space):
                    return True
    return False


def is_bmesh_valid(bm):
    if isinstance(bm, bmesh.types.BMesh):
        if bm.is_valid:
            return True
    return False


def sort_hit_info(hit_infos=[], attr=''):
    if all([isinstance(var, HitInfo) and hasattr(var, attr) for var in hit_infos]):
        if len(hit_infos) > 0:
            hit_infos.sort(key=lambda var: getattr(var, attr))
            return True
    return False


class HitInfo:
    def __init__(self, obj):
        # ID Data
        self.uid = obj.session_uid
        self.obj = obj
        self.ray = None
        self.bmed = None
        # MATRICES
        self.mat_ws = obj.matrix_world.copy()
        self.mat_ws_inv = obj.matrix_world.inverted_safe()
        self.mat_ws_trs = obj.matrix_world.transposed()
        # VERT
        self.vert_index = -1
        self.vert_dist_to_mouse = math.inf
        self.vert_dist_to_ray_origin = math.inf
        self.vert_co_ws = Vector((0,0,0))
        # EDGE
        self.edge_index = -1
        self.edge_dist_to_face_co_vs = math.inf
        self.edge_co_ws_nearest = Vector((0,0,0))
        self.edge_co_ws_center = Vector((0,0,0))
        # FACE
        self.face_index = -1
        self.face_dist_to_ray_origin = math.inf
        self.face_co_ws = Vector((0,0,0))
        self.face_no_ws = Vector((0,0,0))


    def __del__(self):
        del self.uid
        del self.obj
        del self.ray
        del self.bmed


class Ray:
    def __init__(self, context, obj, options=OPTIONS.NONE):
        # ID DATA
        self.uid = None
        self.obj = None
        self.use_eval = OPTIONS.USE_EVAL in options
        self.ignore_hidden_geo = OPTIONS.IGNORE_HIDDEN_GEO in options
        # MATRICES
        self.mat_ws = Matrix.Identity(4)
        self.mat_ws_inv = Matrix.Identity(4)
        self.mat_ws_trs = Matrix.Identity(4)
        # TREES
        self.BM = None
        self.BOUNDS_BVH = None
        self.FACE_BVH = None
        self.VERTS_KD = None
        self.build(context, obj)


    def build(self, context, obj):
        self.close()
        # ID Data
        self.uid = obj.session_uid
        self.obj = obj
        # MATRICES
        self.mat_ws = obj.matrix_world.copy()
        self.mat_ws_inv = obj.matrix_world.inverted_safe()
        self.mat_ws_trs = obj.matrix_world.transposed()
        # BMESH
        self.BM = bmesh.new(use_operators=False)
        if self.use_eval:
            deps = context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(deps)
            eval_mesh = eval_obj.to_mesh()
            self.BM.from_mesh(eval_mesh)
            eval_obj.to_mesh_clear()
        else:
            self.BM.from_mesh(obj.data)
        # TREES
        if ensure_bmesh_type_tables_normals_selections(self.BM):
            self.BM.transform(self.mat_ws)
            self.BOUNDS_BVH = math3.bvh_tree_from_bmesh_bounds(self.BM, tolerance=0.25)
            self.FACE_BVH = BVHTree.FromBMesh(self.BM, epsilon=0.0)
            self.VERTS_KD = KDTree(len(self.BM.verts))
            for vert in self.BM.verts:
                self.VERTS_KD.insert(vert.co, vert.index)
            self.VERTS_KD.balance()
        else:
            self.BM = None


    def validator(self):
        # ID DATA
        if not isinstance(self.obj, bpy.types.Object): return False
        try:
            if self.obj.session_uid != self.uid: return False
        except: return False
        # BMESH
        if not isinstance(self.BM, bmesh.types.BMesh): return False
        if not self.BM.is_valid: return False
        # BOUNDS
        if not isinstance(self.BOUNDS_BVH, BVHTree): return False
        # BVH
        if not isinstance(self.FACE_BVH, BVHTree): return False
        # KD
        if not isinstance(self.VERTS_KD, KDTree): return False
        return True


    def cast_to_bounds_BVH(self):
        if not self.validator(): return False
        hit_co_ws = self.BOUNDS_BVH.ray_cast(RAY_ORIGIN, RAY_NORMAL)[0]
        if isinstance(hit_co_ws, Vector): return True
        return False


    def cast_to_vert_BVH(self, context, options=OPTIONS.NONE):
        if not self.validator(): return None
        if OPTIONS.CHECK_OBSTRUCTIONS in options:
            for hit_info in self.__iter_ray_to_face_BVH():
                if isinstance(hit_info, HitInfo):
                    self.__closest_vert_to_mouse_from_face_BVH(context, hit_info)
                    if hit_info.vert_index >= 0:
                        return hit_info
                    else:
                        del hit_info
        delta = None
        for hit_info in self.__iter_ray_to_face_BVH():
            if isinstance(hit_info, HitInfo):
                self.__closest_vert_to_mouse_from_face_BVH(context, hit_info)
                if hit_info.vert_index >= 0:
                    if isinstance(delta, HitInfo):
                        if hit_info.vert_dist_to_mouse < delta.vert_dist_to_mouse:
                            delta = hit_info.vert_dist_to_mouse
                    else:
                        delta = hit_info
                else:
                    del hit_info
        return delta


    def cast_to_edge_BVH(self, context, options=OPTIONS.NONE):
        if not self.validator(): return None

        if OPTIONS.CHECK_OBSTRUCTIONS in options:
            for hit_info in self.__iter_ray_to_face_BVH():
                if isinstance(hit_info, HitInfo):
                    self.__closest_edge_to_mouse_from_face_BVH(context, hit_info)
                    if hit_info.edge_index >= 0:
                        return hit_info
                    else:
                        del hit_info
        delta = None
        for hit_info in self.__iter_ray_to_face_BVH():
            if isinstance(hit_info, HitInfo):
                self.__closest_edge_to_mouse_from_face_BVH(context, hit_info)
                if hit_info.edge_index >= 0:
                    if isinstance(delta, HitInfo):
                        if hit_info.vert_dist_to_mouse < delta.vert_dist_to_mouse:
                            delta = hit_info.vert_dist_to_mouse
                    else:
                        delta = hit_info
                else:
                    del hit_info
        return delta


    def cast_to_face_BVH(self, context, options=OPTIONS.NONE):
        if not self.validator(): return None

        for hit_info in self.__iter_ray_to_face_BVH():
            if isinstance(hit_info, HitInfo):
                return hit_info
        return None


    def cast_to_BVH_as_test(self, ray_origin=Vector((0,0,0)), ray_normal=Vector((0,0,0)), ray_distance=0.0):
        if not self.validator(): return False
        ray_origin = ray_origin.copy()
        ray_step = ray_normal * EPSILON
        while True:
            hit_co_ws, _, _, _ = self.FACE_BVH.ray_cast(ray_origin, ray_normal, ray_distance)
            # No Hit
            if not isinstance(hit_co_ws, Vector):
                return False
            # Ray Step
            ray_origin = hit_co_ws + ray_step
            # Search Hit Location
            search_data = self.FACE_BVH.find_nearest_range(hit_co_ws, EPSILON)
            for face_co_ws, face_normal_ws, face_index, _ in search_data:
                if face_index < len(self.BM.faces) and face_index >= 0:
                    face = self.BM.faces[face_index]
                    if face.is_valid:
                        # Skip Hidden Faces
                        if self.ignore_hidden_geo and face.hide:
                            continue
                        else:
                            return True
        return False


    def close(self):
        self.obj = None
        if isinstance(self.BM, bmesh.types.BMesh):
            self.BM.free()
        self.BM = None
        self.BOUNDS_BVH = None
        self.FACE_BVH = None
        self.VERTS_KD = None
        del self.BM
        del self.BOUNDS_BVH
        del self.FACE_BVH
        del self.VERTS_KD


    def __closest_vert_to_mouse_from_face_BVH(self, context, hit_info:HitInfo):
        face = self.BM.faces[hit_info.face_index]
        if not isinstance(face, bmesh.types.BMFace): return
        if not face.is_valid: return
        hw = context.area.width / 2
        hh = context.area.height / 2
        perp_mat = context.region_data.perspective_matrix
        for vert in face.verts:
            if vert.is_valid:
                prj = perp_mat @ vert.co.to_4d()
                if prj.w > 0.0:
                    vert_co_ss = Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w)))
                    distance = (MOUSE - vert_co_ss).length
                    if distance < hit_info.vert_dist_to_mouse:
                        hit_info.vert_index = vert.index
                        hit_info.vert_dist_to_mouse = distance
                        hit_info.vert_dist_to_ray_origin = (RAY_ORIGIN - vert.co).length
                        hit_info.vert_co_ws = vert.co.copy()


    def __closest_edge_to_mouse_from_face_BVH(self, context, hit_info:HitInfo):
        face = self.BM.faces[hit_info.face_index]
        if not isinstance(face, bmesh.types.BMFace): return
        if not face.is_valid: return
        perp_mat = context.region_data.perspective_matrix
        face_co_vs = perp_mat @ hit_info.face_co_ws
        for edge in face.edges:
            if not edge.is_valid: continue
            vert_1_co_ws = edge.verts[0].co
            vert_2_co_ws = edge.verts[1].co
            vert_1_co_vs = perp_mat @ vert_1_co_ws
            vert_2_co_vs = perp_mat @ vert_2_co_ws
            intersection, factor = intersect_point_line(face_co_vs, vert_1_co_vs, vert_2_co_vs)
            if factor < 0:
                factor = 0
                intersection = vert_1_co_vs
            elif factor > 1:
                factor = 1
                intersection = vert_2_co_vs
            distance = (intersection - face_co_vs).length
            if distance < hit_info.edge_dist_to_face_co_vs:
                hit_info.edge_dist_to_face_co_vs = distance
                hit_info.edge_co_ws_nearest = vert_1_co_ws.lerp(vert_2_co_ws, factor)
                hit_info.edge_co_ws_center = (vert_1_co_ws + vert_2_co_ws) / 2
                hit_info.edge_index = edge.index


    def __iter_ray_to_face_BVH(self):
        ray_origin = RAY_ORIGIN.copy()
        saved_indices = set()
        while True:
            hit_co_ws, _, _, _ = self.FACE_BVH.ray_cast(ray_origin, RAY_NORMAL)
            # No Hit
            if not isinstance(hit_co_ws, Vector):
                break
            # Ray Step
            ray_origin = hit_co_ws + RAY_STEP
            # Search Hit Location
            hit_infos = []
            search_data = self.FACE_BVH.find_nearest_range(hit_co_ws, EPSILON)
            for face_co_ws, face_normal_ws, face_index, _ in search_data:
                if face_index < len(self.BM.faces) and face_index >= 0:
                    if face_index not in saved_indices:
                        saved_indices.add(face_index)
                        face = self.BM.faces[face_index]
                        if face.is_valid:
                            # Skip Hidden Faces
                            if self.ignore_hidden_geo and face.hide: continue
                            # Calc Hit Info
                            hit_info = HitInfo(obj=self.obj)
                            hit_info.face_index = face_index
                            hit_info.face_dist_to_ray_origin = (RAY_ORIGIN - face_co_ws).length
                            hit_info.face_co_ws = face_co_ws
                            hit_info.face_no_ws = face_normal_ws
                            hit_infos.append(hit_info)
            if sort_hit_info(hit_infos, attr='face_dist_to_ray_origin'):
                for hit_info in hit_infos:
                    yield hit_info
        return None


class BmeshEditor:
    def __init__(self, obj):
        # SETTINGS
        self.undo_limit = user_prefs().settings.undo_limit
        # ID Data
        self.uid = obj.session_uid
        self.obj = obj
        # MATRICES
        self.mat_ws = obj.matrix_world.copy()
        self.mat_ws_inv = obj.matrix_world.inverted_safe()
        self.mat_ws_trs = obj.matrix_world.transposed()
        # ORIGINAL BACKUP
        self.ogmesh = obj.data.copy()
        self.ogmesh_uid = self.ogmesh.session_uid
        self.ogmesh.calc_loop_triangles()
        self.ogmesh.ps.is_backup = True
        # MESH BACKUPS
        self.backups = []
        # BMESH
        self.BM = None


    def validator(self):
        # ID DATA
        if not isinstance(self.obj, bpy.types.Object): return False
        try:
            if self.obj.session_uid != self.uid: return False
        except: return False
        if self.obj.type != 'MESH': return False
        # BACKUP
        if not isinstance(self.ogmesh, bpy.types.Mesh): return False
        try:
            if self.ogmesh.session_uid != self.ogmesh_uid: return False
        except: return False
        # BMESH
        return self.ensure_bmesh()


    def ensure_bmesh(self):
        if isinstance(self.BM, bmesh.types.BMesh) and self.BM.is_valid: return True
        if isinstance(self.BM, bmesh.types.BMesh) and not self.BM.is_valid:
            self.BM.free()
            self.BM = None
            gc.collect()
        if self.obj.data.is_editmode:
            self.BM = bmesh.from_edit_mesh(self.obj.data)
        else:
            self.BM = bmesh.new(use_operators=True)
            self.BM.from_mesh(self.obj.data, face_normals=True, vertex_normals=True, use_shape_key=False, shape_key_index=0)
        if ensure_bmesh_type_tables_normals_selections(self.BM): return True
        return False


    def restore(self):
        if not self.validator(): return False
        backup = self.backups[-1] if self.backups else self.ogmesh
        bmesh.ops.delete(self.BM, geom=self.BM.verts, context='VERTS')
        self.BM.from_mesh(backup, face_normals=True, vertex_normals=True, use_shape_key=False, shape_key_index=0)
        return ensure_bmesh_type_tables_normals_selections(self.BM)


    def update(self):
        if not self.validator(): return False
        ensure_bmesh_normals_selections(self.BM)
        if self.obj.data.is_editmode:
            bmesh.update_edit_mesh(self.obj.data, loop_triangles=True, destructive=True)
        elif not self.BM.is_wrapped:
            self.BM.to_mesh(self.obj.data)
            self.obj.data.calc_loop_triangles()
        return True


    def save(self):
        if not self.update(): return False
        if self.obj.data.is_editmode:
            self.obj.update_from_editmode()
        backup = self.obj.data.copy()
        backup.calc_loop_triangles()
        backup.ps.is_backup = True
        self.backups.append(backup)
        # Undo Limit
        if len(self.backups) > self.undo_limit:
            backup = self.backups[0]
            self.backups.remove(backup)
            if isinstance(backup, bpy.types.Mesh):
                if backup.session_uid != self.uid and backup.session_uid != self.ogmesh_uid:
                    if backup.name in bpy.data.meshes:
                        bpy.data.meshes.remove(backup, do_unlink=True, do_id_user=True, do_ui_user=True)
        return True


    def undo(self):
        if self.backups:
            backup = self.backups.pop()
            if isinstance(backup, bpy.types.Mesh):
                if backup.session_uid != self.uid and backup.session_uid != self.ogmesh_uid:
                    if backup.name in bpy.data.meshes:
                        bpy.data.meshes.remove(backup, do_unlink=True, do_id_user=True, do_ui_user=True)
        if self.restore():
            if self.update():
                return True
        return False


    def close(self, revert=False):
        # Remove Backups
        for backup in self.backups:
            if isinstance(backup, bpy.types.Mesh):
                if backup.session_uid != self.uid and backup.session_uid != self.ogmesh_uid:
                    if backup.name in bpy.data.meshes:
                        bpy.data.meshes.remove(backup)
        self.backups = []
        # Revert to Original Mesh
        if revert: self.restore()
        # Update Edit / Object mode mesh
        self.update()
        # Free the Bmesh
        if isinstance(self.BM, bmesh.types.BMesh):
            self.BM.free()
        self.BM = None
        if isinstance(self.obj, bpy.types.Object):
            try:
                self.obj.data.ps.is_backup = False
                self.obj.data.calc_loop_triangles()
            except: pass
        self.obj = None
        if isinstance(self.ogmesh, bpy.types.Mesh):
            try:
                if self.ogmesh.session_uid != self.uid:
                    if self.ogmesh.name in bpy.data.meshes:
                        bpy.data.meshes.remove(self.ogmesh)
            except: pass
        self.ogmesh = None
        # Delete
        del self.uid
        del self.obj
        del self.mat_ws
        del self.mat_ws_inv
        del self.mat_ws_trs
        del self.ogmesh
        del self.backups
        del self.BM


    def get_bm_elem(self, index=-1, elem_type='VERT'):
        if not self.ensure_bmesh(): return None
        if elem_type == 'VERT' and self.BM.verts:
            if index < len(self.BM.verts) and index >= 0:
                self.BM.verts.ensure_lookup_table()
                vert = self.BM.verts[index]
                if vert.is_valid:
                    return vert
        elif elem_type == 'EDGE' and self.BM.edges:
            if index < len(self.BM.edges) and index >= 0:
                self.BM.edges.ensure_lookup_table()
                edge = self.BM.edges[index]
                if edge.is_valid:
                    return edge
        elif elem_type == 'FACE' and self.BM.faces:
            if index < len(self.BM.faces) and index >= 0:
                self.BM.faces.ensure_lookup_table()
                face = self.BM.faces[index]
                if face.is_valid:
                    return face
        return None


class MeshGraphics:
    def __init__(self):
        # --------------- VERTS --------------- #
        # KEY -> Batch || VAL -> (Color, Use Depth Test, Point Size)
        self.vert_batch_map = {}
        # --------------- EDGES --------------- #
        # KEY -> Batch || VAL -> (Color, Use Depth Test, Line Width)
        self.edge_batch_map = {}
        # --------------- FACES --------------- #
        # KEY -> Batch || VAL -> (Color, Use Depth Test, Cull)
        self.face_batch_map = {}


    def clear_batches(self, verts=True, edges=True, faces=True):
        if verts: self.vert_batch_map.clear()
        if edges: self.edge_batch_map.clear()
        if faces: self.face_batch_map.clear()


    def batch_for_geo(self, obj, bm, geo=[], use_depth_test=False, point_size=1, line_width=1, face_cull=False, vert_color=None, edge_color=None, face_color=None):
        # VALIDATE
        if not geo: return
        if not is_obj_valid(obj): return
        if not is_bmesh_valid(bm): return

        # SORT : ELEMENTS
        verts = None
        edges = None
        faces = None
        for elem in geo:
            if isinstance(elem, bmesh.types.BMVert) and elem.is_valid:
                if verts is None:
                    verts = set()
                verts.add(elem)
            elif isinstance(elem, bmesh.types.BMEdge) and elem.is_valid:
                if edges is None:
                    edges = set()
                edges.add(elem)
            elif isinstance(elem, bmesh.types.BMFace) and elem.is_valid:
                if faces is None:
                    faces = set()
                faces.add(elem)
        if verts is None and edges is None and faces is None:
            return

        # REFS
        mat_ws = obj.matrix_world

        # BACTCH : VERTS
        if verts is not None:
            coords = [(mat_ws @ vert.co) + (vert.normal * 0.0007) for vert in verts]
            if coords:
                batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": coords})
                if batch:
                    color = vert_color if vert_color else COLORS.VERT
                    self.vert_batch_map[batch] = (color, use_depth_test, point_size)

        # BACTCH : EDGES
        if edges is not None:
            coords = [(mat_ws @ vert.co) + (vert.normal * 0.0005) for edge in edges for vert in edge.verts if vert.is_valid]
            if coords:
                batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": coords})
                if batch:
                    color = edge_color if edge_color else COLORS.EDGE
                    self.edge_batch_map[batch] = (color, use_depth_test, line_width)

        # BACTCH : FACES
        if faces is not None:
            loop_triangles = bm.calc_loop_triangles()
            if loop_triangles:
                triangles = {tri for tri in loop_triangles if tri[0].face in faces}
                coords = [(mat_ws @ loop.vert.co) + (loop.face.normal * 0.0003) for tri_loops in triangles for loop in tri_loops if loop.is_valid and loop.vert.is_valid]
                if coords:
                    indices = [(i, i+1, i+2) for i in range(0, len(coords), 3)]
                    batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": coords}, indices=indices)
                    if batch:
                        color = face_color if face_color else COLORS.FACE
                        self.face_batch_map[batch] = (color, use_depth_test, face_cull)


    def draw_3d(self, verts=True, edges=True, faces=True):
        if not verts and not edges and not faces: return
        state.blend_set('ALPHA')
        if faces:
            for batch, data in self.face_batch_map.items():
                color, use_depth_test, face_cull = data
                if use_depth_test:
                    state.depth_test_set('LESS_EQUAL')
                    state.depth_mask_set(True)
                if face_cull:
                    state.face_culling_set('BACK')
                UNIFORM_COLOR.uniform_float("color", color)
                batch.draw(UNIFORM_COLOR)
        if edges:
            for batch, data in self.edge_batch_map.items():
                color, use_depth_test, line_width = data
                if use_depth_test:
                    state.depth_test_set('LESS_EQUAL')
                    state.depth_mask_set(True)
                state.line_width_set(line_width)
                UNIFORM_COLOR.uniform_float("color", color)
                batch.draw(UNIFORM_COLOR)
        if verts:
            for batch, data in self.vert_batch_map.items():
                color, use_depth_test, point_size = data
                if use_depth_test:
                    state.depth_test_set('LESS_EQUAL')
                    state.depth_mask_set(True)
                state.point_size_set(point_size)
                UNIFORM_COLOR.uniform_float("color", color)
                batch.draw(UNIFORM_COLOR)
        state.line_width_set(1)
        state.point_size_set(1)
        state.face_culling_set('NONE')
        state.depth_test_set('NONE')
        state.depth_mask_set(False)
        state.blend_set('NONE')

########################•########################
"""                 CONTROLLER                """
########################•########################

def mesh_add_options(context, obj,
    check_bpy_data=True, check_no_runtime_data=True, check_only_visible=True,
    ray_obm=True, ray_edm=True,
    bme_obm=True, bme_edm=True,
    ignore_hid_geo_obm=False, ignore_hid_geo_edm=True,
    eval_obm=False, eval_edm=False):
    ''' Checks ON • Ray ON • Bme ON • Ignore Hidden EDM ON • Eval OFF'''

    options = OPTIONS.NONE

    # CHECKS
    if not isinstance(obj, bpy.types.Object): return options
    if not isinstance(obj.data, bpy.types.Mesh): return options
    if check_bpy_data:
        if obj.name not in bpy.data.objects: return options
        if obj.data.name not in bpy.data.meshes: return options
    if check_no_runtime_data:
        if obj.is_runtime_data: return options
        if obj.data.is_runtime_data: return options
    if check_only_visible:
        if not is_obj_visible(context, obj): return options
        options |= OPTIONS.ONLY_VISIBLE

    # EDIT MODE
    if obj.data.is_editmode:
        if ray_edm:
            options |= OPTIONS.USE_RAY
        if bme_edm:
            options |= OPTIONS.USE_BME
        if ignore_hid_geo_edm:
            options |= OPTIONS.IGNORE_HIDDEN_GEO
        if eval_edm:
            options |= OPTIONS.USE_EVAL

    # OBJECT MODE
    else:
        if ray_obm:
            options |= OPTIONS.USE_RAY
        if bme_obm:
            options |= OPTIONS.USE_BME
        if ignore_hid_geo_obm:
            options |= OPTIONS.IGNORE_HIDDEN_GEO
        if eval_obm:
            options |= OPTIONS.USE_EVAL

    # REMOVE NONE
    if options != OPTIONS.NONE:
        options &= ~OPTIONS.NONE
    return options


def ray_options(context, check_wireframe=True, only_specified=False):
    options = OPTIONS.NONE
    if check_wireframe:
        if context.space_data.type == 'VIEW_3D':
            if context.space_data.shading.type != 'WIREFRAME':
                options = OPTIONS.CHECK_OBSTRUCTIONS
    if only_specified:
        options |= OPTIONS.ONLY_SPECIFIED
    if options != OPTIONS.NONE:
        options &= ~OPTIONS.NONE
    return options


class BmeshController:
    def __init__(self):
        object_mode_toggle_reset()
        self.RAY_MAP = dict()
        self.BME_MAP = dict()
        self.specified_obj_uids = set()
        self.save_pools = []
        self.mesh_graphics = MeshGraphics()
        self.last_ray_uid = None

    # --- MANAGE --- #

    def add_obj(self, context, obj, options=OPTIONS.NONE):
        # NULL
        if options == OPTIONS.NONE:
            return False
        # ORIGINAL
        if obj != obj.original:
            obj = obj.original
        # ID CHECK
        if not is_obj_valid(obj):
            return False
        # VISIBLE
        if OPTIONS.ONLY_VISIBLE in options:
            if not is_obj_visible(context, obj):
                return False
        # UPDATE MESH
        if obj.data.is_editmode:
            obj.update_from_editmode()
        # KEY
        uid = obj.session_uid
        # BMESH RAY
        if OPTIONS.USE_RAY in options:
            # OLD
            if uid in self.RAY_MAP:
                if isinstance(self.RAY_MAP[uid], Ray):
                    self.RAY_MAP[uid].close()
                del self.RAY_MAP[uid]
            # NEW
            self.RAY_MAP[uid] = Ray(context, obj, options)
        # BMESH EDITOR
        if OPTIONS.USE_BME in options:
            # OLD
            if uid in self.BME_MAP:
                if isinstance(self.BME_MAP[uid], BmeshEditor):
                    self.BME_MAP[uid].close(revert=True)
                del self.BME_MAP[uid]
            # NEW
            self.BME_MAP[uid] = BmeshEditor(obj)
        return True


    def close(self, context, revert=False):
        for ray in self.RAY_MAP.values():
            if isinstance(ray, BmeshEditor):
                ray.close()
        for bmed in self.BME_MAP.values():
            if isinstance(bmed, BmeshEditor):
                bmed.close(revert)
        del self.RAY_MAP
        del self.BME_MAP
        del self.specified_obj_uids
        del self.save_pools
        del self.mesh_graphics
        del self.last_ray_uid
        gc.collect()

    # --- LIMITS --- #

    def clear_specified_objs(self):
        self.specified_obj_uids.clear()


    def set_specified_objs(self, objs=[]):
        self.specified_obj_uids.clear()
        for obj in objs:
            if isinstance(obj, bpy.types.Object):
                self.specified_obj_uids.add(obj.session_uid)


    def is_obj_in_specified(self, obj):
        if isinstance(obj, bpy.types.Object):
            if obj.session_uid in self.specified_obj_uids:
                return True
        return False


    def available_objs(self, ensure_ray=True, ensure_bmeditor=True):
        objs = set()
        if ensure_ray:
            for ray in self.RAY_MAP.values():
                if isinstance(ray, Ray):
                    if ray.validator():
                        objs.add(ray.obj)
        if ensure_bmeditor:
            for bmed in self.BME_MAP.values():
                if isinstance(bmed, BmeshEditor):
                    if bmed.validator():
                        objs.add(bmed.obj)
        return objs

    # --- RAY --- #

    def get_bmeditor_from_last_ray(self):
        if self.last_ray_uid is None:
            return None
        if self.last_ray_uid in self.BME_MAP:
            bmed = self.BME_MAP[self.last_ray_uid]
            if isinstance(bmed, BmeshEditor):
                if bmed.validator():
                    return bmed
        return None


    def rebuild_ray(self, context, obj):
        if not is_obj_valid(obj): return
        if obj != obj.original:
            obj = obj.original
        if obj.data.is_editmode:
            obj.update_from_editmode()
        uid = obj.session_uid
        if uid in self.RAY_MAP:
            if isinstance(self.RAY_MAP[uid], Ray):
                self.RAY_MAP[uid].build(context, obj)


    def ray_to_vert(self, context, event, options=OPTIONS.NONE):
        update_ray_info(context, event)
        hit_infos = []
        for uid, ray in self.RAY_MAP.items():
            if isinstance(ray, Ray):
                # Specified Only
                if OPTIONS.ONLY_SPECIFIED in options:
                    if uid not in self.specified_obj_uids:
                        continue
                # Bounds
                if ray.cast_to_bounds_BVH():
                    # Verts
                    hit_info = ray.cast_to_vert_BVH(context, options)
                    if isinstance(hit_info, HitInfo):
                        hit_infos.append(hit_info)
        #  By Closest Face
        if OPTIONS.CHECK_OBSTRUCTIONS in options:
            if sort_hit_info(hit_infos, attr='face_dist_to_ray_origin'):
                hit_info = hit_infos[0]
                if len(hit_infos) > 1:
                    del hit_infos[1:]
                del hit_infos
                if not self.is_point_obstructed(point=hit_info.vert_co_ws):
                    return self.__finalize_hit_info(hit_info)
        # By Closest Vert
        else:
            if sort_hit_info(hit_infos, attr='vert_dist_to_ray_origin'):
                hit_info = hit_infos[0]
                if len(hit_infos) > 1:
                    del hit_infos[1:]
                del hit_infos
                return self.__finalize_hit_info(hit_info)
        return None


    def ray_to_edge(self, context, event, options=OPTIONS.NONE):
        update_ray_info(context, event)
        hit_infos = []
        for uid, ray in self.RAY_MAP.items():
            if isinstance(ray, Ray):
                # Specified Only
                if OPTIONS.ONLY_SPECIFIED in options:
                    if uid not in self.specified_obj_uids:
                        continue
                # Bounds
                if ray.cast_to_bounds_BVH():
                    # Edge
                    hit_info = ray.cast_to_edge_BVH(context, options)
                    if isinstance(hit_info, HitInfo):
                        hit_infos.append(hit_info)
        #  By Closest Face
        if OPTIONS.CHECK_OBSTRUCTIONS in options:
            if sort_hit_info(hit_infos, attr='face_dist_to_ray_origin'):
                hit_info = hit_infos[0]
                if len(hit_infos) > 1:
                    del hit_infos[1:]
                del hit_infos
                if not self.is_point_obstructed(point=hit_info.edge_co_ws_nearest):
                    return self.__finalize_hit_info(hit_info)
        # By Closest Vert
        else:
            if sort_hit_info(hit_infos, attr='edge_dist_to_face_co_vs'):
                hit_info = hit_infos[0]
                if len(hit_infos) > 1:
                    del hit_infos[1:]
                del hit_infos
                return self.__finalize_hit_info(hit_info)
        return None


    def ray_to_face(self, context, event, options=OPTIONS.NONE):
        update_ray_info(context, event)
        hit_infos = []
        for uid, ray in self.RAY_MAP.items():
            if isinstance(ray, Ray):
                # Specified Only
                if OPTIONS.ONLY_SPECIFIED in options:
                    if uid not in self.specified_obj_uids:
                        continue
                # Bounds
                if ray.cast_to_bounds_BVH():
                    # FACE
                    hit_info = ray.cast_to_face_BVH(context, options)
                    if isinstance(hit_info, HitInfo):
                        hit_infos.append(hit_info)
        #  By Closest Face
        if sort_hit_info(hit_infos, attr='face_dist_to_ray_origin'):
            hit_info = hit_infos[0]
            if len(hit_infos) > 1:
                del hit_infos[1:]
            del hit_infos
            return self.__finalize_hit_info(hit_info)
        return None

    # --- BME --- #

    def iter_bmeditors(self):
        for uid, bmed in self.BME_MAP.items():
            if isinstance(bmed, BmeshEditor):
                # Specified BmEditors
                if self.specified_obj_uids:
                    if uid in self.specified_obj_uids:
                        if bmed.validator():
                            yield bmed
                # All BmEditors
                else:
                    if bmed.validator():
                        yield bmed


    def get_bmeditor(self, obj):
        if isinstance(obj, bpy.types.Object):
            uid = obj.session_uid
            if uid in self.BME_MAP:
                bmed = self.BME_MAP[uid]
                if isinstance(bmed, BmeshEditor):
                    if bmed.validator():
                        return bmed
        return None

    # --- SAVE --- #

    def save_in_pool(self, context, obj, update_ray=True):
        self.__validate_save_pool()
        if not isinstance(obj, bpy.types.Object):
            return False
        uid = obj.session_uid
        if uid in self.BME_MAP:
            bmed = self.BME_MAP[uid]
            if isinstance(bmed, BmeshEditor):
                if bmed.save():
                    if update_ray:
                        self.rebuild_ray(context, obj)
                    if len(self.save_pools) == 0:
                        pool = [uid]
                        self.save_pools.append(pool)
                    else:
                        self.save_pools[-1].append(uid)
                    return True
        return False


    def save_pool_push(self):
        self.__validate_save_pool()
        # Add an empty list to the end of the pools if needed
        if len(self.save_pools) > 0:
            if len(self.save_pools[-1]) > 0:
                pool = []
                self.save_pools.append(pool)


    def save_pool_undo(self, context, update_ray=True):
        self.__validate_save_pool()
        if not self.save_pools:
            return set()
        # Get last pool with items
        pool = None
        while len(self.save_pools) > 0:
            pool = self.save_pools.pop()
            if len(pool) > 0:
                break
        # No valid pool
        if not isinstance(pool, list):
            return set()
        # Undo BmEditors
        objs = set()
        for uid in pool:
            if uid in self.BME_MAP:
                bmed = self.BME_MAP[uid]
                if isinstance(bmed, BmeshEditor):
                    if bmed.undo():
                        objs.add(bmed.obj)
        # Rebuild Ray Data
        if update_ray:
            for obj in objs:
                self.rebuild_ray(context, obj)
        # Ensure new inserts
        self.save_pools.append([])
        # Objs that hae been changed
        return objs

    # --- UTILS --- #

    def is_point_obstructed(self, point=Vector((0,0,0))):
        ray_normal = (RAY_ORIGIN - point).normalized()
        ray_origin = point + (ray_normal * EPSILON)
        ray_distance = (RAY_ORIGIN - ray_origin).length
        for ray in self.RAY_MAP.values():
            if isinstance(ray, Ray):
                if ray.cast_to_BVH_as_test(ray_origin, ray_normal, ray_distance):
                    return True
        return False


    def __validate_save_pool(self):
        # Invalid Pools
        if not isinstance(self.save_pools, list):
            self.save_pools = []
            return
        # Remove bad pools
        for pool in self.save_pools[:]:
            if not isinstance(pool, list):
                self.save_pools.remove(pool)
        # Remove bad items
        for pool in self.save_pools:
            for uid in pool[:]:
                if not isinstance(uid, int):
                    pool.remove(uid)
        # Remove empty pools : Ignoring the last (since its for push)
        max_index = len(self.save_pools) - 1
        if max_index <= 0:
            return
        for index, pool in enumerate(self.save_pools[:]):
            if len(pool) == 0:
                if index < max_index:
                    self.save_pools.remove(pool)


    def __finalize_hit_info(self, hit_info:HitInfo):
        if not isinstance(hit_info, HitInfo):
            return None
        uid = hit_info.uid
        self.last_ray_uid = uid
        if uid in self.RAY_MAP:
            ray = self.RAY_MAP[uid]
            if isinstance(ray, Ray):
                if ray.validator():
                    hit_info.ray = ray
        if uid in self.BME_MAP:
            bmed = self.BME_MAP[uid]
            if isinstance(bmed, BmeshEditor):
                if bmed.validator():
                    hit_info.bmed = bmed
        return hit_info

########################•########################
"""                POINT CAST                 """
########################•########################

def ray_to_point__vert_co_ws(context, event, bmeCON, options=OPTIONS.NONE):
    point = None
    if isinstance(bmeCON, BmeshController):
        hit_info = bmeCON.ray_to_vert(context, event, options)
        if isinstance(hit_info, HitInfo):
            point = hit_info.vert_co_ws.copy()
            hit_info = None
            del hit_info
    return point


def ray_to_point__edge_co_ws_nearest(context, event, bmeCON, options=OPTIONS.NONE):
    point = None
    if isinstance(bmeCON, BmeshController):
        hit_info = bmeCON.ray_to_edge(context, event, options)
        if isinstance(hit_info, HitInfo):
            point = hit_info.edge_co_ws_nearest.copy()
            hit_info = None
            del hit_info
    return point


def ray_to_point__edge_co_ws_center(context, event, bmeCON, options=OPTIONS.NONE):
    point = None
    if isinstance(bmeCON, BmeshController):
        hit_info = bmeCON.ray_to_edge(context, event, options)
        if isinstance(hit_info, HitInfo):
            point = hit_info.edge_co_ws_center.copy()
            hit_info = None
            del hit_info
    return point


def ray_to_point__face_co_ws(context, event, bmeCON, options=OPTIONS.NONE):
    point = None
    if isinstance(bmeCON, BmeshController):
        hit_info = bmeCON.ray_to_face(context, event, options)
        if isinstance(hit_info, HitInfo):
            point = hit_info.face_co_ws.copy()
            hit_info = None
            del hit_info
    return point
