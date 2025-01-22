########################•########################
"""                   KodoPy                  """
########################•########################

from enum import Enum


class MODAL_STATUS(Enum):
    RUNNING = 0
    CONFIRM = 1
    CANCEL = 2
    ERROR = 3
    PASS = 4


class UX_STATUS(Enum):
    ACTIVE = 0
    INACTIVE = 1


class OPS_STATUS(Enum):
    COMPLETED = 0
    CANCELLED = 1
    ACTIVE = 2
    INACTIVE = 3
    PASS = 4

