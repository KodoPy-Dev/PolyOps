########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import math
from collections import deque
from math import cos, sin, radians
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from mathutils.geometry import distance_point_to_plane, intersect_line_plane, intersect_point_line
from . import math3
from .addon import user_prefs
from .context import set_component_selection, object_mode_toggle_start, object_mode_toggle_end
from .curve import create as create_curve
from .graphics import COLORS
from .object import parent_object
from .poly_fade import init as init_poly_fade
from .vec_fade import init as init_vec_fade

########################•########################
"""                 CONSTANTS                 """
########################•########################

EPSILON = 0.0001
DEG_01 = radians(1)
DEG_15 = radians(15)
DEG_30 = radians(30)
DEG_45 = radians(45)
DEG_60 = radians(60)
MAT_IDENTITY = Matrix.Identity(4)
VEC3_ZERO = Vector((0,0,0))

########################•########################
"""                   MANAGE                  """
########################•########################

def open_bmesh(context, obj):
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        bm = None
        if obj.data.is_editmode:
            bm = bmesh.from_edit_mesh(obj.data)
        else:
            bm = bmesh.new(use_operators=True)
            bm.from_mesh(obj.data, face_normals=True, vertex_normals=True, use_shape_key=False, shape_key_index=0)
        if ensure_bmesh_type_tables_normals_selections(bm):
            return bm
    return None


def close_bmesh(context, obj, bm):
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if ensure_bmesh_normals_selections(bm):
            if bm.is_wrapped and obj.data.is_editmode:
                bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
            elif not bm.is_wrapped and not obj.data.is_editmode:
                bm.to_mesh(obj.data)
                obj.data.calc_loop_triangles()
    if isinstance(bm, bmesh.types.BMesh):
        bm.free()
    bm = None


def close_bmesh_no_update(bm):
    if isinstance(bm, bmesh.types.BMesh):
        bm.free()
    bm = None
    del bm


def ensure_bmesh_type_tables_normals_selections(bm):
    if isinstance(bm, bmesh.types.BMesh) and bm.is_valid:
        tool_sel_mode = bpy.context.tool_settings.mesh_select_mode
        bm.select_mode = {mode for mode, sel in zip(['VERT', 'EDGE', 'FACE'], tool_sel_mode) if sel}
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()
        bm.select_history.validate()
        bm.select_flush_mode()
        bm.normal_update()
        return True
    return False


def ensure_bmesh_normals_selections(bm):
    if isinstance(bm, bmesh.types.BMesh) and bm.is_valid:
        tool_sel_mode = bpy.context.tool_settings.mesh_select_mode
        bm.select_mode = {mode for mode, sel in zip(['VERT', 'EDGE', 'FACE'], tool_sel_mode) if sel}
        bm.select_flush_mode()
        bm.normal_update()
        return True
    return False


def bmesh_instance_valid(bm):
    if isinstance(bm, bmesh.types.BMesh):
        if bm.is_valid:
            return True
    return False

########################•########################
"""                  QUERIES                  """
########################•########################

def query_sel_vert_indices(obj):
    '''
    RET : LIST -> of Vert Indices if Vert Selected
    '''
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if obj.data.is_editmode:
            obj.update_from_editmode()
        return [v.index for v in obj.data.vertices if v.select]
    return []


def query_sel_edge_indices(obj):
    '''
    RET : LIST -> of Edge Indices if Edge Selected
    '''
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if obj.data.is_editmode:
            obj.update_from_editmode()
        return [e.index for e in obj.data.edges if e.select]
    return []


def query_sel_polygon_indices(obj):
    '''
    RET : LIST -> of Polygon Indices if Polygon Selected
    '''
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if obj.data.is_editmode:
            obj.update_from_editmode()
        return [p.index for p in obj.data.polygons if p.select]
    return []


def query_any_sel_verts(objs=[]):
    '''
    RET : BOOL -> if any Vert is Selected
    '''
    for obj in objs:
        if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
            if obj.data.is_editmode:
                obj.update_from_editmode()
            for vert in obj.data.vertices:
                if vert.select:
                    return True
    return False


def query_any_sel_edges(objs=[]):
    '''
    RET : BOOL -> if any Edge is Selected
    '''
    for obj in objs:
        if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
            if obj.data.is_editmode:
                obj.update_from_editmode()
            for edge in obj.data.edges:
                if edge.select:
                    return True
    return False


def query_any_sel_faces(objs=[]):
    '''
    RET : BOOL -> if any Face is Selected
    '''
    for obj in objs:
        if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
            if obj.data.is_editmode:
                obj.update_from_editmode()
            for face in obj.data.polygons:
                if face.select:
                    return True
    return False


def query_vert_indices_from_boundary_or_wire(context, obj):
    '''
    RET : LIST -> of Vert Indices if Vert is Boundary or Wire and not Hidden
    '''
    bm = open_bmesh(context, obj)
    if not bm: return []
    indices = [vert.index for vert in bm.verts if vert.is_valid and (not vert.hide) and (vert.is_boundary or vert.is_wire)]
    bm.free()
    bm = None
    del bm
    return indices


def query_for_faces_containing_verts(bm, target_verts=[], min_match_count=3):
    '''
    RET : LIST -> of Faces that contain min_match_count in target_verts
    '''
    if isinstance(bm, bmesh.types.BMesh):
        vertex_set = set(target_verts)
        matching_faces = []
        for face in bm.faces:
            if len(vertex_set.intersection({vert for vert in face.verts})) >= min_match_count:
                matching_faces.append(face)
        return matching_faces
    return []


def query_any_polygons_shaded_smooth(obj):
    '''
    RET : BOOL -> if any of the Polygons are shaded smooth
    '''
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if obj.data.is_editmode:
            obj.update_from_editmode()
        return any([p.use_smooth for p in obj.data.polygons])
    return False

########################•########################
"""                  CREATE                   """
########################•########################

def create_vert(bm, point=Vector((0,0,0))):
    if isinstance(point, Vector) and len(point) == 3:
        return bm.verts.new(point)
    return None


def create_verts(bm, points=[]):
    return [bm.verts.new(p) for p in points if isinstance(p, Vector) and len(p) == 3]


def create_edge(bm, vert_1=None, vert_2=None):
    if not isinstance(vert_1, bmesh.types.BMVert) or not vert_1.is_valid:
        return None
    if not isinstance(vert_2, bmesh.types.BMVert) or not vert_2.is_valid:
        return None
    return bm.edges.new((vert_1, vert_2))


def create_edges(bm, vert_pairs=[]):
    created = []
    for vert_pair in vert_pairs:
        valid = False
        if isinstance(vert_pair, (tuple, list)):
            if len(vert_pair) == 2:
                v1, v2 = vert_pair
                if isinstance(v1, bmesh.types.BMVert) and v1.is_valid:
                    if isinstance(v2, bmesh.types.BMVert) and v2.is_valid:
                        valid = True
        if valid:
            created.append(bm.edges.new(vert_pair))
    return created


def create_face(bm, verts=[]):
    if not all(isinstance(vert, bmesh.types.BMVert) and vert.is_valid for vert in verts):
        return None
    return bm.faces.new(verts)


def create_circle(bm, location=Vector((0,0,0)), radius=1, cap_ends=True, segments=32):
    bmesh.ops.create_circle(
        bm,
        cap_ends=cap_ends,
        cap_tris=False,
        segments=segments,
        radius=radius,
        matrix=Matrix.Translation(location),
        calc_uvs=False)


def create_rectangle(bm, p1=Vector((0,0,0)), p2=Vector((0,0,0)), p3=Vector((0,0,0)), p4=Vector((0,0,0)), face_fill=True):
    v1 = bm.verts.new(p1)
    v2 = bm.verts.new(p2)
    v3 = bm.verts.new(p3)
    v4 = bm.verts.new(p4)
    if face_fill:
        bm.faces.new((v1, v2, v3, v4))
    else:
        e1 = bm.edges.new((v1, v2))
        e2 = bm.edges.new((v2, v3))
        e3 = bm.edges.new((v3, v4))
        e4 = bm.edges.new((v4, v1))

########################•########################
"""                  SHADING                  """
########################•########################

def shade_recalc_normals(bm):
    if isinstance(bm, bmesh.types.BMesh):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

########################•########################
"""                   LAYERS                  """
########################•########################

def layer_from_bmesh(bm, elem_type='', data_type='', layer_name=''):
    '''
    IFO : Not all layers options implemented
    '''
    if isinstance(bm, bmesh.types.BMesh):
        if elem_type == 'EDGE':
            if data_type == 'FLOAT':
                if layer_name in bm.edges.layers.float.keys():
                    return bm.edges.layers.float[layer_name]
                return bm.edges.layers.float.new(layer_name)
        if elem_type == 'VERT':
            if data_type == 'FLOAT':
                if layer_name in bm.verts.layers.float.keys():
                    return bm.verts.layers.float[layer_name]
                return bm.verts.layers.float.new(layer_name)


def layer_deform_vert_map(context, obj, remove_empty=False):
    '''
    RET : {Vert Index : {V-Group Name : Weight}}
    '''
    bm = open_bmesh(context, obj)
    if not bm: return
    obj_vgroups = obj.vertex_groups
    vgroup_weights = {v.index: {} for v in bm.verts}
    bm.verts.layers.deform.verify()
    deform = bm.verts.layers.deform.active
    for vert in bm.verts:
        for vgroup_index, weight in vert[deform].items():
            vgroup_name = obj_vgroups[vgroup_index].name
            if vgroup_name not in vgroup_weights[vert.index]:
                vgroup_weights[vert.index][vgroup_name] = weight
            else:
                vgroup_weights[vert.index][vgroup_name] += weight
    if remove_empty:
        vgroup_weights = {k: v for k, v in vgroup_weights.items() if v}
    close_bmesh(context, obj, bm)
    del bm
    return vgroup_weights

########################•########################
"""                INTERSECTIONS              """
########################•########################

def edge_verts_are_in_plane(edge, plane_co=Vector((0,0,0)), plane_no=Vector((1,0,0)), epsilon=EPSILON):
    if abs(distance_point_to_plane(edge.verts[0].co, plane_co, plane_no)) <= epsilon:
        if abs(distance_point_to_plane(edge.verts[1].co, plane_co, plane_no)) <= epsilon:
            return True
    return False


def vert_in_plane(vert, plane_co=Vector((0,0,0)), plane_no=Vector((1,0,0)), epsilon=EPSILON):
    if abs(distance_point_to_plane(vert.co, plane_co, plane_no)) <= epsilon:
        return True
    return False


def verts_in_planes(bm, plane_co=Vector((0,0,0)), plane_normals=[], only_center_line=True, epsilon=EPSILON):
    '''
    Ret : Vertices along the plane or if not only center line, return everything on or below the plane
    '''
    verts = set()
    distance_point_to_plane = geometry.distance_point_to_plane
    for vert in bm.verts:
        for plane_no in plane_normals:
            if only_center_line:
                if abs(distance_point_to_plane(vert.co, plane_co, plane_no)) <= epsilon:
                    verts.add(vert)
            else:
                if distance_point_to_plane(vert.co, plane_co, plane_no) <= epsilon:
                    verts.add(vert)
    return list(verts)


def geom_in_plane(bm, plane_co=Vector((0,0,0)), plane_no=Vector((1,0,0)), only_center_line=True, epsilon=EPSILON):
    verts = verts_in_planes(bm, plane_co=plane_co, plane_normals=[plane_no], only_center_line=only_center_line)
    edges = set()
    faces = set()
    for vert in verts:
        for edge in vert.link_edges:
            if edge.other_vert(vert) in verts:
                edges.add(edge)
            for face in edge.link_faces:
                if all([v in verts for v in face.verts]):
                    faces.add(face)
    return list(verts), list(edges), list(faces)

########################•########################
"""                 PROJECTIONS               """
########################•########################

def project_verts_to_plane(plane_co=Vector((0,0,0)), plane_no=Vector((0,0,1)), verts=[]):
    for vert in verts:
        p1 = vert.co
        p2 = p1 + plane_no * distance_point_to_plane(vert.co, plane_co, plane_no)
        point = intersect_line_plane(p1, p2, plane_co, plane_no, False)
        if point:
            vert.co = point

########################•########################
"""                   MARKS                   """
########################•########################

def assign_edge_marks(context, obj, recalc=True, recalc_angle=DEG_30, recalc_append=True, mark_boundary=True, omit_x_axis=True, omit_y_axis=False, omit_z_axis=False, seam=True, sharp=True, e_crease=0, b_weight=0, show_poly_fade=False):
    bm = open_bmesh(context, obj)
    if not bm: return
    smooth = not sharp
    bevel_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='bevel_weight_edge')
    crease_edge_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='crease_edge')
    # Poly Fade
    poly_fade_lines = []
    mat_ws = obj.matrix_world
    # Auto Assign
    if recalc:
        for edge in bm.edges:
            if not edge.is_valid:
                continue
            mark_edge = edge.calc_face_angle(-1) >= recalc_angle
            if mark_boundary and edge.is_boundary:
                mark_edge = True
            if omit_x_axis and edge_verts_are_in_plane(edge, plane_no=Vector((1,0,0))):
                mark_edge = False
            if omit_y_axis and edge_verts_are_in_plane(edge, plane_no=Vector((0,1,0))):
                mark_edge = False
            if omit_z_axis and edge_verts_are_in_plane(edge, plane_no=Vector((0,0,1))):
                mark_edge = False
            if mark_edge:
                edge.seam = seam
                edge.smooth = smooth
                edge[bevel_layer] = b_weight
                edge[crease_edge_layer] = e_crease
                # Poly Fade
                if show_poly_fade:
                    vert_1, vert_2 = edge.verts
                    vert_1_co = vert_1.co.copy()
                    vert_2_co = vert_2.co.copy()
                    if vert_1.is_valid:
                        poly_fade_lines.append(mat_ws @ vert_1_co)
                    if vert_2.is_valid:
                        poly_fade_lines.append(mat_ws @ vert_2_co)
            else:
                if not recalc_append:
                    edge.seam = False
                    edge.smooth = True
                    edge[bevel_layer] = 0
                    edge[crease_edge_layer] = 0
    # Manual Assign
    else:
        # EDGES
        for edge in bm.edges:
            if not edge.is_valid:
                continue
            if edge.select:
                edge.seam = seam
                edge.smooth = smooth
                edge[bevel_layer] = b_weight
                edge[crease_edge_layer] = e_crease
                # Poly Fade
                if show_poly_fade:
                    vert_1, vert_2 = edge.verts
                    vert_1_co = vert_1.co.copy()
                    vert_2_co = vert_2.co.copy()
                    if vert_1.is_valid:
                        poly_fade_lines.append(mat_ws @ vert_1_co)
                    if vert_2.is_valid:
                        poly_fade_lines.append(mat_ws @ vert_2_co)
    # Poly Fade
    if show_poly_fade and poly_fade_lines:
        init_poly_fade(obj, lines=poly_fade_lines)
    close_bmesh(context, obj, bm)
    del bm


def assign_vert_marks(context, obj, v_crease=0, mark_boundary=True, omit_x_axis=True, omit_y_axis=False, omit_z_axis=False):
    bm = open_bmesh(context, obj)
    if not bm: return
    vert_crease_layer = layer_from_bmesh(bm, elem_type='VERT', data_type='FLOAT', layer_name='crease_vert')
    for vert in bm.verts:
        mark_vert = vert.select
        if mark_boundary and any([edge.is_boundary for edge in vert.link_edges]):
            mark_vert = True
        if omit_x_axis and vert_in_plane(vert, plane_no=Vector((1,0,0))):
            mark_vert = False
        if omit_y_axis and vert_in_plane(vert, plane_no=Vector((0,1,0))):
            mark_vert = False
        if omit_z_axis and vert_in_plane(vert, plane_no=Vector((0,0,1))):
            mark_vert = False
        if mark_vert:
            vert[vert_crease_layer] = v_crease
    close_bmesh(context, obj, bm)
    del bm


def remove_edge_marks(context, obj, selected_only=True, seam=True, sharp=True, e_crease=True, b_weight=True):
    bm = open_bmesh(context, obj)
    if not bm: return

    bevel_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='bevel_weight_edge')
    crease_edge_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='crease_edge')
    # Remove Selected
    if selected_only:
        for edge in bm.edges:
            if edge.select:
                if seam:
                    edge.seam = False
                if sharp:
                    edge.smooth = True
                if e_crease:
                    edge[bevel_layer] = 0.0
                if b_weight:
                    edge[crease_edge_layer] = 0.0
    # Remove All
    else:
        for edge in bm.edges:
            if seam:
                edge.seam = False
            if sharp:
                edge.smooth = True
            if e_crease:
                edge[bevel_layer] = 0.0
            if b_weight:
                edge[crease_edge_layer] = 0.0
    close_bmesh(context, obj, bm)
    del bm


def remove_vert_marks(context, obj, remove_all=True):
    bm = open_bmesh(context, obj)
    if not bm: return

    vert_crease_layer = layer_from_bmesh(bm, elem_type='VERT', data_type='FLOAT', layer_name='crease_vert')
    # Remove All
    if remove_all:
        for vert in bm.verts:
            vert[vert_crease_layer] = 0.0
    # Remove Selected
    else:
        for vert in bm.verts:
            if vert.select == False: continue
            vert[vert_crease_layer] = 0.0
    close_bmesh(context, obj, bm)
    del bm

########################•########################
"""                 SELECTIONS                """
########################•########################

def select_marks(context, obj, sharp_edges=True, seamed_edges=True, bevel_edges=True, crease_edges=True, creased_verts=True):
    bm = open_bmesh(context, obj)
    if not bm: return

    bevel_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='bevel_weight_edge')
    crease_edge_layer = layer_from_bmesh(bm, elem_type='EDGE', data_type='FLOAT', layer_name='crease_edge')
    vert_crease_layer = layer_from_bmesh(bm, elem_type='VERT', data_type='FLOAT', layer_name='crease_vert')
    for edge in bm.edges:
        if sharp_edges == True:
            if edge.smooth == False:
                edge.select = True
        if seamed_edges == True:
            if edge.seam == True:
                edge.select = True
        if bevel_edges == True:
            if edge[bevel_layer] > 0.0:
                edge.select = True
        if crease_edges == True:
            if edge[crease_edge_layer] > 0.0:
                edge.select = True
    if creased_verts == True:
        for vert in bm.verts:
            if vert[vert_crease_layer] > 0.0:
                vert.select = True
    close_bmesh(context, obj, bm)
    del bm


def select_boundary_of_faces(bm, faces=[]):
    boundary_edges = set()
    for face in faces:
        for edge in face.edges:
            if edge.is_boundary:
                edge.select = True
                boundary_edges.add(edge)
                continue
            for edge_face in edge.link_faces:
                if edge_face not in faces:
                    edge.select = True
                    boundary_edges.add(edge)
                    break
    return list(boundary_edges)


def select_boundary(context, obj, omit_axis_x=True, omit_axis_y=False, omit_axis_z=False, flip_axis_x=True, flip_axis_y=False, flip_axis_z=False):
    bm = open_bmesh(context, obj)
    if not bm: return

    # Capture boundary of selected faces
    sel_faces = [face for face in bm.faces if face.select]
    boundary_edges = []
    # Everything Selected
    if len(sel_faces) == len(bm.faces):
        set_component_selection(context, values=(False, True, False))
        select_all_elements(bm, select=False)
        for edge in bm.edges:
            if edge.is_boundary:
                edge.select = True
    else:
        # No faces selected --> check if verts are selected
        if not sel_faces:
            sel_verts = [vert for vert in bm.verts if vert.select]
            if sel_verts:
                sel_faces = faces_connected_to_verts(verts=sel_verts)
        set_component_selection(context, values=(False, True, False))
        select_all_elements(bm, select=False)
        # Select boundary of selection
        if sel_faces:
            edges = select_boundary_of_faces(bm, faces=sel_faces)
            boundary_edges.extend(edges)
        # Select boundary edges
        else:
            for edge in bm.edges:
                if edge.is_boundary or any([face.hide for face in edge.link_faces]):
                    edge.select = True
                    boundary_edges.append(edge)
    # Get axis vertices to remove
    if omit_axis_x or omit_axis_y or omit_axis_z:
        plane_normals = []
        if omit_axis_x:
            if flip_axis_x:
                plane_normals.append(Vector((-1,0,0)))
            else:
                plane_normals.append(Vector((1,0,0)))
        if omit_axis_y:
            if flip_axis_y:
                plane_normals.append(Vector((0,-1,0)))
            else:
                plane_normals.append(Vector((0,1,0)))
        if omit_axis_z:
            if flip_axis_z:
                plane_normals.append(Vector((0,0,-1)))
            else:
                plane_normals.append(Vector((0,0,1)))
        if plane_normals:
            verts_to_omit = verts_in_planes(bm, Vector((0,0,0)), plane_normals, only_center_line=False)
            verts_to_omit = set(verts_to_omit)
            for edge in boundary_edges:
                if (edge.verts[0] in verts_to_omit) and (edge.verts[1] in verts_to_omit):
                    edge.select = False
    close_bmesh(context, obj, bm)
    del bm


def select_all_elements(bm, select=True):
    for vert in bm.verts:
        vert.select = select
    bm.select_flush(select)


def select_flush(bm, select=True):
    bm.select_flush(select)


def select_axis_verts(context, obj, x=True, y=False, z=False, only_center_line=True, invert=False):
    bm = open_bmesh(context, obj)
    if not bm: return

    set_component_selection(context, values=(True, False, False))
    select_all_elements(bm, select=False)
    plane_co = Vector((0,0,0))
    plane_normals = []
    if x: plane_normals.append( Vector((-1 if invert else 1, 0, 0)) )
    if y: plane_normals.append( Vector((0, -1 if invert else 1, 0)) )
    if z: plane_normals.append( Vector((0, 0, -1 if invert else 1)) )
    verts = verts_in_planes(bm, plane_co, plane_normals, only_center_line)
    if only_center_line and invert:
        verts = [v for v in bm.verts if v not in verts]
    for vert in verts:
        vert.select_set(True)
    bm.select_flush(True)
    close_bmesh(context, obj, bm)
    del bm

########################•########################
"""                  TRACERS                  """
########################•########################

def trace_edge_by_angle(bm, edge, vert, step_limit=150, angle_limit=DEG_30, break_at_intersections=False, break_at_boundary=False):
    # Validate
    if vert not in edge.verts:
        return []
    # Edge Setup
    edges = set()
    verts = set()
    verts.add(edge.other_vert(vert))
    next_vert_breaks = False
    # Loop to Limit
    for i in range(step_limit):
        # Boundary
        if break_at_boundary:
            if edge.is_boundary:
                break
        # Add
        edges.add(edge)
        verts.add(vert)
        # Next Edge by Largest Angle
        delta_angle = 0
        next_edge = None
        for link_edge in vert.link_edges:
            if link_edge in edges:
                continue
            # Vert Coords
            v1 = edge.other_vert(vert).co
            v2 = vert.co
            v3 = link_edge.other_vert(vert).co
            # Normals
            n1 = (v1 - v2).normalized()
            n2 = (v3 - v2).normalized()
            if n1.length == 0 or n2.length == 0:
                continue
            # Angle
            angle = n1.angle(n2, math.pi)
            # Limit
            if math.pi - angle > angle_limit:
                continue
            # Delta
            if angle > delta_angle:
                delta_angle = angle
                next_edge = link_edge
        # No next edges
        if not next_edge:
            break
        # Set for next
        edge = next_edge
        vert = edge.other_vert(vert)
        # Intersection
        if next_vert_breaks:
            break
        if break_at_intersections:
            if vert in verts:
                next_vert_breaks = True
    return list(edges)

########################•########################
"""                  TAGGING                  """
########################•########################

def clear_all_tags(bm):
    for vert in bm.verts: vert.tag = False
    for edge in bm.edges: edge.tag = False
    for face in bm.faces: face.tag = False


def clear_vert_tags(bm):
    for vert in bm.verts: vert.tag = False


def clear_edge_tags(bm):
    for edge in bm.edges: edge.tag = False


def clear_face_tags(bm):
    for face in bm.faces: face.tag = False


def set_elem_tags(elems=[], value=False):
    for elem in elems:
        elem.tag = value


def clean_tagged_geo(bm):
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.tag], dist=EPSILON)
    bmesh.ops.dissolve_degenerate(bm, dist=EPSILON, edges=[e for e in bm.edges if e.tag])
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if f.tag])
    bmesh.ops.dissolve_limit(bm, angle_limit=radians(1), use_dissolve_boundaries=False, verts=[v for v in bm.verts if v.tag], edges=[e for e in bm.edges if e.tag])

########################•########################
"""                CONNECTIONS                """
########################•########################

def verts_connected_to_vert(vert):
    return [edge.other_vert(vert) for edge in vert.link_edges]


def verts_connected_to_vert_inclusive(vert, included_verts=[]):
    return [v for e in vert.link_edges for v in e.verts if v != vert and v in included_verts]    


def shared_vert_between_connected_edges(edge_1, edge_2):
    if edge_1.verts[0] in edge_2.verts: return edge_1.verts[0]
    elif edge_1.verts[1] in edge_2.verts: return edge_1.verts[1]
    return None


def edges_polygon_count_equal_to(edges=[], poly_count=0):
    return all([len(e.link_faces) == poly_count] for e in edges)


def edges_connected_to_vert(vert, exclude=[]):
    return [edge for edge in vert.link_edges if edge not in exclude]


def edges_connected_to_verts(verts):
    return list(set([e for v in verts for e in v.link_edges]))


def edges_connected_to_edge(edge):
    return set([e for e in edge.verts[0].link_edges[:] + edge.verts[1].link_edges[:] if e != edge])


def faces_connected_to_vert(vert, exclude=[]):
    return [face for face in vert.link_faces if face not in exclude]


def faces_connected_to_verts(verts):
    return list(set([f for v in verts for f in v.link_faces]))

########################•########################
"""                   LOOPS                   """
########################•########################

def loop_from_edge_vert(edge, vert):
    for loop in edge.link_loops:
        if loop.vert == vert:
            return loop
    return None


def loops_connected_to_loop_vert(loop):
    return loop.edge.other_vert(loop.vert).link_loops


def polygon_loops_from_edge_vert(edge, vert):
    loop = loop_from_edge_vert(edge, vert)
    if not loop: return []
    loops = []
    while True:
        loops.append(loop)
        loop = loop.link_loop_next
        if loop.edge == edge:
            return loops


def polygon_loops_from_loop(starting_loop):
    loops = []
    loop = starting_loop
    while True:
        loops.append(loop)
        loop = loop.link_loop_next
        if loop == starting_loop:
            return loops


def radial_polygon_loops_from_edge_vert(edge, vert):
    loop = loop_from_edge_vert(edge, vert)
    if not loop: return []
    loop = loop.link_loop_radial_next
    loops = []
    while True:
        loops.append(loop)
        loop = loop.link_loop_next
        if loop.edge == edge:
            return loops


def radial_polygon_loops_from_loop(starting_loop):
    starting_loop = starting_loop.link_loop_radial_next
    loops = []
    loop = starting_loop
    while True:
        loops.append(loop)
        loop = loop.link_loop_next
        if loop == starting_loop:
            return loops


def get_a_boundary_loop(faces):
    for face in faces:
        for loop in face.loops:
            if loop.edge.is_boundary:
                return loop
            if loop.link_loop_radial_next.face not in faces:
                return loop
    return None

########################•########################
"""                  ISLANDS                  """
########################•########################

def face_islands_from_faces(faces=[]):
    if not faces:
        return []

    visited = {face: False for face in faces}

    def get_island(face):
        island = set()
        queue = [face]
        while queue:
            current_face = queue.pop()
            island.add(current_face)
            visited[current_face] = True
            for loop in current_face.loops:
                next_face = loop.link_loop_radial_next.face
                if next_face in faces and not visited[next_face]:
                    queue.append(next_face)
        return island

    islands = []
    for face in faces:
        if not visited[face]:
            island = get_island(face)
            islands.append(island)
    return islands


def vert_islands_from_seperation(bm):
    if not bm.verts:
        return []
    bm.verts.ensure_lookup_table()
    islands = []
    visited = set()
    for vert in bm.verts:
        if vert in visited:
            continue
        island = []
        que = deque([vert])
        while que:
            vert = que.popleft()
            if vert in visited:
                continue
            visited.add(vert)
            island.append(vert)
            que.extend([v for e in vert.link_edges for v in e.verts if v not in visited])
        islands.append(island)
    return islands


def vert_island_containing_vert(vert):
    if not isinstance(vert, bmesh.types.BMVert):
        return []
    island = []
    visited = set()
    que = deque([vert])
    while que:
        vert = que.popleft()
        if vert in visited:
            continue
        visited.add(vert)
        que.extend([v for e in vert.link_edges for v in e.verts if v not in visited])
        island.append(vert)
    return island


def perimeter_edges_from_faces(faces=[], convert_to_list=True):
    edges = set()
    for face in faces:
        for edge in face.edges:
            if edge.is_boundary:
                edges.add(edge)
            else:
                for edge_face in edge.link_faces:
                    if edge_face not in faces:
                        edges.add(edge)
                        break
    if convert_to_list:
        return list(edges)
    return edges


def connected_faces_to_face_by_angle(face, angle=DEG_15):
    island = set()
    que = deque([face])
    while que:
        face = que.popleft()
        if face in island:
            continue
        island.add(face)
        for edge in face.edges:
            if edge.is_boundary:
                continue
            edge_angle = edge.calc_face_angle(None)
            if angle is None:
                continue
            if edge_angle <= angle:
                for edge_face in edge.link_faces:
                    if edge_face != face:
                        que.append(edge_face)
    return list(island)

########################•########################
"""                DIMENSIONAL                """
########################•########################

def sum_length_of_edges(edges=[]):
    return sum([e.calc_length() for e in edges])


def triangle_coords_from_faces(bm, faces=[], matrix=None):
    if not isinstance(bm, bmesh.types.BMesh):
        return {}
    faces_set = set(faces)
    if not faces_set:
        return []
    bm.faces.ensure_lookup_table()
    triangles = bm.calc_loop_triangles()
    filtered_triangles = [tri for tri in triangles if tri[0].face in faces_set]
    if matrix:
        return [matrix @ loop.vert.co for tri_loops in filtered_triangles for loop in tri_loops]
    return [loop.vert.co.copy() for tri_loops in filtered_triangles for loop in tri_loops]


def triangle_coords_from_face_indices(bm, face_indices=[], matrix=None):
    if not isinstance(bm, bmesh.types.BMesh):
        return {}
    face_indices_set = set(face_indices)
    if not face_indices_set:
        return {}
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    triangles = bm.calc_loop_triangles()
    filtered_triangles = [tri for tri in triangles if tri[0].face.index in face_indices_set]
    if matrix:
        return [matrix @ loop.vert.co for tri_loops in filtered_triangles for loop in tri_loops]
    return [loop.vert.co.copy() for tri_loops in filtered_triangles for loop in tri_loops]


def closest_vert_to_vert_on_face(face, target_vert):
    delta = math.inf
    closest_vert = None
    for vert in face.verts:
        if vert != target_vert:
            distance = (target_vert.co - vert.co).length
            if distance < delta:
                delta = distance
                closest_vert = vert
    return closest_vert


def farthest_vert_to_vert_on_face(face, target_vert):
    delta = -math.inf
    closest_vert = None
    for vert in face.verts:
        if vert != target_vert:
            distance = (target_vert.co - vert.co).length
            if distance > delta:
                delta = distance
                closest_vert = vert
    return closest_vert

########################•########################
"""                  CHAINS                   """
########################•########################

def vert_chain_from_edge_chain(edge_chain=[]):
    if not edge_chain: return []
    if len(edge_chain) == 1:
        return [v for v in edge_chain[0].verts]
    if len(edge_chain) == 2:
        v2 = shared_vert_between_connected_edges(edge_chain[0], edge_chain[1])
        v1 = edge_chain[0].other_vert(v2)
        v3 = edge_chain[1].other_vert(v2)
        return [v1, v2, v3]

    vert_chain = []
    curr_vert = None

    if edge_chain[0].verts[0] in edge_chain[1].verts:
        curr_vert = edge_chain[0].verts[1]
    else:
        curr_vert = edge_chain[0].verts[0]

    vert_chain.append(curr_vert)
    for edge in edge_chain:
        vert_chain.append(edge.other_vert(curr_vert))
        curr_vert = edge.other_vert(curr_vert)

    return vert_chain


def vert_chain_to_distance_map(vert_chain=[]):
    '''
    Ret : {vert: (distance, vert coordinate)}
    Ifo : Distance is the accumulated distancce down each edge || Coordinate is the verts current position
    '''
    if len(vert_chain) == 0:
        return {}
    if len(vert_chain) == 1:
        return {vert_chain[0]: (0, vert_chain[0].co.copy())}
    distance_map = {vert_chain[0]: (0, vert_chain[0].co.copy())}
    delta = 0
    for i in range(len(vert_chain) - 1):
        curr_vert = vert_chain[i]
        next_vert = vert_chain[i + 1]
        delta += (curr_vert.co - next_vert.co).length
        distance_map[curr_vert] = (delta, curr_vert.co.copy())
    return distance_map


def edge_chains_from_unsorted_edges(edges=[]):
    if not edges: return []

    edge_chains = []
    traversed = []

    while True:
        remaining = [e for e in edges if e not in traversed]
        if not remaining: break

        edge = remaining[0]
        conn_a = [e for e in edges_connected_to_vert(edge.verts[0]) if e != edge and e in edges]
        conn_b = [e for e in edges_connected_to_vert(edge.verts[1]) if e != edge and e in edges]
        
        # --- Single edge cases --- #
        if len(conn_a) == len(conn_b):
            if len(conn_a) == 0 or len(conn_a) > 1:
                edge_chains.append([edge])
                traversed.append(edge)
                continue
        if len(conn_a) > 1 and len(conn_b) == 0:
            edge_chains.append([edge])
            traversed.append(edge)
            continue
        if len(conn_b) > 1 and len(conn_a) == 0:
            edge_chains.append([edge])
            traversed.append(edge)
            continue

        # --- Follow Chain --- #
        chain = [edge]
        stack = []
        if len(conn_a) == 1:
            stack.append(conn_a[0])
        if len(conn_b) == 1:
            stack.append(conn_b[0])

        while stack:
            queued_edge = stack.pop()
            chain.append(queued_edge)
            for i in range(2):
                connections = [e for e in queued_edge.verts[i].link_edges if e != queued_edge and e in edges]
                if len(connections) == 1:
                    connected_edge = connections[0]
                    if connected_edge not in chain:
                        stack.append(connected_edge)

        # Assign Edge Chain
        edge_chains.append(edge_chain_from_connected_edges(chain))
        traversed.extend(chain)
    
    return edge_chains


def edge_chain_from_connected_edges(edges=[]):
    if not edges: return []

    sorted_edges = []
    curr_edge = None
    curr_vert = None

    # Create a map of vertex to edges
    vert_edge_map = {}
    for edge in edges:
        for vert in edge.verts:
            if vert not in vert_edge_map:
                vert_edge_map[vert] = []
            vert_edge_map[vert].append(edge)

    # Find an edge starting from an endpoint if possible
    for vert, vert_edges in vert_edge_map.items():
        if len(vert_edges) == 1:  # This vertex is an endpoint
            curr_edge = vert_edges[0]
            curr_vert = vert
            break

    # If no endpoint is found, start from any edge
    if curr_edge is None:
        curr_edge = edges[0]
        curr_vert = curr_edge.verts[0]

    sorted_edges.append(curr_edge)
    # Determine the initial direction
    curr_vert = curr_edge.other_vert(curr_vert)

    while True:
        next_edges = [e for e in curr_vert.link_edges if e in edges and e not in sorted_edges]
        if next_edges:
            curr_edge = next_edges[0]
            sorted_edges.append(curr_edge)
            curr_vert = curr_edge.other_vert(curr_vert)
        else:
            break

    return sorted_edges


def edge_chain_dissolve_iso_verts(bm, edge_chain=[], dissolve_distance=EPSILON):
    '''
    Ops : Dissolve verts that only have edges on the chain and are close enough to another vert
    '''
    vert_chain = vert_chain_from_edge_chain(edge_chain)
    dissole_verts = set()
    for vert in vert_chain:
        if len( [ e for e in vert.link_edges if e not in edge_chain ] ) > 0: continue
        conn_verts = verts_connected_to_vert(vert)
        for conn_vert in conn_verts:
            if (vert.co - conn_vert.co).magnitude <= dissolve_distance:
                dissole_verts.add(vert)
    bmesh.ops.dissolve_verts(bm, verts=list(dissole_verts), use_face_split=False, use_boundary_tear=False)


def edge_chain_merge_junctions(bm, edge_chain=[], flip=False, merge_distance=EPSILON):
    '''
    Ops : Merge verts on the edge chain nearest to verts from a side
    Ret : True on Completion else False
    Ifo : First call to speed things up -> edge_chain_validator(edge_chain, check_2_faces=True)
    '''
    side_a_faces, side_b_faces = edge_chain_faces_from_sides(edge_chain)
    if side_a_faces is None or side_b_faces is None:
        return False
    faces = side_b_faces if flip else side_a_faces
    chain_edges = set(edge_chain)
    all_verts = {v for e in chain_edges for v in e.verts}
    frozen_verts = {v for f in faces for e in f.edges if e not in chain_edges for v in e.verts if v in all_verts}
    movable_verts = {v for v in all_verts if v not in frozen_verts}
    merge_map = {v: None for v in movable_verts}
    for vert in movable_verts:
        edges = {e for e in vert.link_edges if e in chain_edges}
        delta_dist = math.inf
        merge_to_vert = None
        for edge in edges:
            lead_vert = edge.other_vert(vert)
            curr_edge = edge
            distance = 0
            while True:
                if lead_vert == vert:
                    break
                distance += curr_edge.calc_length()
                if distance > merge_distance:
                    break
                if lead_vert in frozen_verts:
                    if delta_dist > distance:
                        delta_dist = distance
                        merge_to_vert = lead_vert
                    break
                for next_edge in lead_vert.link_edges:
                    if next_edge != curr_edge:
                        if next_edge in chain_edges:
                            curr_edge = next_edge
                            lead_vert = next_edge.other_vert(lead_vert)
                            break
        merge_map[vert] = merge_to_vert
    for from_vert, to_vert in merge_map.items():
        if to_vert:
            from_vert.co = to_vert.co
    bmesh.ops.remove_doubles(bm, verts=list(all_verts), dist=0.0001)
    return True


def edge_chain_faces_from_sides(edge_chain=[]):
    '''
    Ret : set, set : 2 sets of faces, one for each side or None, None
    Ifo : dge chain must be valid and each edge needs two faces exactly
    '''
    curr_vert = edge_chain_first_vert(edge_chain)
    # Case : Utils faild
    if not curr_vert: return None, None
    curr_loop = None
    side_a_faces = set()
    side_b_faces = set()
    for edge in edge_chain:
        loop_set = False
        for loop in curr_vert.link_loops:
            if loop.edge == edge:
                curr_loop = loop
                loop_set = True
                break
        # Case : Next vert was incorrect and chain is bad
        if loop_set == False: return None, None
        side_a_faces.add(curr_loop.face)
        side_b_faces.add(curr_loop.link_loop_radial_prev.face)
        curr_vert = edge.other_vert(curr_vert)
    return side_a_faces, side_b_faces


def edge_chain_last_vert(edge_chain=[]):
    if len(edge_chain) == 0: return None
    if len(edge_chain) == 1: return edge_chain[0].verts[1]
    e1 = edge_chain[-1]
    e2 = edge_chain[-2]
    if e1.verts[0] in e2.verts: return e1.verts[1]
    elif e1.verts[1] in e2.verts: return e1.verts[0]
    return None


def edge_chain_first_vert(edge_chain=[]):
    if len(edge_chain) == 0: return None
    if len(edge_chain) == 1: return edge_chain[0].verts[0]
    e1 = edge_chain[0]
    e2 = edge_chain[1]
    if e1.verts[0] in e2.verts: return e1.verts[1]
    elif e1.verts[1] in e2.verts: return e1.verts[0]
    return None


def edge_chain_first_vert_and_loop(edge_chain=[]):
    first_vert = edge_chain_first_vert(edge_chain)
    if first_vert is None: return None, None
    for loop in first_vert.link_loops:
        if loop.edge == first_edge[0]:
            return loop, first_vert
    return None, None


def edge_chain_connected_polygons(edge_chain=[]):
    return list(set([face for edge in edge_chain for face in edge.link_faces]))


def edge_chain_validator(edge_chain=[], check_cyclic=False, check_2_faces=False):
    '''
    Ret : True or False
    '''
    # Case : Empty chain
    if len(edge_chain) == 0:
        return False
    # Case : Deleted Edges
    if any([e.is_valid == False for e in edge_chain]):
        return False
    # Case : Can't be cyclic
    if check_cyclic:
        if len(edge_chain) < 3:
            return False
        v1, v2 = edge_chain[0].verts
        v3, v4 = edge_chain[-1].verts
        if len(set([v1, v2, v3, v4])) > 3:
            return False
    # Case : Not all 2 edges
    if check_2_faces:
        if any([len(e.link_faces) != 2 for e in edge_chain]):
            return False
    # Case : Only one edge
    if len(edge_chain) == 1:
        return True
    curr_vert = edge_chain_first_vert(edge_chain)
    # Case : First 2 edges not connected
    if curr_vert is None:
        return False
    # Case : No connectivity
    for edge in edge_chain:
        if curr_vert not in edge.verts:
            return False
        curr_vert = edge.other_vert(curr_vert)
    return True


def edge_chain_map_from_edges(edges=[]):
    '''
    Ops : Creates sub chains from edge chain when face count changes
    '''

    chains_map = {}
    chains_map['wire_chains'] = edge_chains_from_unsorted_edges([e for e in edges if len(e.link_faces) == 0])
    chains_map['border_chains'] = edge_chains_from_unsorted_edges([e for e in edges if len(e.link_faces) == 1])
    chains_map['dual_face_chains'] = edge_chains_from_unsorted_edges([e for e in edges if len(e.link_faces) == 2])
    return chains_map


def edge_chain_adjacency_edge_map(edge_chain=[]):
    '''
    Ret : Dictionary : KEY = Vert, VAL = Tuple with an edge from its side or none || None on failure
    Ifo : All edges must have 2 faces || Only considers edges connected to the vert in the edge's polygon
    '''
    # Case : No edges
    if len(edge_chain) == 0:
        return None
    # Case : Not all edges have same face count
    if any([len(e.link_faces) != 2 for e in edge_chain]):
        return None
    edge_chain_set = set(edge_chain)
    adj_map = {}
    curr_vert = edge_chain_first_vert(edge_chain)
    curr_loop = None
    side_a_polygon = None
    side_b_polygon = None

    # Case : Bad chain
    if curr_vert is None:
        return None

    # Algo : Walk
    for edge in edge_chain:
        curr_loop = None
        for loop in edge.link_loops:
            if loop.vert == curr_vert:
                curr_loop = loop
                break
        # Case : Bad chain
        if curr_loop is None:
            return None
        side_a_polygon = curr_loop.face
        side_b_polygon = curr_loop.link_loop_radial_prev.face
        side_a_edge = None
        side_b_edge = None

        for other_edge in curr_vert.link_edges:
            # Case : Edge in chain already
            if other_edge in edge_chain_set: continue
            if other_edge in side_a_polygon.edges:
                side_a_edge = other_edge
            elif other_edge in side_b_polygon.edges:
                side_b_edge = other_edge

        adj_map[curr_vert] = (side_a_edge, side_b_edge)
        curr_vert = edge.other_vert(curr_vert)

    # Algo : Capture last vert from edge chain
    side_a_edge = None
    side_b_edge = None
    for other_edge in curr_vert.link_edges:
        # Case : Edge in chain already
        if other_edge in edge_chain_set: continue
        if other_edge in side_a_polygon.edges:
            side_a_edge = other_edge
        elif other_edge in side_b_polygon.edges:
            side_b_edge = other_edge
    adj_map[curr_vert] = (side_a_edge, side_b_edge)

    return adj_map


def edge_chain_adjacency_face_map(edge_chain=[]):
    '''
    Ret : {edge : (face a, face b)} -OR- None
    Ifo : All edges must have exaclty 2 faces
    '''
    # Case : No edges
    if len(edge_chain) == 0:
        return None
    # Case : Edges dont all have 2 polygons
    if not all([len(e.link_faces) == 2 for e in edge_chain]):
        return None
    # Case : Only 1 edge
    if len(edge_chain) == 1:
        f1 = edge_chain[0].link_faces[0]
        f2 = edge_chain[0].link_faces[1]
        return {edge_chain: (f1, f2)}

    curr_vert = edge_chain_first_vert(edge_chain)
    # Case : Edge chain not consistent
    if curr_vert is None:
        return None

    curr_loop = None
    for loop in curr_vert.link_loops:
        if loop.edge == edge_chain[0]:
            curr_loop = loop
            break
    
    adj_map = {}
    for edge in edge_chain:
        curr_vert = edge.other_vert(curr_vert)
        next_loop = None
        for loop in curr_vert.link_loops:
            if loop.edge == edge:
                next_loop = loop
                break
        # Case : Edge chain not consistent
        if next_loop is None:
            return None
        curr_loop = next_loop
        adj_map[edge] = (curr_loop.face, curr_loop.link_loop_radial_prev.face)
    return adj_map


def edge_chain_from_edge_traversal(edges=[], start_vert=None, end_verts=[]):
    '''
    Ret : Edge chain path from the start vert to the first vert in end verts or None on failure
    '''
    # Queue for BFS, stores (current_vert, path_taken) tuples
    queue = deque([(start_vert, [])])
    end_verts_set = set(end_verts)
    visited = set()
    visited.add(start_vert)
    while queue:
        current_vert, path = queue.popleft()
        # If we reach an end vertex, return the path
        if current_vert in end_verts_set:
            return edge_chain_from_connected_edges(path)
        # Explore connected edges
        for edge in current_vert.link_edges:
            if edge in edges:
                next_vert = edge.other_vert(current_vert)
                if next_vert not in visited:
                    visited.add(next_vert)
                    queue.append((next_vert, path + [edge]))
    return None


def edge_chain_slice_map_from_distance(edge_chain=[], start_vert=None, end_verts=[], max_travel_dist=1.0, forward=True):
    '''
    Ret : [ (distnace, vert), ] or None on failure
    '''
    vert_chain = vert_chain_from_edge_chain(edge_chain)
    if not vert_chain: return None
    if start_vert not in vert_chain: return None
    if forward == False: vert_chain.reverse()
    travel_distance = 0
    slice_map = []
    index = vert_chain.index(start_vert)
    curr_vert = start_vert
    cyclic = vert_chain[0] == vert_chain[-1]
    while True:
        index += 1
        if index >= len(vert_chain) - 1:
            if cyclic: index = 0
            else: break
        next_vert = vert_chain[index]
        travel_distance += (curr_vert.co - next_vert.co).magnitude
        if travel_distance > max_travel_dist:
            break
        slice_map.append((travel_distance, next_vert))
        if next_vert == start_vert or next_vert in end_verts:
            break
        curr_vert = next_vert
    return slice_map

########################•########################
"""                BMESH OPS                  """
########################•########################

def remove_doubles_safe(bm, verts=[], dist=EPSILON):
    bmesh.ops.remove_doubles(bm, verts=list(set(v for v in verts if v.is_valid)), dist=dist)


def split_edge_at_center(edge):
    vert = edge.verts[0]
    split_edge, split_vert = bmesh.utils.edge_split(edge, vert, 0.5)
    if isinstance(split_vert, bmesh.types.BMVert):
        if split_vert.is_valid:
            return split_vert
    return None


def split_edge_at_point(edge, point=VEC3_ZERO):
    vert_1 = edge.verts[0]
    vert_2 = edge.verts[1]
    factor = math3.projected_point_line_factor(point, vert_1.co, vert_2.co, clamp_factor=True)
    if factor <= 0:
        return None, None
    elif factor >= 1:
        return None, None
    split_edge, split_vert = bmesh.utils.edge_split(edge, vert_1, factor)
    if isinstance(split_vert, bmesh.types.BMVert):
        if split_vert.is_valid:
            return split_vert
    return None


def split_edge_by_factor(edge, factor=0.5):
    vert = edge.verts[0]
    new_edge, new_vert = bmesh.utils.edge_split(edge, vert, factor)
    return new_edge, new_vert


def bisect_mesh(bm, plane_co=Vector((0,0,0)), plane_no=Vector((0,0,0)), cut_hidden=False, vert_sample_for_island=None, only_sel_geo=False):
    # Verts + Edges + Faces
    geom = []
    # Island Only
    if isinstance(vert_sample_for_island, bmesh.types.BMVert):
        verts = vert_island_containing_vert(vert_sample_for_island)
        edges = list({e for v in verts for e in v.link_edges})
        faces = list({f for e in edges for f in e.link_faces})
        geom = verts + edges + faces
    # All
    else:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    # Selected (Removes Hidden Also)
    if only_sel_geo:
        geom = [elem for elem in geom if elem.select]
    # Remove Hidden
    elif not cut_hidden:
        geom = [elem for elem in geom if not elem.hide]
    # Bisect
    ret = bmesh.ops.bisect_plane(bm,
        geom=geom,
        dist=0.00001,
        plane_co=plane_co,
        plane_no=plane_no,
        use_snap_center=True,
        clear_outer=False,
        clear_inner=False)
    if only_sel_geo:
        for elem in ret['geom_cut']:
            elem.select = True
        bm.select_flush(True)
    return ret

########################•########################
"""               OBJECT OPS                  """
########################•########################

def ops_trace_edges(context, obj, step_limit=150, angle_limit=DEG_30, select_traced=True, from_selected=True, from_index=-1, vert_dir_index=-1, break_at_intersections=True, break_at_boundary=True):
    bm = open_bmesh(context, obj)
    if not bm: return []

    traced_edges = set()
    # Trace Selected
    if from_selected:
        edges = [edge for edge in bm.edges if edge.select]
        for edge in edges:
            if edge in traced_edges:
                continue
            for vert in edge.verts:
                traced_edges.update(trace_edge_by_angle(bm, edge, vert=vert, step_limit=step_limit, angle_limit=angle_limit, break_at_intersections=break_at_intersections, break_at_boundary=break_at_boundary))
    # Trace From Edge Index
    elif from_index >= 0 and from_index < len(bm.edges):
        edge = bm.edges[from_index]
        # Both Directions
        if vert_dir_index < 0:
            for vert in edge.verts:
                traced_edges.update(trace_edge_by_angle(bm, edge, vert=vert, step_limit=step_limit, angle_limit=angle_limit, break_at_intersections=break_at_intersections, break_at_boundary=break_at_boundary))
        # Single Direction
        else:
            vert = edge.verts[0] if vert_dir_index < 1 else edge.verts[1]
            traced_edges.update(trace_edge_by_angle(bm, edge, vert=vert, step_limit=step_limit, angle_limit=angle_limit, break_at_intersections=break_at_intersections, break_at_boundary=break_at_boundary))
    # Select
    if select_traced:
        for edge in traced_edges:
            edge.select = True
        select_flush(bm, select=True)
    # Edge Indices / Close / Ret
    traced_indices = [edge.index for edge in traced_edges]
    close_bmesh(context, obj, bm)
    del bm
    return traced_indices


def ops_slice_mesh(obj, bm, plane_co=Vector((0,0,0)), plane_no=Vector((1,0,0)), clear_outer=False, clear_inner=False, fill_cut_with_faces=False, cut_sel_geo=False, sel_cut_geo=False):
    '''
    OPS : Cuts the mesh along the plane and removes geo on the plane side with option to create faces
    '''
    if not bmesh_instance_valid(bm):
        return
    # Version to delete the selected geo on one side of the plane
    if obj.data.is_editmode and cut_sel_geo and (clear_outer or clear_inner):
        # Geo to bisect
        select_flush(bm, select=True)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        geom = [elem for elem in geom if elem.select and not elem.hide]
        # Bisect
        ret = bmesh.ops.bisect_plane(bm,
            geom=geom,
            dist=0.00001,
            plane_co=plane_co,
            plane_no=plane_no,
            use_snap_center=True,
            clear_outer=False,
            clear_inner=False)
        # Delete Holes
        select_all_elements(bm, select=False)
        verts = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMVert) and distance_point_to_plane(elem.co, plane_co, plane_no) >= -EPSILON]
        edges = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMEdge) if all([vert in verts for vert in elem.verts])]
        faces = [elem for elem in ret['geom'] if isinstance(elem, bmesh.types.BMFace) if all([vert in verts for vert in elem.verts])]
        del_geo = verts[:] + edges[:] + faces[:]
        sel_elems = [elem for elem in ret['geom'] if elem not in del_geo]
        if del_geo:
            bmesh.ops.delete(bm, geom=del_geo, context='FACES')
        # Select
        if sel_cut_geo:
            for elem in sel_elems:
                if elem.is_valid:
                    elem.select = True
        # Doubles
        verts = [elem for elem in ret['geom_cut'] if elem.is_valid and isinstance(elem, bmesh.types.BMVert)]
        bmesh.ops.remove_doubles(bm, verts=verts, dist=EPSILON)
        # Fill Faces
        if fill_cut_with_faces and edges:
            edges = [edge for edge in edges if edge.is_valid]
            edge_chains = edge_chains_from_unsorted_edges(edges)
            for edge_chain in edge_chains:
                ret_net = bmesh.ops.edgenet_prepare(bm, edges=edge_chain)
                bmesh.ops.holes_fill(bm, edges=ret_net['edges'])
    # Version that removes all geo from a side or removes none
    else:
        # Geo to bisect
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        if obj.data.is_editmode:
            if cut_sel_geo:
                geom = [elem for elem in geom if elem.select and not elem.hide]
            else:
                geom = [elem for elem in geom if not elem.hide]
        # Bisect
        ret = bmesh.ops.bisect_plane(bm,
            geom=geom,
            dist=0.00001,
            plane_co=plane_co,
            plane_no=plane_no,
            use_snap_center=True,
            clear_outer=clear_outer,
            clear_inner=clear_inner)
        # Select
        if sel_cut_geo and obj.data.is_editmode:
            for elem in ret['geom_cut']:
                elem.select = True
            bm.select_mode = {'VERT', 'EDGE', 'FACE'}
            bm.select_flush_mode()
        # Fill Faces
        if fill_cut_with_faces and ret['geom_cut']:
            edges = [elem for elem in ret['geom_cut'] if isinstance(elem, bmesh.types.BMEdge)]
            edge_chains = edge_chains_from_unsorted_edges(edges)
            for edge_chain in edge_chains:
                ret_net = bmesh.ops.edgenet_prepare(bm, edges=edge_chain)
                bmesh.ops.holes_fill(bm, edges=ret_net['edges'])
        # Doubles
        verts = [elem for elem in ret['geom_cut'] if elem.is_valid and isinstance(elem, bmesh.types.BMVert)]
        bmesh.ops.remove_doubles(bm, verts=verts, dist=EPSILON)


def ops_mirror_and_weld(obj, bm, axis='X', flip=False, only_sel_geo=False, show_poly_fade=True, color=(0,0,0,1)):
    if not bmesh_instance_valid(bm):
        return
    # Mirror Geo
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    if obj.data.is_editmode:
        if only_sel_geo:
            geom = [elem for elem in geom if elem.select and not elem.hide]
        else:
            geom = [elem for elem in geom if not elem.hide]
    # Mirror
    mat = Matrix.Rotation(math.pi, 4, axis) if flip else Matrix.Identity(4)
    ret = bmesh.ops.mirror(bm, geom=geom, matrix=mat, merge_dist=EPSILON, axis=axis)
    # Poly Fade
    if show_poly_fade:
        if int(len(bm.edges)) < user_prefs().settings.mesh_fade_geo_limit:
            mat_ws = obj.matrix_world
            geom_set = set(geom)
            faces = [face for face in bm.faces if face.is_valid and face not in geom_set]
            lines = [mat_ws @ vert.co for face in faces if face.is_valid for edge in face.edges if edge.is_valid for vert in edge.verts if vert.is_valid]
            init_poly_fade(obj, lines=lines, color_a=COLORS.WHITE, color_b=color)
        else:
            init_poly_fade(obj, bounding_box_only=True, color_a=COLORS.WHITE, color_b=color)
    # Doubles
    if obj.data.is_editmode:
        bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if not v.hide], dist=EPSILON)
    else:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=EPSILON)
    # Normals
    if obj.data.is_editmode:
        bmesh.ops.recalc_face_normals(bm, faces=[f for f in bm.faces if not f.hide])
    else:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def ops_clean_mesh(context, obj, clean_all=True, dissolve_angle=DEG_01, remove_interior=True, clean_hidden=True, epsilon=EPSILON):
    bm = open_bmesh(context, obj)
    if not bm: return

    # Show hidden (Ops : Always Selects on Reveal)
    if clean_hidden:
        bpy.ops.mesh.reveal()
    select_flush(bm, select=True)
    not_all_faces_selected = False
    if not clean_all:
        for face in bm.faces:
            if not face.select:
                not_all_faces_selected = True
                break
    # Dissolve Edges
    edges = []
    if clean_all:
        edges = [e for e in bm.edges if e.calc_face_angle(math.pi) <= dissolve_angle]
    else:
        perimeter_edges = []
        if not_all_faces_selected:
            perimeter_edges = perimeter_edges_from_faces(faces=[f for f in bm.faces if f.select])
        if perimeter_edges:
            edges = [e for e in bm.edges if e.select and e not in perimeter_edges and e.calc_face_angle(math.pi) <= dissolve_angle]
        else:
            edges = [e for e in bm.edges if e.select and e.calc_face_angle(math.pi) <= dissolve_angle]
    bmesh.ops.dissolve_edges(bm, edges=edges, use_verts=False, use_face_split=False)
    # Doubles
    verts = bm.verts if clean_all else [v for v in bm.verts if v.select]
    bmesh.ops.remove_doubles(bm, verts=verts, dist=epsilon)
    # Dissolve Degenerate
    edges = bm.edges if clean_all else [e for e in bm.edges if e.select]
    bmesh.ops.dissolve_degenerate(bm, dist=epsilon, edges=edges)
    # Dissolve Limit
    if clean_all:
        verts = bm.verts
        edges = bm.edges
        bmesh.ops.dissolve_limit(bm, angle_limit=dissolve_angle, use_dissolve_boundaries=False, verts=verts, edges=edges)
    else:
        if not_all_faces_selected:
            select_flush(bm, select=True)
            perimeter_edges = set(perimeter_edges_from_faces(faces=[f for f in bm.faces if f.select]))
            perimeter_verts = set([v for e in perimeter_edges for v in e.verts])
            verts = [v for v in bm.verts if v.select]
            edges = [e for e in bm.edges if e.select and e not in perimeter_edges]
            bmesh.ops.dissolve_limit(bm, angle_limit=dissolve_angle, use_dissolve_boundaries=False, verts=verts, edges=edges)
        else:
            verts = [v for v in bm.verts if v.select]
            edges = [e for e in bm.edges if e.select]
            bmesh.ops.dissolve_limit(bm, angle_limit=dissolve_angle, use_dissolve_boundaries=False, verts=verts, edges=edges)
    # Normals
    faces = bm.faces if clean_all else [f for f in bm.faces if f.select]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    # Interior Faces
    if remove_interior and clean_all:
        select_all_elements(bm, select=False)
        bpy.ops.mesh.select_interior_faces()
        faces = [f for f in bm.faces if f.select]
        bmesh.ops.delete(bm, geom=faces, context='FACES')
    close_bmesh(context, obj, bm)
    del bm


def ops_flatten_geometry(context, obj, project_boundary_verts=True, clean_surface=False):
    bm = open_bmesh(context, obj)
    if not bm: return

    # Selections
    active_elem = bm.select_history.active
    sel_verts = [v for v in bm.verts if v.select]
    sel_edges = [e for e in bm.edges if e.select]
    sel_faces = [f for f in bm.faces if f.select and f != active_elem]
    # Project verts by face normal and boundary edges
    if active_elem and isinstance(active_elem, bmesh.types.BMFace) and sel_faces:
        active_elem.normal_update()
        plane_co = active_elem.calc_center_median()
        plane_no = active_elem.normal
        # Tag
        for vert in sel_verts:
            vert.tag = False
        if project_boundary_verts:
            outter_edges = perimeter_edges_from_faces(sel_faces)
            outter_verts = {vert for edge in outter_edges for vert in edge.verts}
            for vert in outter_verts:
                project_edges = [edge for edge in vert.link_edges if edge not in sel_edges]
                if not project_edges:
                    continue
                project_edge = project_edges[0]
                direction = (vert.co - project_edge.other_vert(vert).co).normalized()
                line_a = vert.co
                line_b = vert.co + direction
                intersection = intersect_line_plane(line_a, line_b, plane_co, plane_no)
                if not intersection:
                    continue
                vert.co = intersection
                vert.tag = True
        for vert in sel_verts:
            if vert.tag:
                continue
            if vert in active_elem.verts:
                continue
            offset = distance_point_to_plane(vert.co, plane_co, plane_no)
            vert.co -= plane_no * offset
    # Project verts to triangulated plane
    elif sel_verts:
        for face in query_for_faces_containing_verts(bm, target_verts=sel_verts):
            sel_face_verts = [vert for vert in face.verts if vert.select]
            plane_co = math3.center_of_coords([vert.co for vert in sel_face_verts])
            plane_no = math3.normal_from_points(v1=sel_face_verts[0].co, v2=sel_face_verts[1].co, v3=sel_face_verts[2].co)
            for vert in face.verts:
                slide_edge = [edge for edge in vert.link_edges if edge not in face.edges]
                if slide_edge:
                    slide_edge = slide_edge[0]
                    direction = vert.co - slide_edge.other_vert(vert).co
                    p1 = vert.co
                    p2 = p1 + direction
                    intersection_point = intersect_line_plane(p1, p2, plane_co, plane_no, False)
                    if intersection_point:
                        vert.co = intersection_point
                else:
                    offset = distance_point_to_plane(vert.co, plane_co, plane_no)
                    vert.co -= plane_no * offset
    # Clean
    if clean_surface:
        bmesh.ops.remove_doubles(bm, verts=sel_verts, dist=EPSILON)
        bmesh.ops.dissolve_degenerate(bm, dist=EPSILON, edges=[e for e in bm.edges if e.select])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.dissolve_limit(bm, angle_limit=radians(1), use_dissolve_boundaries=False, verts=[v for v in bm.verts if v.select], edges=[e for e in bm.edges if e.select])
    shade_recalc_normals(bm)
    close_bmesh(context, obj, bm)
    del bm


def ops_selections_to_curves(context, obj, simplify=True):
    bm = open_bmesh(context, obj)
    if not bm: return
    if any([e.select for e in bm.edges]) == False:
        return None
    # Create Curve
    curve_obj = create_curve(context, location=Vector((0,0,0)), obj_name="Curve", curve_type='CURVE')
    # Matrix
    mat_ws = obj.matrix_world
    loc, rot, sca = mat_ws.decompose()
    sca_mat = math3.sca_matrix(sca)
    curve_obj.matrix_world = math3.loc_matrix(loc) @ math3.rot_matrix(rot)
    # Parent
    parent_object(child=curve_obj, parent=obj)
    # Curve Data
    curve_data = curve_obj.data
    curve_data.dimensions = '3D'

    # Duplicate selection and clean it
    original_geometry = []
    if simplify:
        ret = bmesh.ops.duplicate(bm, geom=[v for v in bm.verts if v.select] + [e for e in bm.edges if e.select] + [f for f in bm.faces if f.select])
        select_all_elements(bm, select=False)
        clear_all_tags(bm)
        original_geometry = ret['geom_orig']
        for elem in ret['geom']:
            elem.select = True
            elem.tag = True
        clean_tagged_geo(bm)

    def set_spline_data(spline, add_new=True, coord=Vector((0,0,0))):
        spline_point = None
        if add_new:
            spline.bezier_points.add(1)
            spline_point = spline.bezier_points[-1]
        else:
            spline_point = spline.bezier_points[0]
        spline_point.co = coord
        spline_point.handle_left_type = 'VECTOR'
        spline_point.handle_right_type = 'VECTOR'

    # Boundary Edges
    sel_faces = [f for f in bm.faces if f.select]
    face_islands = face_islands_from_faces(faces=sel_faces)
    for face_island in face_islands:
        for face in face_island:
            face.select = False
        spline = curve_data.splines.new(type='BEZIER')

        # Travel Sorted edges
        perimeter_edges = perimeter_edges_from_faces(faces=face_island)
        edge_chain = edge_chain_from_connected_edges(edges=perimeter_edges)
        vert_chain = vert_chain_from_edge_chain(edge_chain=edge_chain)
        if not vert_chain: continue

        # Continious edge chain
        applied_coords = []
        if vert_chain[0] == vert_chain[-1]:
            coord = sca_mat @ vert_chain[-1].co
            applied_coords.append(coord)
            spline.use_cyclic_u = True
            set_spline_data(spline, add_new=False, coord=coord)

        # Create Spline Points
        for index, vert in enumerate(vert_chain):
            coord = sca_mat @ vert.co
            if coord in applied_coords: continue
            applied_coords.append(coord)
            set_spline_data(spline, add_new=True, coord=coord)

    # Edge Chains
    sel_edges = [e for e in bm.edges if e.select]
    edge_chains = edge_chains_from_unsorted_edges(edges=sel_edges)
    for edge_chain in edge_chains:

        vert_chain = vert_chain_from_edge_chain(edge_chain=edge_chain)
        if not vert_chain: continue

        spline = curve_data.splines.new(type='BEZIER')
        if vert_chain[0] == vert_chain[-1]:
            spline.use_cyclic_u = True
        
        applied_coords = []
        coord = sca_mat @ vert_chain[0].co
        applied_coords.append(coord)
        set_spline_data(spline, add_new=False, coord=coord)
        
        # Create Spline Points
        for index, vert in enumerate(vert_chain):
            coord = sca_mat @ vert.co
            if coord in applied_coords: continue
            set_spline_data(spline, add_new=True, coord=coord)

    # Remove Simplified Geo and restore selection
    if simplify:
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.tag], context='VERTS')
        for elem in original_geometry:
            elem.select = True

    close_bmesh(context, obj, bm)
    del bm
    return curve_obj

########################•########################
"""                    R&D                    """
########################•########################

def create_convex_hull(bm):
    ret = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    hull_geo = set(ret['geom'])
    faces = [face for face in bm.faces if face.is_valid and face not in hull_geo]
    bmesh.ops.delete(bm, geom=faces, context='FACES')
    edges = [edge for edge in bm.edges if edge.is_valid and edge not in hull_geo]
    bmesh.ops.delete(bm, geom=edges, context='EDGES')
    verts = [vert for vert in bm.verts if vert.is_valid and vert not in hull_geo]
    bmesh.ops.delete(bm, geom=verts, context='VERTS')
    bm.normal_update()

