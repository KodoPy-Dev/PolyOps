########################•########################
"""                   NOTES                   """
########################•########################

''' 
[VS-Code]
    - Change Comments Color
        "editor.tokenColorCustomizations": {
            "comments": "#d4922f"
        },

[B3D Windows]
    Window Manager............ Root Application
        Windows............... Duplicated Blender Windows
            Screen............ Active Workspace
                Areas......... Workspace Editors
                    Spaces.... Editors in this area (first one is the active one)
                    Regions... Data on how the area is divided
[Space]
    if Space type == 'VIEW_3D'
        space.type             = SpaceView3D
        space.region_3d        = RegionView3D
        space.region_quadviews = [RegionView3D, RegionView3D, RegionView3D, RegionView3D]

[Object Update]
    obj.data.update_from_edit_mode()
        - when you have made changes in Edit Mode to the mesh and need those changes to be reflected in the mesh data.
        - Removes edge data (marks)
    Use obj.update()
        - when you have changed properties at the object level and need to ensure those changes are reflected in Blender's internal state.

[DATA]
    Terabit = 1,000 Gigabits
    Gigabyte = 8,000 Megabits
    Gigabyte = 8,000,000 Kilobits
    Gigabyte = 8,000,000,000 Bits
    Megabyte = 8,000,000 Bits
    Kilobit = 1,000 Bits
'''

########################•########################
"""              BMESH EDIT MODE              """
########################•########################

import bpy
import bmesh
from mathutils import *
from math import *
obj = bpy.context.edit_object
mesh = obj.data
bm = bmesh.from_edit_mesh(mesh)

bmesh.update_edit_mesh(mesh, loop_triangles=True)

########################•########################
"""             BMESH OBJECT MODE             """
########################•########################

import bpy
import bmesh
from mathutils import *
from math import *
obj = bpy.context.active_object
mesh = obj.data
bm = bmesh.new(use_operators=True)
bm.from_mesh(mesh, face_normals=True, vertex_normals=True)


bm.to_mesh(mesh)

########################•########################
"""             MESH FROM PY DATA             """
########################•########################

import bpy

obj_name = "PyDataObj"
mesh = bpy.data.meshes.new(name=obj_name)
obj = bpy.data.objects.new(name=obj_name, object_data=mesh)

vertices = []
edges = []
faces = []

mesh.from_pydata(vertices, edges, faces, shade_flat=True)
context.collection.objects.link(obj)

########################•########################
"""                  IMPORTS                  """
########################•########################

import bmesh
from mathutils import *
from math import *

########################•########################
"""                  VECTORS                  """
########################•########################

vec_zero = Vector((0,0,0))
x_norm = Vector((1,0,0))
y_norm = Vector((0,1,0))
z_norm = Vector((0,0,1))

########################•########################
"""                   TYPES                   """
########################•########################

var = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
var = {1: [2], 2: [1,3], 3: [2], 4: [], 5:[6], 6:[5], 7:[8], 8:[7,9], 9:[8]}
var = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX']
var = {1: {'ONE':1}, 2: {'ONE':1}, 3: {'ONE':1, 'TWO':2, 'THREE':3}, 4: {}}
var = {1: {'A':6, 'B': 3}, 2: {'A':-56, 'B': 64}, 3: {'A':8, 'B': 24}, 4: {'A':23, 'B': 3}}
var = {1: {'NUM':0}, 2: {'NUM':0}, 3: {'NUM':0}, 4: {'NUM':0}}
var = {'VERTS':[1,2,3], 'EDGES':[4,5], 'FACES':[6,7,8,9]}

########################•########################
"""                  WINDOWS                  """
########################•########################

region_3d = None
for screen in C.workspace.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    region_3d = region
                    break

rv3d = None
for screen in C.workspace.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    rv3d = region
                    break

space_view_3d = None
for screen in C.workspace.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space_view_3d = space
                    break

########################•########################
"""                    ZIP                    """
########################•########################

var_a = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX']
var_b = ['1', '2', '3', '4', '5', '6']
for a, b in zip(var_a, var_b):
    print(f'{a} : {b}')

########################•########################
"""             BMESH FRAME CHANGE            """
########################•########################

import bpy
import bmesh
from mathutils import *
from math import *

def handle(scene):
    obj = bpy.context.edit_object
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    bmesh.update_edit_mesh(mesh, loop_triangles=True)

if handle in bpy.app.handlers.frame_change_pre:
    bpy.app.handlers.frame_change_pre.remove(handle)
bpy.app.handlers.frame_change_pre.append(handle)

########################•########################
"""                 QUAD VIEW                 """
########################•########################

rv3d = None
for window in context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    if region.alignment == 'QUAD_SPLIT':
                        rv3d = region

########################•########################
"""              LOOP WITH ITERATOR           """
########################•########################

my_list = [1, 2, 3, 4, 5]
iterator = iter(my_list)
while True:
    try:
        item = next(iterator)
    except StopIteration:
        break

