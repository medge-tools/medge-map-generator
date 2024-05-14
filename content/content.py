import bpy
from bpy.types import Object, Context, Collection
from mathutils import Vector

from math import pi

from ..                import b3d_utils
from ..dataset.dataset import is_dataset, dataset_sequences
from .props            import MET_PG_Module, get_population_prop


# -----------------------------------------------------------------------------
def populate(_obj:Object, _modules:list[MET_PG_Module], _context:Context):
    if not is_dataset(_obj): return

    collection_name = 'POPULATED_' + _obj.name
    population:list[tuple[Object, int]] = []
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
            bbmin, bbmax = b3d_utils.mesh_bounds(module)

            x = (bbmin.x + bbmax.x) * .5
            start = Vector((x, bbmin.y, origin.z))
            end = Vector((x, bbmax.y, origin.z))

            curr_length += (end - start).length

            if curr_length >= total_length:
                break

            next_location += origin - start

            module = b3d_utils.duplicate_object(module, True, collection_name)
            module.name = f'{n_module}_{module.name}'
            module.location = next_location
            population.append((module, state))

            next_location += end - origin
            n_module += 1

    # Align the population the curve. Some objects deform along the z-axis, some don't 

    # Convert the dataset object to a curve
    curve_3d = b3d_utils.duplicate_object(_obj, False, collection_name)
    bpy.ops.object.convert(target='CURVE')

    # Keep modules parallel to the +z axis
    curve_3d.data.twist_mode = 'Z_UP'

    def center(_obj:Object):
        center = Vector()
        vertices = _obj.data.vertices
        for v in vertices:
            center += _obj.matrix_world @ v.co
        return center / len(vertices)

    # We need the 3D locations if the objects should not deform along the z-axis
    locations_3d = []

    for module, state in population:
        deform_z = _modules[state].deform_z

        temp = module
        if not deform_z:
            temp = b3d_utils.duplicate_object(module, False)

        mod = temp.modifiers.new('Curve', 'CURVE')
        mod.object = curve_3d
        mod.deform_axis = 'POS_Y'

        if deform_z: continue

        bpy.ops.object.modifier_apply(modifier='Curve')
        locations_3d.append(center(temp))
        b3d_utils.remove_object(temp)

    # Project the curve to the xy-plane
    curve_2d = b3d_utils.duplicate_object(curve_3d)
    curve_2d.data.dimensions = '2D'

    # Align every object to the 2D curve that should NOT deform along z
    for k, (module, state) in enumerate(population):
        deform_z = _modules[state].deform_z

        if deform_z: continue

        mod = module.modifiers.new('Curve', 'CURVE')
        mod.object = curve_2d
        mod.deform_axis = 'POS_Y'
                
        # Because of the curve modifier we have to change to x-value to move it along the z-axis
        module.location.x = locations_3d[k].z - center(module).z

        # The curve modifier rotates the object for some reason, changing the tilt on a 2D curve has no affect
        # Instead we rotate it back
        module.rotation_euler.y = pi * .5
    
    # Update collection property
    collection = bpy.data.collections[collection_name]
    get_population_prop(collection).has_content = True


def finalize(_collection: Collection):
    for obj in _collection.objects:
        if obj.type == 'CURVE':
            b3d_utils.remove_object(obj)
            continue

        b3d_utils.set_active_object(obj)
        bpy.ops.object.modifier_apply(modifier='Curve', single_user=True)

    