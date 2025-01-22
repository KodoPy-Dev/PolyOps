########################•########################
"""                   KodoPy                  """
########################•########################

import os
from . import blends
from . import shapes
from .shapes import workplane
from . import icon


def directory_location():
    return os.path.dirname(os.path.abspath(__file__))


