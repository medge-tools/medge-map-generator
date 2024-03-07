from bpy.types import Object

from ..dataset.dataset  import DatasetOps
from ..dataset.props    import get_dataset
from ..b3d_utils        import duplicate_object


# -----------------------------------------------------------------------------
def populate(obj: Object, modules: list[Object]):
    if not get_dataset(obj).is_dataset: return

    states, locations, _, _ = DatasetOps.get_data(obj)

    for k in range(len(states)):
        s = states[k]
        l = locations[k]

        m = modules[s]
        
        if not m: continue

        o = duplicate_object(m, True)
        o.location = l
