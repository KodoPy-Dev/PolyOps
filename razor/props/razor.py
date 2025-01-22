########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from bpy.props import *
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from . import PROPS_BASE, PROPS_INDEXER
from .workplane import PS_PROPS_Razor_Workplane
from .features import PS_PROPS_Razor_Part_Features
from .settings import PS_PROPS_Razor_Settings
from .sketch import PS_PROPS_Razor_Sketch
from .ops import PS_PROPS_Razor_Ops


class PS_PROPS_Razor(PROPS_BASE, PROPS_INDEXER):

    # --- UTILS --- #

    @staticmethod
    def is_tool_active():
        tool = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode)
        return tool.idname == "ps.razor_tool"

    # --- RAZOR --- #

    settings : PointerProperty(type=PS_PROPS_Razor_Settings)

    # --- OPS ---- #

    ops : PointerProperty(type=PS_PROPS_Razor_Ops)

    # --- WORKPLANE ---- #

    workplanes : CollectionProperty(type=PS_PROPS_Razor_Workplane)
    active_workplane : StringProperty(name="Active Workplane UUID", default="")

    def new_workplane(self, name="", set_active=True):
        if len(self.workplanes) < self.settings.max_workplanes:
            index = self.next_index
            workplane = self.workplanes.add()
            workplane.name = name if name else f"Workplane {index}"
            workplane.index = index
            workplane.hide = False
            workplane.transform.scale = Vector((2,2,2))
            if set_active:
                self.active_workplane = workplane.uuid
            return workplane
        return None


    def del_workplane(self, uuid=""):
        for i, workplane in enumerate(self.workplanes):
            if workplane.uuid == uuid:
                self.workplanes.remove(i)
                return True
        return False


    def del_all_workplanes(self):
        self.workplanes.clear()


    def del_hidden_workplanes(self):
        que = {workplane.uuid for workplane in self.workplanes if workplane.hide}
        while que:
            uuid = que.pop()
            for i, workplane in enumerate(self.workplanes):
                if workplane.uuid == uuid:
                    self.workplanes.remove(i)
                    break


    def get_active_workplane(self):
        for workplane in self.workplanes:
            if workplane.uuid == self.active_workplane:
                return workplane
        return None


    def get_workplane(self, uuid=""):
        for workplane in self.workplanes:
            if workplane.uuid == uuid:
                return workplane
        return None


    def set_hide_workplane(self, uuid="", hide=False, set_active=True):
        for workplane in self.workplanes:
            if workplane.uuid == uuid:
                workplane.hide = hide
                if self.active_workplane == workplane.uuid:
                    self.active_workplane = ""
                return True
        return False


    def set_active_workplane(self, uuid=""):
        for workplane in self.workplanes:
            if workplane.uuid == uuid:
                self.active_workplane = uuid
                workplane.hide = False
                return True
        return False

    # --- SKETCH ---- #

    sketches : CollectionProperty(type=PS_PROPS_Razor_Sketch)
    active_sketch : StringProperty(name="Active Sketch UUID", default="")

    def new_sketch(self, name="", mat_ws=Matrix.Identity(4), set_active=True):
        index = self.next_index
        sketch = self.sketches.add()
        sketch.name = name if name else f"Sketch {index}"
        sketch.index = index
        sketch.transform.set_matrix(mat_ws)
        if set_active:
            self.active_sketch = sketch.uuid
        return sketch


    def del_sketch(self, uuid=""):
        for i, sketch in enumerate(self.sketches):
            if sketch.uuid == uuid:
                if sketch.uuid == self.active_sketch:
                    self.active_sketch = ""
                sketch.del_all_entities()
                sketch.del_all_edits()
                self.sketches.remove(i)
                return True
        return False


    def get_sketch(self, uuid=""):
        for sketch in reversed(self.sketches):
            if sketch.uuid == uuid:
                return sketch
        return None


    def get_active_sketch(self):
        for sketch in self.sketches:
            if sketch.uuid == self.active_sketch:
                return sketch
        return None


    def set_active_sketch(self, sketch=None):
        if not isinstance(sketch, PS_PROPS_Razor_Sketch): return False
        for other in self.sketches:
            if other.uuid == sketch.uuid:
                self.active_sketch = sketch.uuid
                sketch.hide = False
                return True
        return False

    # --- FEATURES ---- #

    features : PointerProperty(type=PS_PROPS_Razor_Part_Features)

