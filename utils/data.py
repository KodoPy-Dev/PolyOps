########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from mathutils import Vector, Matrix, Euler, Quaternion


def capture_prop_maps(object:object):
    ''' Copy Types : bool, int, float, str, Vector, Matrix, Euler, Quaternion '''

    def recursive(object:object):
        prop_map = dict()
        for prop in dir(object):
            attr = getattr(object, prop)
            # Skip
            if prop.startswith('__'):
                continue
            if prop.endswith('__'):
                continue
            if prop in {'bl_rna', 'rna_type'}:
                continue
            if callable(attr):
                continue
            if type(attr) in {tuple, list, dict}:
                continue
            # Collect
            if type(attr) in {bool, int, float, str}:
                prop_map[prop] = attr
            # Collect
            elif type(attr) in {Vector, Matrix, Euler, Quaternion}:
                prop_map[prop] = attr.copy()
            # Recursive
            elif type(attr) == bpy.types.bpy_prop_collection:
                collection_maps = []
                for iterative_attr in attr:
                    collection_maps.append(recursive(iterative_attr))
                prop_map[prop] = collection_maps
            # Recursive
            else:
                prop_map[prop] = recursive(attr)
        return prop_map
    return recursive(object)


def transfer_props(prop_map:dict, object:object):
    def recursive(prop_map, object):
        for prop, value in prop_map.items():
            # Skip
            if type(prop) != str:
                continue
            if hasattr(object, prop):
                attr = getattr(object, prop)
                # Set
                if type(attr) in {bool, int, float, str, Vector, Matrix, Euler, Quaternion}:
                    try:
                        setattr(object, prop, value)
                    except:
                        pass
                # Recursive
                elif type(attr) == bpy.types.bpy_prop_collection:
                    for index, iterative_attr in enumerate(attr):
                        if index >= len(value):
                            break
                        iterative_map = value[index]
                        recursive(iterative_map, iterative_attr)
                # Recursive
                elif type(value) == dict:
                    recursive(value, attr)
    recursive(prop_map, object)

