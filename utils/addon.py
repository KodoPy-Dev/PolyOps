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


def version(opt='POLY_OPS', as_label=False):
    if opt == 'POLY_OPS':
        from .. import POLY_OPS_VERSION
        if as_label:
            return f"PolyOps {POLY_OPS_VERSION[0]}.{POLY_OPS_VERSION[1]}"
        else:
            return POLY_OPS_VERSION
    elif opt == 'RAZOR':
        from .. import RAZOR_VERSION
        if as_label:
            return f"Razor -{RAZOR_VERSION[0]}.{RAZOR_VERSION[1]}"
        else:
            return RAZOR_VERSION
    if as_label:
        return ''
    return 0
