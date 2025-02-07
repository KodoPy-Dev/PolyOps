########################•########################
"""                   KodoPy                  """
########################•########################

import json
import os
from mathutils import geometry, Vector, Matrix, Euler, Quaternion


def directory_location():
    return os.path.dirname(os.path.abspath(__file__))


def get_shape_data(file_name=""):
    json_file_path = os.path.join(directory_location(), file_name)
    data = None
    with open(json_file_path, "r") as f:
        data = json.load(f)
    if not data: return None
    vertices_data = data["vertices"]
    vertices = [Vector(vertex) for vertex in vertices_data]
    return vertices, data["indices"]

