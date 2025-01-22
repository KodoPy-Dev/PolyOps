########################•########################
"""                   KodoPy                  """
########################•########################

import bpy


class PS_MT_ShadingMenu(bpy.types.Menu):
    bl_idname = "PS_MT_ShadingMenu"
    bl_label = "Marks & Shading"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.obj_shade", text="Object Shading", icon="MESH_CUBE")
        layout.operator("ps.edge_mark", text="Edge Mark", icon="EDGESEL")
        layout.operator("ps.vert_mark", text="Vert Mark", icon="VERTEXSEL")
        layout.operator("ps.object_display", text="Display Mode", icon="MOD_WIREFRAME")
        layout.operator("ps.poly_debug", text="Poly Debug", icon="IMAGE_ALPHA")

