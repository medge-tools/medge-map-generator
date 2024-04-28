import bpy
from bpy.types import Object
from mathutils import Vector

from math import pi

from ..dataset.dataset  import Attribute, is_dataset, dataset_entries
from ..b3d_utils        import duplicate_object, join_objects, mesh_bounds, set_active, remove_object
from .props             import MET_PG_Module


# -----------------------------------------------------------------------------
def populate(_obj:Object, _modules:list[MET_PG_Module]):
    if not is_dataset(_obj): return

    copies = []

    entries = dataset_entries(_obj)
    entry = next(entries)

    curr_location = entry[Attribute.LOCATION.value]

    for entry in entries:
        # Get module
        s = entry[Attribute.STATE.value]

        module = _modules[s].random_object()
        
        if not module: continue
        
        # Calculate the start and end locations using the boundings box
        # We assume that the direction of modules are in the +y direction
        origin = module.location
        bbmin, bbmax = mesh_bounds(module)

        x = (bbmin.x + bbmax.x) * .5
        start = Vector((x, bbmin.y, origin.z))
        end = Vector((x, bbmax.y, origin.z))

        curr_location += origin - start

        curve = duplicate_object(module, False, 'POPULATED_' + _obj.name)
        curve.location = curr_location
        copies.append(curve)

        curr_location += end - origin

    # Join the placed objects into one objects and curve them using the curve modifier
    population = join_objects(copies)
    mod = population.modifiers.new('Curve', 'CURVE')

    # Convert the dataset object to a curve
    curve = duplicate_object(_obj)
    bpy.ops.object.convert(target='CURVE')

    # Keep modules parallel to the +z axis
    curve.data.twist_mode = 'Z_UP'
    for p in curve.data.splines.active.points:
        p.tilt = pi * .5

    # Set the curve modifier settings
    mod.object = curve
    mod.deform_axis = 'POS_Y'

    # Apply the modifier
    set_active(population)
    bpy.ops.object.modifier_apply(modifier="Curve")
    
    # Delete the curve
    remove_object(curve)