########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import gpu
from bpy.props import *
from bpy.types import PropertyGroup
from gpu_extras.batch import batch_for_shader
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from . import PROPS_BASE, PROPS_INDEXER, PROPS_UUID, PS_PROPS_Razor_Transform
from .entity import PS_PROPS_Razor_Entity
from ..props.features import PS_PROPS_Razor_Edit_Features
from ...utils.math3 import matrix_loc_rot


class PS_PROPS_Razor_Sketch(PROPS_BASE, PROPS_INDEXER, PROPS_UUID):
    transform : PointerProperty(type=PS_PROPS_Razor_Transform)
    entities  : CollectionProperty(type=PS_PROPS_Razor_Entity)
    edits     : CollectionProperty(type=PS_PROPS_Razor_Edit_Features)
    deleted   : BoolProperty(name="Deleted", default=False)

    def new_entity(self, shape='POINT'):
        ''' Make sure the sketch transform is already set first '''

        entity = self.entities.add()
        entity.sketch_uuid = self.uuid
        entity.index = self.next_index

        matrix = self.transform.get_matrix()
        matrix = matrix_loc_rot(matrix)
        entity.transform.set_matrix(matrix)

        entity.shape = shape
        entity.geo_is_set = False

        return entity


    def new_edit(self, edit_opt='NONE', entity_a=None, entity_b=None):
        edit = self.edits.add()
        edit.index = self.next_index
        edit.operation = edit_opt


    def del_entity(self, uuid=""):
        for i, entity in enumerate(self.entities):
            if entity.uuid == uuid:
                self.entities.remove(i)
                return True
        return False


    def del_all_entities(self):
        self.entities.clear()


    def del_all_edits(self):
        self.edits.clear()


    def get_entities_sorted(self):
        if len(self.entities) == 0:
            return []
        return sorted(self.entities, key=lambda entity: entity.index)


    def get_entity(self, uuid=""):
        for entity in reversed(self.entities):
            if entity.uuid == uuid:
                return entity
        return None


    def new_sketch_tesselator(self):
        sketch_tess = SketchTess(sketch=self)
        return sketch_tess

########################•########################
"""                 TESSELATOR                """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')

class SketchTess:
    def __init__(self, sketch):
        self.uuid = sketch.uuid
        self.sketch = sketch
        self.mat_ws = self.sketch.transform.get_matrix()
        self.mat_ws_inv = self.mat_ws.inverted_safe()

        self.geo_valid = False
        self.batches_valid = False
        self.reset()


    def reset(self):
        pass


    def build(self):
        pass


    def draw_3D(self):
        if not self.geo_valid: return
        if not self.batches_valid: return
        state = gpu.state
        state.blend_set('ALPHA')

        state.line_width_set(1)
        state.point_size_set(1)
        state.blend_set('NONE')


