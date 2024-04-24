from bpy.types import Object
from mathutils import Vector

from copy         import deepcopy
from numpy.random import choice

from ..dataset.dataset  import Attribute, is_dataset, get_dataset
from ..b3d_utils        import duplicate_object, rotation_matrix
from .props             import MET_PG_Module

# -----------------------------------------------------------------------------
def populate(_obj:Object, _modules:list[MET_PG_Module]):
    if not is_dataset(_obj): return

    dataset = get_dataset(_obj)

    for e1, e2 in zip(dataset, dataset[1:]):
        s = e1[Attribute.PLAYER_STATE.value]
        p1 = e1[Attribute.LOCATION.value]
        
        p2 = e2[Attribute.LOCATION.value]
        p2 = deepcopy(p2)

        obj = _modules[s].random_object()
        
        if not obj: continue

        o = duplicate_object(obj, True)
        
        # Rotation in the xy-plane
        p2.z = p1.z
        R = rotation_matrix(Vector((0, 1, 0)), (p2 - p1).normalized())
        R.resize_4x4()
        o.matrix_world = R @ o.matrix_world

        # Location
        o.location = p1