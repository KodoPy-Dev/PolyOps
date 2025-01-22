########################•########################
"""                   KodoPy                  """
########################•########################

import bpy


def last_created_by_name_ext(name='', objects=[]):
    best_match = None
    delta_ext = 0
    delta_dots = 0
    for obj in objects:
        if not isinstance(obj, bpy.types.Object):
            continue
        if name not in obj.name:
            continue
        splits = [ext for ext in obj.name.replace(name, '').strip().split('.') if ext and ext.isdigit()]
        summed = sum([int(partition) for partition in splits if partition.isdigit()])
        if len(splits) > delta_dots:
            best_match = obj
            delta_ext = summed
            delta_dots = len(splits)
        elif len(splits) == 0 and delta_dots == 0:
            ext = ''
            for char in obj.name.replace(name, '').strip():
                if char.isdigit():
                    ext += char
                elif ext != '':
                    break
            if ext.isdigit():
                ext = int(ext)
                if ext > delta_ext:
                    best_match = obj
                    delta_ext = ext
        elif len(splits) == delta_dots:
            if summed > delta_ext:
                best_match = obj
                delta_ext = summed
                delta_dots = len(splits)
    return best_match

