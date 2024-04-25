import bpy
from bpy.types import Object
from mathutils import Vector

from copy         import deepcopy

from ..dataset.dataset  import Attribute, is_dataset, get_dataset
from ..b3d_utils        import duplicate_object, rotation_matrix, union_objects
from .props             import MET_PG_Module


# -----------------------------------------------------------------------------
def populate(_obj:Object, _modules:list[MET_PG_Module]):
    if not is_dataset(_obj): return

    dataset = get_dataset(_obj)

    states = dataset[:, Attribute.STATE.value]
    vertices = _obj.data.vertices
    
    copies = []

    for k in range(0, len(vertices) - 1, 1):
        print(f'---Iteration: {k}------------------------------------------------------------')

        s = states[k]
        p1 = vertices[k].co
        
        p2 = deepcopy(vertices[k + 1].co)

        o = _modules[s].random_object()
        
        if not o: continue

        copy = duplicate_object(o, False, 'POPULATED_' + _obj.name)
        
        # Rotation to align with the path direction in the xy-plane
        p2.z = p1.z
        R = rotation_matrix(Vector((0, 1, 0)), (p2 - p1).normalized())
        R.resize_4x4()
        copy.matrix_world = R @ copy.matrix_world

        # Location
        copy.location = _obj.matrix_world @ p1

        # Finalize
        copies.append(copy)

    # Join objects
    
