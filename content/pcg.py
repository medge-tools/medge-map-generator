from bpy.types import Object

from ..dataset.dataset  import DatasetOps
from ..dataset.props    import is_dataset


def generate(obj: Object):
    if not is_dataset(obj): return

    t, s, l, c = DatasetOps.get_data(obj)

     
