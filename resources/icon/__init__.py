########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bpy.utils.previews
import os

ICONS_COLLECTION = None
DIRECTORY = os.path.dirname(__file__)


def get_icon_directory():
    return DIRECTORY


def icon_id(icon_name=""):
    if icon_name in ICONS_COLLECTION:
        return ICONS_COLLECTION[icon_name].icon_id
    return ICONS_COLLECTION.load(icon_name, os.path.join(DIRECTORY, icon_name + ".png"), "IMAGE").icon_id


def icon_pr(icon_name=""):
    if icon_name in ICONS_COLLECTION:
        return ICONS_COLLECTION[icon_name]
    return ICONS_COLLECTION.load(icon_name, os.path.join(DIRECTORY, icon_name + ".png"), "IMAGE")


def register_icons_collection():
    global ICONS_COLLECTION
    if ICONS_COLLECTION is None:
        ICONS_COLLECTION = bpy.utils.previews.new()


def unregister_icons_collection():
    global ICONS_COLLECTION
    if ICONS_COLLECTION is not None:
        bpy.utils.previews.remove(ICONS_COLLECTION)
        ICONS_COLLECTION = None
