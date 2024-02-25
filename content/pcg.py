from bpy.types import Object

from ..dataset.dataset  import *
from ..dataset          import props


def generate(obj: Object):
    if not props.is_dataset(obj): return

    t, s, l, c = DatasetOps.get_data(obj)

    