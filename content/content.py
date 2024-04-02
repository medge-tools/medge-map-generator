from bpy.types import Object

from ..dataset.dataset  import Attribute, get_dataset
from ..dataset.props    import get_dataset
from ..b3d_utils        import duplicate_object


# -----------------------------------------------------------------------------
def populate(obj: Object, modules: list[Object]):
    if not get_dataset(obj).is_dataset: return

    dataset = get_dataset(obj)

    for entry in dataset:
        s = entry[Attribute.PLAYER_STATE.label]
        l = entry[Attribute.LOCATION.label]

        m = modules[s]
        
        if not m: continue

        o = duplicate_object(m, True)
        o.location = l
