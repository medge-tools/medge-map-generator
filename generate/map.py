import bpy
from bpy.types import Object, Collection, Spline, Operator
from mathutils import Vector, Matrix

import itertools
import numpy     as     np
from numpy.random import randint
from math         import radians, pi
from dataclasses  import dataclass
from collections  import UserList

from ..                 import b3d_utils
from ..b3d_utils        import rotation_matrix, update_matrices, duplicate_object_with_children, remove_object_with_children
from ..dataset.movement import State
from .props             import MET_PG_curve_module_collection, MET_PG_generated_chain, get_curve_module_prop, MET_SCENE_PG_map_gen_settings


# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class CurveModule:
    def __init__(self, 
                 _curve:Object, 
                 _state:int):

        assert(_curve.type == 'CURVE')

        _curve.data.twist_mode = 'Z_UP'
        
        self.curve = _curve
        self.state = _state

    @property
    def path(self) -> Spline:
        return self.curve.data.splines[0]
    
    @property
    def points(self) -> Spline:
        return self.path.points
    
    @property
    def volume(self) -> Object | None:
        return get_curve_module_prop(self.curve).collision_volume

    def __len__(self):
        return len(self.path.points)

    def __getitem__(self, _key:int):
        return self.path.points[_key].co


    def resize(self, _scale:float):
        self.curve.scale = _scale, _scale, _scale


    def align(self, other:'CurveModule', _align_direction=False, _rotation_offset=0):
        if not other:
            self.curve.location.xyz = 0, 0, 0
            update_matrices(self.curve)
            return

        # My direction
        my_mw = self.curve.matrix_world.copy()
        my_dir = my_mw @ self.points[1].co - (start := my_mw @ self.points[0].co)
        my_dir.normalize()

        # Other direction
        other_wm = other.curve.matrix_world.copy()
        other_dir = (end := other_wm @ other.points[-1].co) - other_wm @ other.points[-2].co
        other_dir.normalize()
        
        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')

        if _align_direction:
            # Get rotation matrix around z-axis from direction vectors
            a = my_dir.xyz    * Vector((1, 1, 0))
            b = other_dir.xyz * Vector((1, 1, 0))

            if a.length == 0 or b.length == 0:
                raise Exception(f'Direction vector has 0 length. Perhaps overlapping control points for curve: {self.curve.name}')

            A = rotation_matrix(a, b)
            R = R @ A

        self.curve.matrix_world = my_mw @ R.to_4x4()

        # Move chain to the end of the other chain
        self.curve.location = end.xyz
        update_matrices(self.curve)

    
    def intersect(self, _other:'CurveModule') -> list[tuple[int, int]] | None:
        if not (vol1 := self.volume) or not (vol2 := _other.volume):
            return None

        return b3d_utils.check_objects_intersection(vol1, vol2)
        

# -----------------------------------------------------------------------------
# Generated Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class GeneratedMap(UserList):
    """` list[CurveModule] `"""

    def __init__(self, _data=None, _settings:MET_SCENE_PG_map_gen_settings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings = _settings

        self.angles = [0]

        for k in range(_settings.angle_step, _settings.max_angle + 1, _settings.angle_step):
            if k != 180:
                self.angles.append(-k)
            self.angles.append(k)


    def resolve_intersection(self, _curr_state:str) -> int:
        if len(self.data) <= 1: return

        lowest_amount_hits = float('inf')

        best_angle_perm = None
        max_depth = 0

        # Resolve any collisions by testing angle product permutations
        start = len(self.data) - 1
        max_depth = max(len(self.data) - self.settings.max_depth - 1, 0)
        
        if self.settings.random_angles:
            np.random.shuffle(self.angles)

        found_zero_collisions = False

        # Store original angles
        original_angles = []

        for cm in self.data:
            a = cm.curve.rotation_euler.z
            original_angles.append(a)

        # Resolve collisions
        for k in range(start, max_depth, -1):
            r = len(self.data) - k

            # Try different angle permutations to solve collisions
            for angle_perm in itertools.product(self.angles, repeat=r):
                self.apply_configuration(k, angle_perm)

                total_hits = self.check_intersection()

                print(f'State: {_curr_state}, Max depth: {max_depth}, Current depth: {k}, Tested angle permutation: {angle_perm}), total penetration: {total_hits}')
                
                if total_hits < lowest_amount_hits: 
                    lowest_amount_hits = total_hits
                    best_angle_perm    = angle_perm
                
                # Reset angles
                for k, cm in enumerate(self.data):
                    cm.curve.rotation_euler.z = original_angles[k]

                if (found_zero_collisions := total_hits == 0): break
                
            if found_zero_collisions:
                print(f'0 Collisions with angle permutation: {angle_perm}')
                break
            
        # Apply the best configuration
        print(f'Best angle permutation: {best_angle_perm}, with total depth: {lowest_amount_hits}')
        self.apply_configuration(k, best_angle_perm)

        return lowest_amount_hits, best_angle_perm
        

    def check_intersection(self) -> float:
        """ Checks if the last element intersects with the rest of the chain """
        overlapping_indices = 0
        
        cm1 = self.data[-1]

        for j in range(len(self.data) - 2, -1, -1):
            cm2 = self.data[j]

            if (hits := cm1.intersect(cm2)):
                overlapping_indices += len(hits)

        return overlapping_indices
    

    def apply_configuration(self, _start_idx:int, _angle_permutation:list[int]):
        # Mirror data 
        end = len(self.data)
        p = 0

        for k in range(_start_idx, end, 1):
            angle = _angle_permutation[p]
            self.data[k].align(self.data[k-1], self.settings.align_orientation, angle)

            p += 1


# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def generate(_gen_chain:MET_PG_generated_chain, 
             _module_group:list[MET_PG_curve_module_collection], 
             _settings:MET_SCENE_PG_map_gen_settings, 
             _target_collection:Collection):
    
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    b3d_utils.deselect_all_objects()

    # Collect all curve objects
    module_names:list[list[str]|None] = []

    for g in _module_group:
        module_names.append(g.collect_curve_names())

    # Generation data
    np.random.seed(_settings.seed)

    states = _gen_chain.split()

    generated_map = GeneratedMap(None, _settings)

    print()
    for k, str_state in enumerate(states):
        print(f'Iteration: {k}')

        state = int(str_state)

        # Handle specific cases:
        if (n := k + 1) < len(states):
            next_state = int(states[n])

            # Case 1: Jump -> WallClimbing
            # To go into WallCLimbing the jump distance should be so short we can just ignore it
            if state == State.Jump:
                if next_state == State.WallClimbing:
                    continue

            # Case 2: WallClimbing -> WallClimb180TurnJump
            # To do a WallClimb180TurnJump the height of the wall can be longer than the player can climb
            elif state == State.WallClimbing:
                if next_state == State.WallClimb180TurnJump:
                    continue

        if (p := k - 1) >= 0:
            prev_state = int(states[p])

            # Case 3: WallClimb180TurnJump -> Falling
            # There are falling modules the could end up back where the player came from
            # Falling should be included in the WallClimb180TurnJump module
            if state == State.Falling:
                if prev_state == State.WallClimb180TurnJump:
                    continue

        names = module_names[state]

        if not names: continue
        
        np.random.shuffle(names)

        fewest_hits = float('inf')
        fewest_hits_name = None

        for j in range(len(names)):
            # Duplicate module
            curr_name = names[j]
            module = bpy.data.objects[curr_name]
            
            curve_obj = duplicate_object_with_children(module, False, _target_collection, False)
            curve_obj.name = f'{k}_{module.name}'

            # Align it
            cm = CurveModule(curve_obj, state)

            if len(generated_map) == 0:
                cm.align(None, _settings.align_orientation)
            else:
                cm.align(generated_map[-1], _settings.align_orientation)

            generated_map.append(cm)

            if (hits := generated_map.check_intersection()) == 0:
                fewest_hits = hits
                break
            
            if hits < fewest_hits:
                fewest_hits_name = curr_name

            # Remove it
            generated_map.pop()
            remove_object_with_children(curve_obj)

        if fewest_hits == 0: continue

        # Resolve intersection if we did not found a module with 0 intersections
        # TODO: resolve intersections by also trying different modules
        if not _settings.resolve_intersection: continue
        
        # Duplicate module with the fewest intersections
        module = bpy.data.objects[fewest_hits_name]
        
        curve_obj = duplicate_object_with_children(module, False, _target_collection, False)
        curve_obj.name = f'{k}_{module.name}'
        
        # Align it
        cm = CurveModule(curve_obj, state)
        cm.align(generated_map[-1], _settings.align_orientation)

        generated_map.append(cm)

        #Resolve intersections
        generated_map.resolve_intersection(State(state).name)
        
    print('Finished!')


# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def prepare_for_export(_settings:MET_SCENE_PG_map_gen_settings, _collection:Collection):
    new_collection = b3d_utils.new_collection('PrepareForExport', _collection)

    # Add player start
    bpy.ops.medge_map_editor.add_actor(type='PLAYER_START')
    ps = bpy.context.object

    b3d_utils.link_object_to_scene(ps, new_collection)
    
    ps.location = Vector((0, 0, 0))

    # Add directional light
    bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 3), scale=(1, 1, 1))
    light = bpy.context.object

    b3d_utils.link_object_to_scene(light, new_collection)

    # Add killvolume
    scale = 500

    bpy.ops.medge_map_editor.add_actor(type='KILL_VOLUME')
    kv = bpy.context.object

    b3d_utils.link_object_to_scene(kv, new_collection)

    kv.location = 0, 0, -50
    kv.scale = scale, scale, 10

    # Add skydome top
    scale = 7000
    bpy.ops.medge_map_editor.add_skydome()
    sd = bpy.context.object

    b3d_utils.link_object_to_scene(sd, new_collection)

    sd.location = 0, 0, 0
    sd.scale = scale, scale, scale

    if _settings.skydome:
        sd.medge_actor.static_mesh.use_prefab = True
        sd.medge_actor.static_mesh.prefab = _settings.skydome

    if _settings.only_top: return

    # Add skydome bottom
    bpy.ops.medge_map_editor.add_skydome()
    sd = bpy.context.object
    b3d_utils.link_object_to_scene(sd, new_collection)

    sd.location = (0, 0, 0)
    sd.scale = (scale, scale, scale)
    sd.rotation_euler.x = pi
        
    if _settings.skydome:
        sd.medge_actor.static_mesh.use_prefab = True
        sd.medge_actor.static_mesh.prefab = _settings.skydome


# -----------------------------------------------------------------------------
def export(_collection:Collection):
    b3d_utils.deselect_all_objects()

    for obj in _collection.all_objects:
        if obj.type != 'LIGHT':
            if obj.medge_actor.type == 'NONE': continue
        
        b3d_utils.select_object(obj)

    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    b3d_utils.deselect_all_objects()
    
    bpy.ops.medge_map_editor.t3d_export('INVOKE_DEFAULT', selected_collection=True)

    bpy.ops.ed.undo()