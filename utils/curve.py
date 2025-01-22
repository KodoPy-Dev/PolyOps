########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from mathutils import Vector, Matrix, Euler, Quaternion
from .collections import link_object_to_collection
from .context import object_mode_toggle_start, object_mode_toggle_end


def create(context, location=Vector((0,0,0)), obj_name="Curve", curve_type='CURVE', collection=None):
    if curve_type in {'CURVE', 'SURFACE', 'FONT'}:
        curve = bpy.data.curves.new(name=obj_name, type=curve_type)
        obj = bpy.data.objects.new(name=obj_name, object_data=curve)
        # Link to active collection
        if collection is None:
            context.collection.objects.link(obj)
        else:
            link_object_to_collection(collection, obj)
        obj.location = location
        return obj
    return None


def delete_curve(curve):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        data = curve.data
        if curve.name in bpy.data.objects:
            bpy.data.objects.remove(curve, do_unlink=True, do_id_user=True, do_ui_user=True)
        if data.name in bpy.data.curves:
            bpy.data.curves.remove(data, do_unlink=True, do_id_user=True, do_ui_user=True)


def delete_curve_data(curve_data):
    if isinstance(curve_data, bpy.types.Curve):
        if curve_data.name in bpy.data.curves:
            bpy.data.curves.remove(curve_data, do_unlink=True, do_id_user=True, do_ui_user=True)


def create_copy(curve):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        return curve.data.copy()
    return None


def swap_curve_data_and_remove_current(context, curve, target_curve_data):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve) and isinstance(target_curve_data, bpy.types.Curve):
        if curve.data.name in bpy.data.curves and target_curve_data.name in bpy.data.curves:
            if curve.data != target_curve_data:
                toggle_mode = False
                if curve.mode == 'EDIT':
                    toggle_mode = True
                    object_mode_toggle_start(context)
                original_data_name = curve.data.name
                curve.data = target_curve_data
                if original_data_name in bpy.data.curves:
                    original_data = bpy.data.curves[original_data_name]
                    bpy.data.curves.remove(original_data, do_unlink=True, do_id_user=True, do_ui_user=True)
                    del original_data
                curve.data.name = original_data_name
                if toggle_mode:
                    object_mode_toggle_end(context)


def capture_prop_map(curve):
    prop_map = {}
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        for prop in dir(curve.data):
            # Skip
            if prop.startswith('__'):
                continue
            if prop.endswith('__'):
                continue
            if prop in {'bl_rna', 'rna_type'}:
                continue
            attr = getattr(curve.data, prop)
            if callable(attr):
                continue
            if type(attr) in {tuple, list, dict}:
                continue
            # Collect
            if type(attr) in {bool, int, float, str}:
                prop_map[prop] = attr
            elif type(attr) in {Vector, Matrix, Euler, Quaternion}:
                prop_map[prop] = attr.copy()
        prop_map['splines'] = []
        for spline in curve.data.splines:
            spline_map = dict()
            for prop in dir(spline):
                # Skip
                if prop.startswith('__'):
                    continue
                if prop.endswith('__'):
                    continue
                if prop in {'bl_rna', 'rna_type'}:
                    continue
                attr = getattr(spline, prop)
                if callable(attr):
                    continue
                if type(attr) in {tuple, list, dict}:
                    continue
                # Collect
                if type(attr) in {bool, int, float, str}:
                    spline_map[prop] = attr
                elif type(attr) in {Vector, Matrix, Euler, Quaternion}:
                    spline_map[prop] = attr.copy()
            prop_map['splines'].append(spline_map)
    return prop_map


def transfer_props(prop_map, curve):
    if isinstance(prop_map, dict) and isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        for prop, value in prop_map.items():
            # Skip
            if type(prop) != str:
                continue
            if prop == 'splines':
                for spline_map, spline in zip(value, curve.data.splines):
                    if isinstance(spline_map, dict):
                        for spline_prop, spline_value in spline_map.items():
                            if hasattr(spline, spline_prop):
                                attr = getattr(spline, spline_prop)
                                # Set
                                if type(attr) in {bool, int, float, str, Vector, Matrix, Euler, Quaternion}:
                                    try:
                                        setattr(spline, spline_prop, spline_value)
                                    except:
                                        pass
            else:
                if hasattr(curve.data, prop):
                    attr = getattr(curve.data, prop)
                    # Set
                    if type(attr) in {bool, int, float, str, Vector, Matrix, Euler, Quaternion}:
                        try:
                            setattr(curve.data, prop, value)
                        except:
                            pass


def set_radius(curve, radius=0.5):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        curve.data.bevel_depth = radius


def set_smooth(curve, smooth=True):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        for spline in curve.data.splines:
            spline.use_smooth = smooth


def set_spline_type(curve, spline_type='BEZIER'):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        if spline_type in {'POLY', 'BEZIER', 'NURBS'}:
            for spline in curve.data.splines:
                spline.type = spline_type


def set_bevel_resolution(curve, resolution=0):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        curve.data.bevel_resolution = resolution


def set_fill_end_caps(curve, fill_end_caps=True):
    if isinstance(curve, bpy.types.Object) and isinstance(curve.data, bpy.types.Curve):
        curve.data.use_fill_caps = fill_end_caps
