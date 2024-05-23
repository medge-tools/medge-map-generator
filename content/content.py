import bpy
from bpy.types import Object, Collection
from mathutils import Vector

import math
from collections import UserList

from ..                 import b3d_utils
from ..dataset.movement import State
from ..dataset.dataset  import is_dataset, dataset_sequences
from .props             import MET_PG_ModuleState, get_population_prop, get_module_prop


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
class PopObject:

    def __init__(self, _parent:Object, _children:list[Object], _state:int):
        self.parent = _parent
        self.children = _children
        self.state = _state


# -----------------------------------------------------------------------------
class PopChain(UserList):
    pass


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


    def get_look_at_angle(self, _outer_idx:int, _inner_idx:int):
        """
        Calculates the angle to rotate the object to face the next object.
        It assumes the object is facing the +x direction
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

        direction = (end - start).normalized()

        a = -1
        if direction.y > 0:
            a = 1

        # We assume that modules face the +x direction
        return direction.angle(Vector((1, 0, 0))) * a
        

# -----------------------------------------------------------------------------
# Populate Dataset Object
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def populate(_dataset:Object, _module_states:list[MET_PG_ModuleState]):
    if not is_dataset(_dataset): return

    b3d_utils.set_object_mode(_dataset, 'OBJECT')

    main_collection     = b3d_utils.new_collection('POPULATED_' + _dataset.name)

    curve_3d_mod_name = 'Curve_3D'
    curve_2d_mod_name = 'Curve_2D'

    population:list[list[PopObject]] = Population()

    m_idx = 0

    print()
    print('Duplicating and aligning modules...')
    for k, (state, locations, total_length) in enumerate(dataset_sequences(_dataset)):
        
        pop_chain = PopChain()

        # Create collection
        current_collection  = b3d_utils.new_collection(f'{k}_{State(state).name}', main_collection)
        modules_collection  = b3d_utils.new_collection(f'{k}_MODULES_' + _dataset.name, current_collection)
        curve_3d_collection = b3d_utils.new_collection(f'{k}_CURVES_3D_' + _dataset.name, current_collection)
        curve_2d_collection = b3d_utils.new_collection(f'{k}_CURVES_2D_' + _dataset.name, current_collection)

        # Create curves
        curve_data, path = b3d_utils.create_curve(len(locations))

        for p1, p2 in zip(path.points, locations):
            p1.co = (*p2, 1)

        curve_3d = b3d_utils.new_object(f'{k}_CURVE_3D', curve_data, curve_3d_collection)
        
        # Duplicate the curve and project it to the xy-plane
        # This curve is used when a object is not to be deformed in the z-axis
        curve_2d = b3d_utils.duplicate_object(curve_3d, False, curve_2d_collection)
        curve_2d.data.dimensions = '2D'
        curve_2d.name = f'{k}_CURVE_2D'


        def align_module(_obj:Object, _location:Vector):
            nonlocal modules_collection, m_idx
            nonlocal curve_3d, curve_2d

            # Duplicated module and place
            copy = b3d_utils.duplicate_object(_obj, False, modules_collection)

            b3d_utils.unparent(copy)

            copy.location = _location

            # Add curve modifier
            mod = copy.modifiers.new(curve_3d_mod_name, 'CURVE')
            mod.object = curve_3d
            mod.deform_axis = 'POS_X'
            mod.show_viewport = True

            # Add curve modifier
            mod = copy.modifiers.new(curve_2d_mod_name, 'CURVE')
            mod.object = curve_2d
            mod.deform_axis = 'POS_X'
            mod.show_viewport = False

            # Append
            copy.name = f'{m_idx}_{_obj.name}'
            m_idx += 1

            return copy


        next_location = Vector()
        mstate = _module_states[state]
        curr_length = 0        

        while True:
            # Get module
            obj = mstate.random_object()
            
            # If there are no modules assigned, move the next_location to the end of the chain
            if not obj: break
            
            origin, bb_start, bb_end = get_bounds_data(obj)

            curr_length += (bb_end - bb_start).length

            if curr_length > total_length:
                population.append(pop_chain); break

            new_location = next_location + origin - bb_start

            parent   = align_module(obj, new_location)
            children = []

            for child in obj.children:
                offset = child.location - obj.location
                c = align_module(child, new_location + offset)
                children.append(c)
            
            pop_chain.append(PopObject(parent, children, state))
            
            if mstate.only_at_chain_start: 
                population.append(pop_chain); break

            next_location += bb_end - bb_start

    print('Update objects according to module settings...')

    def toggle_curve_modifiers(_obj:Object, _show_3d:bool, _show_2d:bool):
        mod = _obj.modifiers[curve_3d_mod_name]
        mod.show_viewport = _show_3d
        
        mod = _obj.modifiers[curve_2d_mod_name]
        mod.show_viewport = _show_2d


    # Update objects according to module settings
    for j, pop_chain in enumerate(population):
        for k, pop_obj in enumerate(pop_chain):
            parent = pop_obj.parent
            p_prop = get_module_prop(parent)

            # Parent world center while deformed by 3D curve
            toggle_curve_modifiers(parent, True, False)
            p_wc1 = eval_world_center(parent)

            # Parent world center while deformed by 2D curve
            toggle_curve_modifiers(parent, False, True)
            p_wc2 = eval_world_center(parent)

            parent_offset = p_wc1 - p_wc2

            angle = None

            # Deform children first, because we might need the parent in it's current location
            for child in pop_obj.children:
                c_prop       = get_module_prop(child)
                local_offset = child.location - parent.location

                if c_prop.deform:
                    if c_prop.deform_z:
                        toggle_curve_modifiers(child, True, False)

                    else:
                        toggle_curve_modifiers(child, False, True)
                        child.location.z = parent_offset.z + local_offset.z

                else:
                    if not angle:
                        toggle_curve_modifiers(child, True, False)
                        angle = population.get_look_at_angle(j, k)

                    toggle_curve_modifiers(child, False, False)

                    child.location  = p_wc1.copy()
                    child.location += local_offset

                    # Rotate around parent
                    child.location.xy      = rotate_xy(p_wc1, child.location, angle)
                    child.rotation_euler.z = angle

            # Deform parent
            if p_prop.deform:
                if p_prop.deform_z:
                    toggle_curve_modifiers(parent, True, False)

                else:
                    toggle_curve_modifiers(parent, False, True)
                    parent.location.z = parent_offset.z

            else:
                if not angle:
                    toggle_curve_modifiers(parent, True, False)
                    angle = population.get_look_at_angle(j, k)

                toggle_curve_modifiers(parent, False, False)

                parent.location         = p_wc1.copy()
                parent.rotation_euler.z = angle


    # Update collection property
    get_population_prop(main_collection).has_content = True

    print('Finished')

    
# -----------------------------------------------------------------------------
def finalize(_collection: Collection):
    for obj in _collection.objects:
        if obj.type == 'CURVE':
            b3d_utils.remove_object(obj)
            continue

        b3d_utils.set_active_object(obj)
        bpy.ops.object.modifier_apply(modifier='Curve', single_user=True)


# -----------------------------------------------------------------------------
def export(_collection: Collection):
    b3d_utils.deselect_all_objects()

    for obj in _collection.all_objects:
        if obj.medge_actor.type == 'NONE': continue
        b3d_utils.select_object(obj)

    bpy.ops.medge_map_editor.t3d_export(selected_objects=True)