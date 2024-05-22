import bpy
from bpy.types import Object, Context, Collection, Mesh, MeshEdges
from mathutils import Vector

import math
import copy
from collections import UserList

from ..                import b3d_utils
from ..dataset.dataset import is_dataset, dataset_sequences
from .props            import MET_PG_ModuleState, get_population_prop, get_module_prop


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def eval_world_center(_obj:Object):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = _obj.evaluated_get(depsgraph)

    center = Vector()
    vertices = obj_eval.data.vertices
    
    for v in vertices:
        center += _obj.matrix_world @ v.co
    
    return center / len(vertices)


# -----------------------------------------------------------------------------
def get_bounds_data(_obj:Object):
    # Calculate the start and end locations using the bounding box
    # We assume that the direction of modules are in the +x direction
    origin = _obj.location.copy()
    origin.y = 0
    
    bbmin, bbmax = b3d_utils.mesh_bounds(_obj)

    bb_start = Vector((bbmin.x, 0, origin.z))
    bb_end = Vector((bbmax.x, 0, origin.z))

    return origin, bb_start, bb_end


# -----------------------------------------------------------------------------
def rotate_xy(_origin:Vector, _point:Vector, _angle:float):
    ox, oy = _origin.xy
    px, py = _point.xy

    cos = math.cos(_angle)
    sin = math.sin(_angle)

    dx = px - ox
    dy = py - oy

    x = ox + cos * dx - sin * dy
    y = oy + sin * dx + cos * dy

    return x, y


# -----------------------------------------------------------------------------
def translate_object_along_curve_to_location(_obj:Object, _target:Vector, _step:int):
    """
    This will move the object along the curve to the start of the chain
    We deform in the +x-axis, so we move in -x direction

    This should only be done for the first object in the chain
    The resulting offset should be applied the rest of the chain
    """
    origin, bb_start, _ = get_bounds_data(_obj)
    min_distance = (origin - bb_start).length

    curr_location = eval_world_center(_obj)

    while (curr_location - _target).length > min_distance:
        _obj.location -= _step
        curr_location  = eval_world_center(_obj)


# -----------------------------------------------------------------------------
class PopObject:

    def __init__(self, _parent:Object, _children:list[Object], _state:int):
        self.parent = _parent
        self.children = _children
        self.state = _state


# -----------------------------------------------------------------------------
class PopChain(UserList):

    def __init__(self, _start_location:Vector) -> None:
        super().__init__()
        self.start_location = _start_location


# -----------------------------------------------------------------------------
class Population(UserList):
    """
    `list[list[PopObject]]`
    """
    def __init__(self):
        super().__init__()
        self.continuous  = []
        self.data_offset = []


    def append(self, item:PopChain):
        if (size := len(item)) == 0: return

        if len(self.data_offset) == 0:
            self.data_offset.append(0)
        else:
            self.data_offset.append(len(self.continuous))

        outer_idx = len(self.data)

        self.data.append(item)
        self.continuous.extend([(outer_idx, inner_idx) for inner_idx in range(0, size)])


    def get_look_at_next_angle(self, _outer_idx:int, _inner_idx:int):
        """
        Calculate the angle first, before making modifications to the object
        The angle calculations depend on the locations while deformed by 3D curve
        """
        offset = self.data_offset[_outer_idx]
        idx    = offset + _inner_idx

        start_idx = idx
        end_idx   = idx + 1

        if end_idx >= len(self.continuous):
            start_idx = idx - 1
            end_idx   = idx

        j1, k1 = self.continuous[start_idx]
        j2, k2 = self.continuous[end_idx]

        pop1:PopObject = self.data[j1][k1]
        pop2:PopObject = self.data[j2][k2]

        start = eval_world_center(pop1.parent)
        end   = eval_world_center(pop2.parent)

        start.z = 0
        end.z   = 0

        direction = (start - end).normalized()

        # We assume that modules face the +x direction
        return direction.angle(Vector((1, 0, 0))) * -1
        

# -----------------------------------------------------------------------------
# Populate Dataset Object
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def populate(_dataset:Object, _module_states:list[MET_PG_ModuleState]):
    if not is_dataset(_dataset): return

    # To select sharp edges we need to be in object mode
    b3d_utils.set_object_mode(_dataset, 'OBJECT')

    collection_name = 'POPULATED_' + _dataset.name
    population:list[PopChain] = Population()

    next_location = None
    start_location = None

    idx = 0

    # Convert the dataset object to a curve
    curve_3d = b3d_utils.duplicate_object(_dataset, False, collection_name)
    bpy.ops.object.convert(target='CURVE')
    # Keep the +z-axis of modules parallel to the world +z axis
    curve_3d.data.twist_mode = 'Z_UP'


    def align_module(_obj:Object, _location:Vector):
        nonlocal collection_name, curve_3d, idx
        
        # Duplicated module and place
        copy = b3d_utils.duplicate_object(_obj, False, collection_name)

        b3d_utils.unparent(copy)
        copy.location = _location

        # Add curve modifier
        mod = copy.modifiers.new('Curve', 'CURVE')
        mod.object = curve_3d
        mod.deform_axis = 'POS_X'

        # Append
        copy.name = f'{idx}_{_obj.name}'
        idx += 1

        return copy


    print()
    print('Duplicating and aligning modules...')
    for state, locations, total_length in dataset_sequences(_dataset):
        
        pop_chain = PopChain(locations[0].copy())


        def next_chain():
            nonlocal next_location, start_location, total_length
            nonlocal population, pop_chain

            next_location.x = start_location.x + total_length
            start_location.x = next_location.x

            population.append(pop_chain)


        if not next_location:
            next_location = locations[0].copy()
            start_location = next_location.copy()

        curr_length = 0        
        mstate = _module_states[state]

        while True:
            # Get module
            obj = mstate.random_object()
            
            # If there are no modules assigned, move the next_location to the end of the chain
            if not obj: 
                next_chain()
                break
            
            origin, bb_start, bb_end = get_bounds_data(obj)

            curr_length += (bb_end - bb_start).length

            if curr_length > total_length:
                next_chain()
                break

            new_location = next_location + origin - bb_start

            parent = align_module(obj, new_location)
            children = []

            for child in obj.children:
                offset = child.location - obj.location
                c = align_module(child, new_location + offset)
                children.append(c)
            
            offset = new_location.x - start_location.x

            pop_chain.append(PopObject(parent, children, state, offset))
            
            if mstate.only_at_chain_start: 
                next_chain()
                break

            next_location += bb_end - bb_start


    print('Update objects according to module settings...')
    # Duplicate the curve and project it to the xy-plane
    # This curve is used when a object is not to be deformed in the z-axis
    curve_2d = b3d_utils.duplicate_object(curve_3d, False, collection_name)
    curve_2d.data.dimensions = '2D'

    # Update objects according to module settings
    for j, pop_chain in enumerate(population):
        for k, pop_obj in enumerate(pop_chain):
            parent = pop_obj.parent

            p_prop = get_module_prop(parent)
            p_mod  = parent.modifiers[0]

            # Parent world center while deformed by 3D curve
            p_wc1 = eval_world_center(parent)
            # Parent world center while deformed by 2D curve
            p_mod.object = curve_2d
            p_wc2 = eval_world_center(parent)

            parent_offset = p_wc1 - p_wc2

            angle = None

            # Deform children first, because we might need the parent in it's original location
            for child in pop_obj.children:
                c_prop = get_module_prop(child)
                c_mod  = child.modifiers[0]

                local_offset = child.location - parent.location

                if c_prop.deform:
                    if c_prop.deform_z:
                        c_mod.object = curve_3d

                    else:
                        c_mod.object = curve_2d

                        child.location.z  = parent_offset.z + local_offset.z
                        child.location.x -= pop_obj.distance_to_start

                else:
                    # Calculate the angle first, before making modifications to the object
                    # The angle calculations depend on the locations while deformed by 3D curve
                    if not angle:
                        angle = population.get_look_at_next_angle(j, k)

                    c_mod.object = None

                    child.location  = p_wc1.copy()
                    child.location += local_offset

                    child.location.xy      = rotate_xy(p_wc1, child.location, angle)
                    child.rotation_euler.z = angle

            # Deform parent
            if p_prop.deform:
                if p_prop.deform_z:
                    p_mod.object = curve_3d

                else:
                    p_mod.object = curve_2d
                    
                    parent.location.z  = parent_offset.z
                    parent.location.x -= pop_obj.distance_to_start

            else:
                # Calculate the angle first, before making modifications to the object
                # The angle calculations depend on the locations while deformed by 3D curve
                if not angle:
                    angle = population.get_look_at_next_angle(j, k)

                p_mod.object = None

                parent.location = p_wc1.copy()
                parent.rotation_euler.z = angle


    # Update collection property
    collection = bpy.data.collections[collection_name]
    get_population_prop(collection).has_content = True

    print('Finished')

    return
    
   
    # The xy position for a object differs if the curve is in 3D or 2D
    # To compensate we calculate a chain offset.
    # This calculation happens at the start of each chain 
    chain_offset_x = 0
    curr_state = -1

    for j, (obj, state) in enumerate(population):
        p_prop = get_module_prop(obj)

        # Curve deform objects
        if p_prop.deform:
            p_mod = obj.modifiers.new('Curve', 'CURVE')
            p_mod.deform_axis = 'POS_X'

            if p_prop.deform_z:
                p_mod.object = curve_3d

            else:
                p_mod.object = curve_2d

                p_wc1:Vector = curve_wcenters[j]
                p_wc2:Vector = eval_world_center(obj)
                
                obj.location.z = p_wc1.z - p_wc2.z
                
                # Calculate chain offset
                if curr_state != state:
                    curr_state = state

                    p_wc1.z = p_wc2.z = 0
                    chain_offset_x = (p_wc1 - p_wc2).length
                
                #mobj.location.x -= chain_offset
                
        # Manually place objects
        else:
            obj.location = curve_wcenters[j] #+ wcenter_origin_offsets[k]
            obj.rotation_euler.z = directions[j].angle(Vector((1, 0, 0))) * -1


    # Update collection property
    collection = bpy.data.collections[collection_name]
    get_population_prop(collection).has_content = True

    print('Finished')


def finalize(_collection: Collection):
    for obj in _collection.objects:
        if obj.type == 'CURVE':
            b3d_utils.remove_object(obj)
            continue

        b3d_utils.set_active_object(obj)
        bpy.ops.object.modifier_apply(modifier='Curve', single_user=True)

    