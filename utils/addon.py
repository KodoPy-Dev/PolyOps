########################•########################
"""                   KodoPy                  """
########################•########################

import bpy

addon_name = __name__.partition('.')[0]


def user_prefs():
    return bpy.context.preferences.addons[addon_name].preferences


def exists(name=""):
    for addon_name in bpy.context.preferences.addons.keys():
        if name in addon_name: return True
    return False


def version(as_label=False):
    from .. import bl_info
    version = bl_info['version']
    if as_label:
        return f"PolyOps {version[0]}.{version[1]}"
    return version
