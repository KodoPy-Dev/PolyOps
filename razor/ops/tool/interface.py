########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from .data import DB
from ....utils.modal_status import UX_STATUS
from .... import utils


OPS_MENU = None


class OpsMenu:
    def __init__(self):
        self.status = UX_STATUS.INACTIVE
        self.menu = None


    def setup(self, context, event):
        PropMap   = utils.modal_ux.PropMap
        Row       = utils.modal_ux.Row
        Container = utils.modal_ux.Container
        Menu      = utils.modal_ux.Menu
        box_len   = 6

        map_1 = PropMap(label="Cancel" , instance=self, prop_name='menu_callback', box_len=box_len)
        map_2 = PropMap(label="Undo"   , instance=self, prop_name='menu_callback', box_len=box_len)
        map_3 = PropMap(label="Confirm", instance=self, prop_name='menu_callback', box_len=box_len)
        row_1 = Row(label="", prop_maps=[map_1, map_2, map_3], min_borders=True)
        cont_1 = Container(label="", rows=[row_1])

        self.menu = Menu(context, event, containers=[cont_1])


    def menu_callback(self, context, event, prop_map):
        razor = DB.razor
        label = prop_map.label
        if label == "Confirm":
            razor.ops.status = 'FINISHED'
        elif label == "Cancel":
            razor.ops.status = 'CANCELLED'
        elif label == "Undo":
            DB.graph.undo()


    def update(self, context, event):
        razor = DB.razor
        self.menu.update(context, event)
        razor.ops.in_menu = False
        if self.menu.status == UX_STATUS.ACTIVE:
            razor.ops.in_menu = True


def setup():
    context = DB.runtime.context
    event   = DB.runtime.event

    global OPS_MENU
    OPS_MENU = OpsMenu()
    OPS_MENU.setup(context, event)


def update():
    context = DB.runtime.context
    event   = DB.runtime.event
    prefs   = DB.prefs
    razor   = DB.razor

    global OPS_MENU
    if isinstance(OPS_MENU, OpsMenu):
        OPS_MENU.update(context, event)


def close():
    context = bpy.context
    global OPS_MENU
    if isinstance(OPS_MENU, OpsMenu):
        OPS_MENU.menu.close(context)
    OPS_MENU = None


def draw_menus():
    global OPS_MENU
    if isinstance(OPS_MENU, OpsMenu):
        OPS_MENU.menu.draw()








