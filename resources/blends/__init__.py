########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import os
from pathlib import Path

AUTO_SMOOTH_NAME = 'Smooth by Angle'


def blend_file_path(file_name=""):
    blends_dir = Path(__file__).parent.resolve()
    blend_file = blends_dir.joinpath(file_name)
    if blend_file.exists():
        return str(blend_file)
    return None


def autosmooth_nodes(search_current_blend_first=True):
    if search_current_blend_first:
        for node_group in bpy.data.node_groups:
            if node_group.name == AUTO_SMOOTH_NAME:
                return node_group

    filepath = blend_file_path(file_name="smooth_by_angle.blend")
    if filepath is None: return None

    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        for node_group_name in data_from.node_groups:
            if node_group_name == AUTO_SMOOTH_NAME:
                data_to.node_groups.append(AUTO_SMOOTH_NAME)
                break

    for node_group in data_to.node_groups:
        if node_group.name == AUTO_SMOOTH_NAME:
            node_group.asset_clear()
            for library in bpy.data.libraries[:]:
                if library.filepath == filepath:
                    bpy.data.libraries.remove(library)
                    break
            return node_group
    return None

