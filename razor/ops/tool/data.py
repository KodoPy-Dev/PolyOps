########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gpu
import math
from collections import OrderedDict
from enum import Enum
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from gpu_extras.batch import batch_for_shader
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from ...props.entity import PS_PROPS_Razor_Entity, EntityTess
from ...props.sketch import PS_PROPS_Razor_Sketch, SketchTess
from ...props.workplane import PS_PROPS_Razor_Workplane
from ....utils.event import LMB_press, LMB_release, is_mouse_dragging, reset_mouse_drag
from ....utils.math3 import matrix_loc_rot
from .... import utils

########################•########################
"""                 DATA BASE                 """
########################•########################

class DB:
    prefs   = None
    razor   = None
    runtime = None
    ops     = None
    surface = None
    part    = None
    sketch_CON = None

    @classmethod
    def init(cls, context, event):
        cls.reset()
        cls.prefs   = utils.addon.user_prefs()
        cls.razor   = context.scene.razor
        cls.runtime = Runtime(context, event)
        cls.ops     = Ops()
        cls.surface = Surface()
        cls.part    = Part()
        cls.sketch_CON = SketchController()

    @classmethod
    def reset(cls):
        cls.prefs   = None
        cls.razor   = None
        cls.runtime = None
        cls.ops     = None
        cls.surface = None
        cls.part    = None
        cls.sketch_CON = None

    @classmethod
    def close(cls):
        razor = bpy.context.scene.razor
        revert = True if razor.ops.status in {'CANCELLED', 'ERROR'} else False
        if isinstance(cls.part, Part):
            cls.part.close(revert)
        if isinstance(cls.sketch_CON, SketchController):
            cls.sketch_CON.close(revert)
        cls.reset()

    @classmethod
    def update(cls, context, event):
        cls.runtime.update(context, event)


class Runtime:
    def __init__(self, context, event):
        self.context = context
        self.event = event
        self.LMB_pressed = False
        self.LMB_released = False
        self.mouse_pos = Vector((0,0))
        self.is_mouse_dragging = False
        reset_mouse_drag()


    def update(self, context, event):
        self.context = context
        self.event = event
        self.LMB_pressed = LMB_press(event)
        self.LMB_released = LMB_release(event)
        self.mouse_pos.x = event.mouse_region_x
        self.mouse_pos.y = event.mouse_region_y
        self.is_mouse_dragging = is_mouse_dragging(event)


class Ops:
    def __init__(self):
        self.graphics = utils.graphics.Graphics()
        self.points_ws = []
        self.points_ls = []


    def reset(self):
        self.graphics.clear(opt='ALL')
        self.points_ws.clear()
        self.points_ls.clear()


class Surface:
    def __init__(self):
        # Space
        self.loc_ws = Vector((0,0,0))
        self.rot_ws = Quaternion()
        self.sca_ws = Vector((0,0,0))
        self.mat_ws = Matrix.Identity(4)
        self.loc_rot_mat_ws = Matrix.Identity(4)
        self.loc_rot_mat_ws_inv = Matrix.Identity(4)
        self.mat_ws_inv = Matrix.Identity(4)
        self.mat_ws_trs = Matrix.Identity(4)
        self.normal = Vector((0,0,1))
        # Points
        self.snap_points = []
        self.bvh_tree = None
        self.kd_tree = None
        # Sources
        self.workplane = None
        self.obj = None
        self.world_axis = ''


    def setup_for_screen_space(self):
        razor = DB.razor
        razor.ops.space = 'VIEW_2D'


    def setup_for_workplane(self, workplane):
        razor = DB.razor
        razor.ops.space = 'VIEW_3D'

        self.workplane = workplane
        transform = self.workplane.transform
        mat_ws = transform.get_matrix()
        self.set_matrices(mat_ws)
        self.normal = transform.get_normal()
        GRID = workplane.get_grid_data(axis_points=True, central_lines=True, origin=True)
        points = GRID['AXIS_POINTS'] + GRID['CENTRAL_LINES_X'] + GRID['CENTRAL_LINES_Y'] + [GRID['ORIGIN']]
        self.snap_points = points
        self.kd_tree = utils.math3.kd_tree_from_points(points=self.snap_points)


    def setup_for_obj(self, obj):
        razor = DB.razor
        razor.ops.space = 'VIEW_3D'

        self.obj = obj
        mat_ws = obj.matrix_world.copy()
        self.set_matrices(mat_ws)
        self.normal = (self.mat_ws_trs @ Vector((0,0,1))).normalized()


    def setup_for_world(self, axis='XY'):
        razor = DB.razor
        razor.ops.space = 'VIEW_3D'

        self.world_axis = axis
        loc = Vector((0,0,0))
        sca = Vector((1,1,1))
        if axis == 'XY':
            rot = Quaternion()
            self.set_matrices(Matrix.LocRotScale(loc, rot, sca))
        elif axis == 'XZ':
            rot = Quaternion(Vector((1,0,0)), math.pi/2)
            self.set_matrices(Matrix.LocRotScale(loc, rot, sca))
        elif axis == 'YZ':
            rot = Quaternion(Vector((0,1,0)), math.pi/2)
            self.set_matrices(Matrix.LocRotScale(loc, rot, sca))
        self.normal = (self.mat_ws_trs @ Vector((0,0,1))).normalized()


    def set_matrices(self, mat_ws=Matrix.Identity(4)):
        razor = DB.razor
        razor.ops.space = 'VIEW_3D'

        if not isinstance(mat_ws, Matrix): return False
        if len(mat_ws) != 4: return False
        loc, rot, sca = mat_ws.decompose()
        self.loc_ws = loc
        self.rot_ws = rot
        self.sca_ws = sca
        self.mat_ws = mat_ws
        self.mat_ws_inv = self.mat_ws.inverted_safe()
        self.mat_ws_trs = self.mat_ws.to_3x3().transposed()
        # No Scale
        self.loc_rot_mat_ws = matrix_loc_rot(mat_ws)
        self.loc_rot_mat_ws_inv = self.loc_rot_mat_ws.inverted_safe()
        return True


class Part:
    def __init__(self):
        self.bm = None
        self.obj = None
        self.mod = None
        self.mesh = None
        self.lattice = None
        self.control_points = {'FRONT':(0,1,4,5), 'BACK':(2,3,6,7), 'TOP':(4,5,6,7), 'BOTTOM':(0,1,2,3), 'LEFT':(0,2,4,6), 'RIGHT':(1,3,5,7)}


    def setup(self):
        self.create_mesh_obj()
        self.create_bmesh()


    def create_mesh_obj(self):
        context = DB.runtime.context
        collection = utils.collections.razor_collection(context)
        # Invalid
        if not collection:
            return False
        view_layer = context.view_layer
        # Create
        name = "Razor Part Object"
        self.obj = utils.object.create_obj(context, data_type='MESH', obj_name=name, data_name="Mesh", collection=collection, ensure_visible=True)
        self.obj.hide_set(False, view_layer=view_layer)
        self.mesh = self.obj.data
        self.obj.matrix_world = DB.surface.loc_rot_mat_ws.copy()
        # Valid
        return True


    def create_bmesh(self):
        # Valid
        if isinstance(self.bm, bmesh.types.BMesh):
            if self.bm.is_valid:
                return True
            else:
                self.bm.free()
                self.bm = None
        # Invalid
        if not isinstance(self.mesh, bpy.types.Mesh):
            return False
        # Create
        self.bm = bmesh.new(use_operators=True)
        self.bm.from_mesh(self.mesh, face_normals=True, vertex_normals=True)
        # Valid
        return True


    def create_lattice_obj(self):
        # Invalid
        if not isinstance(self.obj, bpy.types.Object):
            return False
        context = DB.runtime.context
        # Create
        name = f"Razor Part Lattice"
        self.lattice = create(context, data_type='LATTICE', obj_name=name, data_name="Lattice", collection=collection, ensure_visible=True)
        self.lattice.data.interpolation_type_u = 'KEY_LINEAR'
        self.lattice.data.interpolation_type_v = 'KEY_LINEAR'
        self.lattice.data.interpolation_type_w = 'KEY_LINEAR'
        self.lattice.hide_set(True, view_layer=view_layer)
        self.lattice.matrix_world = DB.surface.loc_rot_mat_ws.copy()
        # Parent
        utils.object.parent_object(child=self.lattice, parent=self.obj)
        # Mod
        self.mod = self.obj.modifiers.new('Lattice', 'LATTICE')
        self.mod.object = self.lattice
        self.mod.strength = 1.0
        # Valid
        return True


    def show_objects(self, show_obj=True, show_lattice=False):
        context = DB.runtime.context
        view_layer = context.view_layer
        if self.obj: self.obj.hide_set(show_obj, view_layer=view_layer)
        if self.lattice: self.lattice.hide_set(show_lattice, view_layer=view_layer)


    def deform_side(self, side='TOP', location=Vector((0,0,0))):
        if side not in self.control_points: return
        indices = self.control_points[side]
        for index in indices:
            self.lattice.data.points[index].co_deform = location


    def write_bmesh_to_mesh(self):
        if isinstance(self.bm, bmesh.types.BMesh):
            if isinstance(self.mesh, bpy.types.Mesh):
                self.bm.to_mesh(self.mesh)
                self.mesh.calc_loop_triangles()


    def close(self, revert=False):
        if revert:
            if self.obj:
                utils.object.delete_obj(self.obj)
            if self.lattice:
                utils.object.delete_obj(self.lattice)
        else:
            self.write_bmesh_to_mesh()

        if isinstance(self.bm, bmesh.types.BMesh):
            self.bm.free()
        self.bm = None
        del self.bm
        del self.obj
        del self.mod
        del self.mesh
        del self.lattice


class SketchController:
    def __init__(self):
        self.sketch = None
        self.sketch_tess = None
        self.active_entity_CON = None
        self.entity_CONS = []


    def setup(self):
        razor = DB.razor
        self.sketch = razor.new_sketch(name="Sketch", mat_ws=DB.surface.loc_rot_mat_ws.copy(), set_active=True)
        if isinstance(self.sketch, PS_PROPS_Razor_Sketch):
            return True
        return False


    def new_entity_CON(self):
        if isinstance(self.sketch):
            entity_CON = EntityController(sketch=self.sketch)
            self.active_entity_CON = entity_CON
            self.entity_CONS.append(entity_CON)
            return True
        return False


    def evaluate(self):
        pass


    def undo(self):
        pass


    def close(self, revert=False):
        razor = bpy.context.scene.razor

        def delete_all():
            if isinstance(self.sketch, PS_PROPS_Razor_Sketch):
                self.sketch_tess = None
                uuid = self.sketch.uuid
                razor.del_sketch(uuid)
                self.sketch = None

        def delete_flagged():
            if isinstance(self.sketch, PS_PROPS_Razor_Sketch):
                for entity_CON in self.entity_CONS:
                    if entity_CON.deleted and isinstance(entity_CON.entity, PS_PROPS_Razor_Entity):
                        uuid = entity_CON.entity.uuid
                        self.sketch.del_entity(uuid)
        
        if revert: delete_all()
        else: delete_flagged()


    def draw_2D(self):
        pass


    def draw_3D(self):
        for entity_CON in self.entity_CONS:
            if not entity_CON.deleted:
                entity_CON.draw_3D()


class EntityController:
    def __init__(self, sketch):
        self.sketch = sketch
        self.entity = None
        self.entity_tess = None
        self.uuid = ""
        self.created = False
        self.deleted = False


    def new_entity(self):
        self.entity = None
        if isinstance(self.sketch, PS_PROPS_Razor_Sketch):
            self.entity = self.sketch.new_entity(shape=DB.razor.ops.shape)
            self.uuid = self.entity.uuid
            self.created = True
            return True
        return False


    def new_tess(self):
        self.entity_tess = None
        if isinstance(self.entity, EntityTess):
            self.entity_tess = self.entity.new_entity_tesselator()
            return True
        return False


    def del_entity(self):
        self.deleted = True
        if isinstance(self.entity, PS_PROPS_Razor_Entity):
            self.entity.deleted = True
            return True
        return False


    def reset(self):
        if isinstance(self.entity, PS_PROPS_Razor_Entity):
            self.entity.reset()
        if isinstance(self.entity_tess, EntityTess):
            self.entity_tess.reset()


    def build(self, points_ws=[]):
        self.geo_evaluated = False
        self.edits_evaluated = False
        if isinstance(self.entity_tess, EntityTess):
            self.entity_tess.build_geo_from_points(points_ws)
            if self.entity_tess.geo_valid:
                self.entity_tess.build_batches()
                return self.entity_tess.geo_valid and self.entity_tess.batches_valid
        return False


    def save(self):
        if isinstance(self.tess, EntityTess):
            if self.entity_tess.register_data_to_entity():
                self.entity_tess.set_color_mode(mode='EVAL')
                return True
        return False


    def draw_2D(self):
        pass


    def draw_3D(self):
        if self.deleted: return
        if isinstance(self.entity_tess, EntityTess):
            if not self.deleted:
                self.entity_tess.draw_3D()

