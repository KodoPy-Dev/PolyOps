########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
import math
from math import cos, sin, pi
from bpy.props import *
from bpy.types import PropertyGroup
from gpu_extras.batch import batch_for_shader
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from mathutils.geometry import tessellate_polygon, interpolate_bezier
from . import PROPS_BASE, PROPS_UUID, SHAPE_OPTS, ENTITY_POINT_COUNT_NEEDED, ENTITY_TRIS_NEEDED, PS_PROPS_Razor_Transform
from ...utils.math3 import matrix_loc_rot, center_of_coords
from ...utils import debug_print


class PS_PROPS_Razor_Vertex(PROPS_BASE, PROPS_UUID):
    co : FloatVectorProperty(name="Coord 3D", default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)


class PS_PROPS_Razor_Edge(PROPS_BASE, PROPS_UUID):
    i1 : IntProperty(name="Vert Index 1", default=0, min=0)
    i2 : IntProperty(name="Vert Index 2", default=0, min=0)


class PS_PROPS_Razor_Triangle(PROPS_BASE, PROPS_UUID):
    i1 : IntProperty(name="Vert Index 1", default=0, min=0)
    i2 : IntProperty(name="Vert Index 2", default=0, min=0)
    i3 : IntProperty(name="Vert Index 3", default=0, min=0)


class PS_PROPS_Razor_Entity(PROPS_BASE, PROPS_UUID):

    # --- SKETCH ---- #

    sketch_uuid : StringProperty(name="Sketch UUID", default="")
    transform : PointerProperty(type=PS_PROPS_Razor_Transform)

    # --- SETTINGS ---- #

    shape : EnumProperty(name="Shape", items=SHAPE_OPTS, default='RECTANGLE')
    deleted : BoolProperty(name="Deleted", default=False)
    resolution : IntProperty(name="Resolution", default=24, min=3, max=256)
    is_only_wire : BoolProperty(name="Is Only Wire", default=False)
    is_construction : BoolProperty(name="Is Construction", default=False)

    # --- GEOMETRY LOCAL SPACE ---- #

    geo_is_set : BoolProperty(name="Geo Is Set", default=False)
    verts : CollectionProperty(type=PS_PROPS_Razor_Vertex)
    edges : CollectionProperty(type=PS_PROPS_Razor_Edge)
    tris  : CollectionProperty(type=PS_PROPS_Razor_Triangle)

    # --- PARAMETRICS ---- #

    center : PointerProperty(type=PS_PROPS_Razor_Vertex)
    length : FloatProperty(name="Length", default=0.0)
    width  : FloatProperty(name="Width", default=0.0)
    radius : FloatProperty(name="Radius", default=0.0)

    def reset(self):
        self.geo_is_set = False
        self.verts.clear()
        self.edges.clear()
        self.tris.clear()
        self.center.co = (0.0, 0.0, 0.0)
        self.length = 0
        self.width = 0
        self.radius = 0


    def point_count_needed(self):
        return ENTITY_POINT_COUNT_NEEDED[self.shape]


    def get_sketch(self):
        sketches = self.id_data.razor.sketches
        for sketch in sketches:
            if sketch.uuid == self.sketch_uuid:
                return sketch
        return None


    def new_entity_tesselator(self):
        entity_tess = EntityTess(entity=self)
        return entity_tess

########################•########################
"""                 TESSELATOR                """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')

class EntityTess:
    def __init__(self, entity):
        self.uuid = entity.uuid
        self.entity = entity
        self.mat_ws = self.entity.transform.get_matrix()
        self.mat_ws_inv = self.mat_ws.inverted_safe()
        self.reset()


    def reset(self):
        # Geometry
        self.geo_valid = False
        self.verts_ws = []
        self.verts_ls = []
        self.edge_indices = []
        self.tri_indices = []
        # Paramaters
        self.center_ws = Vector((0,0,0))
        self.center_ls = Vector((0,0,0))
        self.length = 0
        self.width = 0
        self.radius = 0
        # Batches (World Space)
        self.batches_valid = False
        self.vert_batch = None
        self.edge_batch = None
        self.tri_batch = None
        self.center_batch = None
        # Graphics
        self.set_color_mode(mode='SKETCH')


    def build_geo_from_points(self, points_ws=[]):
        self.reset()

        # Validators
        if not isinstance(self.entity, PS_PROPS_Razor_Entity):
            debug_print("Error : Entity type incorrect")
            return
        if not all(isinstance(point, Vector) and len(point) == 3 for point in points_ws):
            debug_print("Error : Point types incorrect")
            return
        required_count = ENTITY_POINT_COUNT_NEEDED[self.entity.shape]
        if required_count > 0:
            if required_count != len(points_ws):
                debug_print("Error : Rquired count != point count")
                return

        # Geometry
        shape = self.entity.shape
        if shape == 'POINT':
            p1_ws = points_ws[0]
            p1_ls = self.convert_point_to_local_space(p1_ws)
            self.verts_ws.append(p1_ws)
            self.verts_ls.append(p1_ls)
            self.center_ws = p1_ws
            self.center_ls = p1_ls
        elif shape == 'LINE':
            p1_ws = points_ws[0]
            p2_ws = points_ws[1]
            p1_ls = self.convert_point_to_local_space(p1_ws)
            p2_ls = self.convert_point_to_local_space(p2_ws)
            self.verts_ws.append(p1_ws)
            self.verts_ws.append(p2_ws)
            self.verts_ls.append(p1_ls)
            self.verts_ls.append(p2_ls)
            self.center_ws = (p1_ws + p2_ws) / 2
            self.center_ls = (p1_ls + p2_ls) / 2
            self.length = (p1_ls + p2_ls).length
        elif shape == 'CIRCLE':
            p1_ws = points_ws[0]
            p2_ws = points_ws[1]
            p1_ls = self.convert_point_to_local_space(p1_ws)
            p2_ls = self.convert_point_to_local_space(p2_ws)
            self.center_ws = p1_ws
            self.center_ls = p1_ls
            self.radius = (p1_ls - p2_ls).length
            res = self.entity.resolution
            step = (pi * 2) / res
            self.verts_ls = [(Vector((cos(step * i), sin(step * i), 0)) * self.radius) + self.center_ls for i in range(res)]
            self.verts_ws = [self.mat_ws @ p_ls for p_ls in self.verts_ls]
        elif shape == 'RECTANGLE':
            p1_ws = points_ws[0]
            p2_ws = points_ws[1]
            p1_ls = self.convert_point_to_local_space(p1_ws)
            p2_ls = self.convert_point_to_local_space(p2_ws)
            max_x = max(p1_ls.x, p2_ls.x)
            min_x = min(p1_ls.x, p2_ls.x)
            max_y = max(p1_ls.y, p2_ls.y)
            min_y = min(p1_ls.y, p2_ls.y)
            BL = Vector((min_x, min_y, 0))
            TL = Vector((min_x, max_y, 0))
            TR = Vector((max_x, max_y, 0))
            BR = Vector((max_x, min_y, 0))
            self.verts_ls = [BL, TL, TR, BR]
            self.verts_ws = [self.mat_ws @ BL, self.mat_ws @ TL, self.mat_ws @ TR, self.mat_ws @ BR]
            self.center_ls = (BL + TR) / 2
            self.center_ws = self.mat_ws @ self.center_ls
            self.length = (BL - BR).length
            self.width = (BL - TL).length
        elif shape == 'NGON':
            self.verts_ws = points_ws[:]
            self.verts_ls = self.convert_points_to_local_space(points_ws)
            self.center_ws = center_of_coords(coords=points_ws)
            self.center_ls = center_of_coords(coords=self.verts_ls)
        elif shape == 'ELLIPSE':
            p1_ls, p2_ls, p3_ls = self.convert_points_to_local_space(points_ws)
            self.center_ws = self.mat_ws @ p1_ls
            self.center_ls = p1_ls
            self.length = abs((p1_ls - p2_ls).x) * 2
            self.width = abs((p1_ls - p3_ls).y) * 2
            rx = self.length / 2
            ry = self.width / 2
            res = self.entity.resolution
            step = (pi * 2) / res
            self.verts_ls = [Vector((cos(step * i) * rx, sin(step * i) * ry, 0)) + self.center_ls for i in range(res)]
            self.verts_ws = [self.mat_ws @ p_ls for p_ls in self.verts_ls]
        elif shape == 'ARC':
            p1_ws = points_ws[0]
            p4_ws = points_ws[3]
            p1_ls, p2_ls, p3_ls, p4_ls = self.convert_points_to_local_space(points_ws)
            res = self.entity.resolution
            self.verts_ls = interpolate_bezier(p1_ls, p2_ls, p3_ls, p4_ls, res)
            self.verts_ws = [self.mat_ws @ p_ls for p_ls in self.verts_ls]
            self.center_ws = (p1_ws + p4_ws) / 2
            self.center_ls = (p1_ls + p4_ls) / 2
        else:
            debug_print("Error : Entity Shape Type Incorrect")
            return

        # Indices
        count = len(self.verts_ls)
        # Edges
        if count > 1:
            self.edge_indices = [(i, (i + 1) % count) for i in range(count)]
        # Tris
        if count > 2:
            if shape in ENTITY_TRIS_NEEDED:
                self.tri_indices = tessellate_polygon([self.verts_ls])
        # Valid
        self.geo_valid = True


    def build_geo_from_entity(self):
        self.geo_valid = False
        # Validators
        if not isinstance(self.entity, PS_PROPS_Razor_Entity):
            debug_print("Error : Entity type incorrect")
            return
        if not self.entity.geo_is_set:
            debug_print("Error : Entity not completed")
            return

        # Geometry
        self.verts_ls = [vert.co.copy() for vert in self.entity.verts]
        self.verts_ws = [self.mat_ws @ point_ls for point_ls in self.verts_ls]
        self.center_ls = self.entity.center.co.copy()
        self.center_ws = self.mat_ws @ self.center_ls
        self.length = self.entity.length
        self.width = self.entity.width
        self.radius = self.entity.radius

        # Indices
        edges = self.entity.edges
        self.edge_indices = [(edge.i1, edge.i2) for edge in edges]
        tris = self.entity.tris
        self.tri_indices = [(tri.i1, tri.i2, tri.i3) for tri in tris]

        # Valid
        self.geo_valid = True


    def register_data_to_entity(self):
        # Validate
        if not isinstance(self.entity, PS_PROPS_Razor_Entity):
            debug_print("Error : Entity type incorrect")
            return False
        # Ensure entity is reset after attempt to write data
        self.entity.reset()
        # Validate
        if not self.verts_ls:
            debug_print("Error : No local space verts")
            return False
        # Write Data
        entity = self.entity
        verts = entity.verts
        for i, co in enumerate(self.verts_ls):
            vert = verts.add()
            vert.index = i
            vert.co = co.copy()
        edges = entity.edges
        for i, indices in enumerate(self.edge_indices):
            edge = edges.add()
            edge.index = i
            edge.i1, edge.i2 = indices
        tris = entity.tris
        for i, indices in enumerate(self.tri_indices):
            tri = tris.add()
            tri.index = i
            tri.i1, tri.i2, tri.i3 = indices
        # Valid
        entity.geo_is_set = True
        return True

    # --- UTILS --- #

    def convert_points_to_local_space(self, points_ws=[]):
        points_ls = []
        append = verts_ls.append
        for point_ws in points_ws:
            point_ls = self.mat_ws_inv @ point_ws
            point_ls.z = 0
            append(point_ls)
        return points_ls


    def convert_point_to_local_space(self, point_ws=Vector((0,0,0))):
        point_ls = self.mat_ws_inv @ point_ws
        point_ls.z = 0
        return point_ls

    # --- GRAPHICS --- #

    def set_color_mode(self, mode='SKETCH'):
        self.center_color = (1.0, 1.0, 1.0, 1.0)
        self.vert_color   = (0.0, 0.0, 0.0, 1.0)
        self.edge_color   = (0.0, 0.0, 0.0, 1.0)
        self.tri_color    = (1.0, 1.0, 1.0, 0.2)
        if mode == 'SKETCH':
            self.edge_color   = (0.0, 0.5, 1.0, 0.8)
        elif mode == 'EVAL':
            self.center_color = (1.0, 1.0, 1.0, 0.2)
            self.tri_color    = (1.0, 1.0, 1.0, 0.5)


    def build_batches(self):
        self.batches_valid = False
        if not self.geo_valid: return
        if not self.verts_ls: return
        self.batches_valid = True
        # Verts
        self.vert_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": self.verts_ws})
        # Edges
        if self.edge_indices:
            self.edge_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": self.verts_ws}, indices=self.edge_indices)
        # Tris
        if self.tri_indices:
            self.tri_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": self.verts_ws}, indices=self.tri_indices)
        # Center
        if self.center_ws:
            self.center_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [self.center_ws]})


    def draw_3D(self):
        if not isinstance(self.entity, PS_PROPS_Razor_Entity): return
        if self.entity.deleted: return
        if not self.geo_valid: return
        if not self.batches_valid: return

        state = gpu.state
        state.blend_set('ALPHA')
        if self.tri_batch:
            UNIFORM_COLOR.uniform_float("color", self.tri_color)
            self.tri_batch.draw(UNIFORM_COLOR)
        if self.edge_batch:
            state.line_width_set(3)
            UNIFORM_COLOR.uniform_float("color", self.edge_color)
            self.edge_batch.draw(UNIFORM_COLOR)
        if self.vert_batch:
            state.point_size_set(4)
            UNIFORM_COLOR.uniform_float("color", self.vert_color)
            self.vert_batch.draw(UNIFORM_COLOR)
        if self.center_batch:
            state.point_size_set(4)
            UNIFORM_COLOR.uniform_float("color", self.center_color)
            self.center_batch.draw(UNIFORM_COLOR)
        state.line_width_set(1)
        state.point_size_set(1)
        state.blend_set('NONE')
