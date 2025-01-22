########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import bmesh
import json
import os
from mathutils import Vector, Matrix
from bpy.props import EnumProperty
from ...resources.icon.geomtry_icon_writer import write_icon_data_from_mesh_object
from ... import utils


class PS_OT_WriteData(bpy.types.Operator):
    bl_idname      = "ps.write_data"
    bl_label       = "Write Data"
    bl_description = "Write Data"
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        dev = utils.addon.user_prefs().dev
        data_write_type = dev.data_write_type
        msg = ""

        if data_write_type == 'VERTS_INDICES_JS':
            obj = utils.context.get_mesh_from_edit_or_mesh_from_active(context)
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                msg = write_verts_indices_json(context, obj)

        elif data_write_type == 'VERTS_INDICES_PY':
            obj = utils.context.get_mesh_from_edit_or_mesh_from_active(context)
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                msg = write_verts_indices_python(context, obj)

        elif data_write_type == 'LINES_PY':
            obj = utils.context.get_mesh_from_edit_or_mesh_from_active(context)
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                msg = write_line_coords_python(context, obj)

        elif data_write_type == 'ICON_DAT':
            msg = write_icon_data_from_mesh_object()

        msgs = [("FINISH", str(msg))] if msg else [("ERROR", "NONE")]
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}


def write_verts_indices_json(context, obj):
    # Mesh
    coords, indices = tri_coords_indices_from_obj(obj)
    data = {"coords": [[v.x, v.y, v.z] for v in coords], "indices": indices }
    # Write
    file_path = resources_path(obj, file_ext='json')
    with open(file_path, "w") as write_file:
        json.dump(data, write_file, indent=1)
    return file_path


def write_verts_indices_python(context, obj):

    # Mesh
    coords, indices = tri_coords_indices_from_obj(obj)

    # Write
    file_path = resources_path(obj, file_ext='py')
    with open(file_path, 'w') as file:
 
        # IMPORTS
        file.write("from mathutils import Vector, Matrix\n")
        file.write("from gpu_extras.batch import batch_for_shader\n")
        file.write("import gpu\n")
        file.write("\n")
        file.write("UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')\n")
        file.write("SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')\n")
        file.write("\n")

        # COORDS
        file.write("coords = [\n")
        for coord in coords:
            file.write(f"\tVector(({coord.x}, {coord.y}, {coord.z})),\n")
        file.write("]\n\n")

        # INDICES
        file.write("indices = [\n")
        for tri_indices in indices:
            file.write(f"\t({tri_indices[0]}, {tri_indices[1]}, {tri_indices[2]}),\n")
        file.write("]\n\n")

        # COLORS
        file.write("colors = [\n")
        if obj.data.color_attributes:
            col_attr = obj.data.color_attributes[0]
            for vert in obj.data.vertices:
                color = col_attr.data[vert.index].color_srgb
                file.write(f"\t({color[0]}, {color[1]}, {color[2]}, {color[3]}),\n")
        file.write("]\n\n")

        # FUNCTIONS
        file.write(gen_poly_batch_flat)
        file.write("\n")
        file.write(draw_poly_batch_flat)
        file.write("\n") 
        file.write(gen_poly_batch_smooth)
        file.write("\n")
        file.write(draw_poly_batch_smooth)
        file.write("\n")
    return file_path


def write_line_coords_python(context, obj):

    # Mesh
    mesh = obj.data
    verts = mesh.vertices
    edges = mesh.edges
    coords = [verts[vert].co for edge in edges for vert in edge.vertices]

    # Write
    file_path = resources_path(obj, file_ext='py')
    with open(file_path, 'w') as file:
 
        # IMPORTS
        file.write("from mathutils import Vector\n")
        file.write("\n")

        # COORDS
        file.write("coords = [\n")
        for coord in coords:
            file.write(f"\tVector(({coord.x}, {coord.y}, {coord.z})),\n")
        file.write("]\n\n")
    return file_path


def resources_path(obj, file_ext='json'):
    from ...resources import shapes
    resources_directory = shapes.directory_location()
    file_path = os.path.join(resources_directory, f"{obj.name}.{file_ext}")
    return file_path


def tri_coords_indices_from_obj(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.index_update()
    bm.faces.index_update()
    triangles = bm.calc_loop_triangles()
    coords = [vert.co for vert in bm.verts]
    indices = [(tri[0].vert.index, tri[1].vert.index, tri[2].vert.index) for tri in triangles]
    return coords, indices


gen_poly_batch_flat = '''def gen_poly_batch_flat(center=Vector((0,0,0)), scale=Vector((1,1,1)), direction=Vector((0,0,1))):
\tglobal coords, indices
\tmat_loc = Matrix.Translation(center.to_4d())
\tmat_sca = Matrix.Diagonal(scale.to_4d())
\tmat_rot = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
\tmat_out = mat_loc @ mat_rot @ mat_sca
\treturn batch_for_shader(gpu.shader.from_builtin('UNIFORM_COLOR'), 'TRIS', {"pos": [mat_out @ coord for coord in coords]}, indices=indices)
'''

draw_poly_batch_flat = '''def draw_poly_batch_flat(batch=None, color_front=(0,0,0,1), color_back=(0,0,0,1)):
\tif not isinstance(batch, gpu.types.GPUBatch): return
\tgpu.state.face_culling_set('FRONT')
\tgpu.state.depth_test_set('GREATER')
\tgpu.state.depth_mask_set(True)
\tgpu.state.blend_set('ALPHA')
\tUNIFORM_COLOR.uniform_float("color", color_back)
\tbatch.draw(UNIFORM_COLOR)
\tgpu.state.face_culling_set('BACK')
\tgpu.state.depth_test_set('LESS_EQUAL')
\tUNIFORM_COLOR.uniform_float("color", color_front)
\tbatch.draw(UNIFORM_COLOR)
\tgpu.state.face_culling_set('NONE')
\tgpu.state.depth_test_set('NONE')
\tgpu.state.depth_mask_set(False)
\tgpu.state.blend_set('NONE')
'''

gen_poly_batch_smooth = '''def gen_poly_batch_smooth(center=Vector((0,0,0)), scale=Vector((1,1,1)), direction=Vector((0,0,1))):
\tglobal coords, indices, colors
\tmat_loc = Matrix.Translation(center.to_4d())
\tmat_sca = Matrix.Diagonal(scale.to_4d())
\tmat_rot = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
\tmat_out = mat_loc @ mat_rot @ mat_sca
\tbatch = batch_for_shader(SMOOTH_COLOR, 'TRIS', {'pos': [mat_out @ coord for coord in coords], 'color':colors}, indices=indices)
\tif isinstance(batch, gpu.types.GPUBatch): return batch
\treturn None
'''

draw_poly_batch_smooth = '''def draw_poly_batch_smooth(batch=None):
\tif not isinstance(batch, gpu.types.GPUBatch): return
\tgpu.state.blend_set('ALPHA')
\tgpu.state.depth_mask_set(True)
\tgpu.state.face_culling_set('BACK')
\tbatch.draw(SMOOTH_COLOR)
\tgpu.state.face_culling_set('NONE')
\tgpu.state.depth_mask_set(False)
\tgpu.state.blend_set('NONE')
'''
