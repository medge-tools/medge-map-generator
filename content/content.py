import bpy
from bpy.types import Object, Context, Collection
from mathutils import Vector

from math import pi

from ..dataset.dataset import is_dataset, dataset_sequences
from ..b3d_utils       import duplicate_object, mesh_bounds, remove_object, set_active
from .props            import MET_PG_Module, get_population_prop


# -----------------------------------------------------------------------------
def populate(_obj:Object, _modules:list[MET_PG_Module], _context:Context):
    if not is_dataset(_obj): return

    collection_name = 'POPULATED_' + _obj.name
    population = []
    next_location = None

    n_module = 0
    for state, locations, total_length in dataset_sequences(_obj, True):
        if not next_location:
            next_location = locations[0]
        
        curr_length = 0

        while True:
            # Get module
            module = _modules[state].random_object()
            
            if not module:
                next_location.y += total_length
                break
            
            # Calculate the start and end locations using the bounding box
            # We assume that the direction of modules are in the +y direction
            origin = module.location
            bbmin, bbmax = mesh_bounds(module)

            x = (bbmin.x + bbmax.x) * .5
            start = Vector((x, bbmin.y, origin.z))
            end = Vector((x, bbmax.y, origin.z))

            curr_length += (end - start).length

            if curr_length >= total_length:
                break

            next_location += origin - start

            m = duplicate_object(module, True, collection_name)
            m.name = f'{n_module}_{m.name}'
            m.location = next_location
            population.append(m)

            next_location += end - origin
            n_module += 1

    # Join the placed objects into one objects and curve them using the curve modifier
    # population = join_objects(copies)
    # mod = population.modifiers.new('Curve', 'CURVE')

    # Convert the dataset object to a curve
    curve = duplicate_object(_obj, False, collection_name)
    bpy.ops.object.convert(target='CURVE')

    # Keep modules parallel to the +z axis
    curve.data.twist_mode = 'Z_UP'

    # Align copies to curve using a curve modifier
    # We only want them to deform along the z-axis:
    # - Deform a copy of the object using the 3D curve and store the z value
    # - Deform the object using the 2D curve and set the z value

    def center(_obj:Object):
        center = Vector()
        vertices = _obj.data.vertices
        for v in vertices:
            center += _obj.matrix_world @ v.co
        return center / len(vertices)

    # Get the locations 3D
    locations_3d = []

    for c in population:
        c2 = duplicate_object(c, False)
        mod = c2.modifiers.new('Curve', 'CURVE')
        mod.object = curve
        mod.deform_axis = 'POS_Y'
        bpy.ops.object.modifier_apply(modifier='Curve')
        locations_3d.append(center(c2))
        remove_object(c2)

    # Project the curve to the xy-plane
    curve.data.dimensions = '2D'

    for k, c in enumerate(population):
        mod = c.modifiers.new('Curve', 'CURVE')
        mod.object = curve
        mod.deform_axis = 'POS_Y'
                
        # Because of the curve modifier we have to change to x-value to move it along the z-axis
        c.location.x = locations_3d[k].z - center(c).z

        # The curve modifier rotates the object for some reason, changing the title on a 2D curve has no affect
        # Instead we rotate it back
        c.rotation_euler.y = pi * .5
    
    # Update collection property
    collection = bpy.data.collections[collection_name]
    get_population_prop(collection).has_content = True


def finalize(_collection:Collection):
    for obj in _collection.objects:
        if obj.type == 'CURVE':
            remove_object(obj)
            continue
        set_active(obj)
        bpy.ops.object.modifier_apply(modifier='Curve', single_user=True)

    