########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from enum import Enum
from .misc import last_created_by_name_ext

########################•########################
"""                  MANAGMENT                """
########################•########################

def valid_collection(collection):
    if type(collection) == bpy.types.Collection:
        return True
    return False


def scence_collections(context, exclude=[]):
    collections = [collection for collection in context.scene.collection.children_recursive if collection not in exclude]
    if context.scene.collection not in exclude:
        collections.append(context.scene.collection)
    return collections


def visible_scene_collections(context):
    def collect(collections, layer):
        if layer.exclude == False:
            if layer.hide_viewport == False:
                if layer.collection.hide_viewport == False:
                    collections.append(layer.collection)
        for layer in layer.children:
            collect(collections, layer)
    collections = []
    collect(collections, layer=context.view_layer.layer_collection)
    return collections


def layer_path_to_collection(context, collection, remove_top_scene_layer=True):
    if not valid_collection(collection):
        return []
    if collection not in scence_collections(context):
        return []
    def search(path, layer, collection):
        if layer.collection == collection:
            path.append(layer)
        else:
            for child_layer in layer.children:
                search(path, layer=child_layer, collection=collection)
                if path and path[-1] == child_layer:
                    path.append(layer)
                    return
    path = []
    search(path, layer=context.view_layer.layer_collection, collection=collection)
    path.reverse()
    if remove_top_scene_layer == True and context.view_layer.layer_collection in path:
        path.remove(context.view_layer.layer_collection)
    return path


def collection_path_settings(context, collection, exclude=True, hide_viewport=True, hide_render=True):
    if not valid_collection(collection):
        return
    layer_path = layer_path_to_collection(context, collection, remove_top_scene_layer=True)
    if not layer_path:
        return
    for layer in layer_path:
        layer.exclude = exclude
        layer.hide_viewport = hide_viewport
        layer.collection.hide_viewport = hide_viewport
        layer.collection.hide_render = hide_render


def unlink_collection(context, target_collection):
    if not valid_collection(target_collection):
        return
    for collection in scence_collections(context, exclude=[target_collection]):
        if target_collection.name in collection.children:
            collection.children.unlink(target_collection)


def link_collection(context, parent_collection, child_collection):
    if not valid_collection(parent_collection):
        return
    if not valid_collection(child_collection):
        return
    collections = scence_collections(context)
    parent_collection.children.link(child_collection)


def link_object_to_collection(target_collection, obj):
    if not obj:
        return
    if not valid_collection(target_collection):
        return
    if obj.name not in target_collection.objects:
        target_collection.objects.link(obj)


def unlink_object_from_all_collections(context, obj):
    if not obj:
        return
    collections = scence_collections(context)
    for collection in obj.users_collection[:]:
        if collection in collections:
            if obj.name in collection.objects:
                collection.objects.unlink(obj)


def get_collection(context, name='', create_new=True):
    collections = scence_collections(context)
    for collection in collections:
        if name == collection.name:
            return collection
    collection = last_created_by_name_ext(name=name, objects=[coll for coll in collections if name in coll.name])
    if valid_collection(collection):
        return collection
    if create_new:
        collection = bpy.data.collections.new(name)
        context.scene.collection.children.link(collection)
        return collection
    return None


def ensure_object_collections_visible(context, obj, hide_others_if_exclude=True):
    if not isinstance(obj, bpy.types.Object):
        return
    if not any([scene == context.scene for scene in obj.users_scene]):
        context.scene.collection.objects.link(obj)
        return
    scene_collections = context.scene.collection.children_recursive
    for user_coll in obj.users_collection:
        if user_coll in scene_collections:
            layer_path = layer_path_to_collection(context, user_coll, remove_top_scene_layer=True)
            if layer_path:
                for layer in layer_path:
                    # layer_excluded = not layer.exclude
                    layer_excluded = layer.exclude
                    layer.exclude = False
                    layer.hide_viewport = False
                    layer.collection.hide_viewport = False
                    # Hide all objects in excluded layer
                    if hide_others_if_exclude and layer_excluded:
                        for obj_in_collection in layer.collection.objects:
                            if obj_in_collection != obj:
                                obj_in_collection.hide_set(True, view_layer=context.view_layer)

########################•########################
"""                   COLORS                  """
########################•########################

class Color_Tags(Enum):
    COLOR_01 = 1 # RED
    COLOR_02 = 2 # ORANGE
    COLOR_03 = 3 # YELLOW
    COLOR_04 = 4 # GREEN
    COLOR_05 = 5 # BLUE
    COLOR_06 = 6 # PURPLE
    COLOR_07 = 7 # PINK
    COLOR_08 = 8 # BROWN


def color_tag_collection(collection, color=Color_Tags.COLOR_05):
    collection.color_tag = color.name

########################•########################
"""              PolyOps Collections          """
########################•########################

def polyops_collection(context):
    collection = get_collection(context, name='PolyOps', create_new=True)
    color_tag_collection(collection, Color_Tags.COLOR_04)
    unlink_collection(context, target_collection=collection)
    link_collection(context, parent_collection=context.scene.collection, child_collection=collection)
    return collection


def boolean_collection(context):
    parent_collection = polyops_collection(context)
    collection = get_collection(context, name='Booleans', create_new=True)
    color_tag_collection(collection, Color_Tags.COLOR_01)
    unlink_collection(context, target_collection=collection)
    link_collection(context, parent_collection=parent_collection, child_collection=collection)
    return collection


def utility_collection(context):
    parent_collection = polyops_collection(context)
    collection = get_collection(context, name='Utility', create_new=True)
    color_tag_collection(collection, Color_Tags.COLOR_06)
    unlink_collection(context, target_collection=collection)
    link_collection(context, parent_collection=parent_collection, child_collection=collection)
    return collection


def razor_collection(context):
    parent_collection = polyops_collection(context)
    collection = get_collection(context, name='Razor', create_new=True)
    color_tag_collection(collection, Color_Tags.COLOR_05)
    unlink_collection(context, target_collection=collection)
    link_collection(context, parent_collection=parent_collection, child_collection=collection)
    return collection


