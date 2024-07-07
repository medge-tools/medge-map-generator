import bpy
from bpy.types import Object, Collection, Spline, Operator
from mathutils import Vector, Matrix

import numpy      as     np
from itertools    import product
from math         import radians, pi
from collections  import UserList

from ..                 import b3d_utils
from ..b3d_utils        import rotation_matrix, update_matrices, duplicate_object_with_children, remove_object_with_children, check_objects_intersection, print_console
from ..dataset.movement import State
from .props             import MET_PG_curve_module_collection, MET_PG_generated_chain, get_curve_module_prop, MET_SCENE_PG_map_gen_settings


# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class CurveModule:
    def __init__(self, 
                 _state:int,
                 _module_names:list[str]):
        
        self.state = _state
        self.module_names = _module_names.copy()
        np.random.shuffle(self.module_names)

        self.curve:Object = None
        self.current_name_index = 0
        self.index = 0
        self.collection = None


    @property
    def path(self) -> Spline:
        return self.curve.data.splines[0]
    
    @property
    def points(self) -> Spline:
        return self.path.points
    
    @property
    def volume(self) -> Object | None:
        return get_curve_module_prop(self.curve).collision_volume

    def __getitem__(self, _key:int):
        return self.path.points[_key].co


    def prepare(self, _index:int, _collection:Collection):
        self.index = _index
        self.collection = _collection


    def next_module(self, _index=-1):
        if self.curve:
            remove_object_with_children(self.curve)

        if _index >= 0 or _index < len(self.module_names):
            idx = _index
        else:
            idx = self.current_name_index
            self.current_name_index += 1
            self.current_name_index %= len(self.module_names)
        
        name = self.module_names[idx]
        module = bpy.data.objects[name]
        
        self.curve = duplicate_object_with_children(module, False, self.collection, False)
        self.curve.name = f'{self.index}_{module.name}'


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

        return check_objects_intersection(vol1, vol2)
        

# -----------------------------------------------------------------------------
# Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class Map(UserList):
    """` list[CurveModule] `"""

    def __init__(self, _data=None, _settings:MET_SCENE_PG_map_gen_settings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings = _settings

        # Only contains indices that point to candidates to resolve intersection
        self.resolve_candidates:list[int] = []
        # If the CurveModule is a resolve candidate, store the index to resolve_candidates, otherwise it is 0
        self.cm_flag:list[int] = []


    def append(self, _item:CurveModule):
        super().append(_item)
        
        if (_item.state == State.Walking or 
            _item.state == State.WallRunningLeft or 
            _item.state == State.WallRunningRight):
            self.resolve_candidates.append(len(self.data) - 1)
            self.cm_flag.append(len(self.resolve_candidates) - 1)

        else:
            self.cm_flag.append(0)


    def build(self, _collection:Collection):
        cm:CurveModule
        # Prepare modules
        for k, cm in enumerate(self.data):
            cm.prepare(k, _collection)

        # Build modules
        for k, cm in enumerate(self.data):
            print(f'Iteration: {k}')
            cm.next_module()

            # Align
            self.align_module(k)

            # Check intersections
            if self.check_intersection(k, k - 1) == 0: 
                continue

            # Resolve intersections
            if not self.settings.resolve_intersection: 
                continue
            
            print(f'Resolving intersection...')
            self.resolve_intersections(k)


    def check_intersection(self, _index:int, _start:int) -> int:
        cm1 = self.data[_index]
            
        for k in range(_start - 1, -1, -1):
            if _index == k: continue

            cm2 = self.data[k]

            if (hits := cm1.intersect(cm2)):
                total_intersections += len(hits)


    def check_intersections_range(self, _start:int) -> int:
        if _start == 0: return 0

        total_intersections = 0
        
        for j in range(_start, -1, -1):
            self.check_intersection(j, _start)

        return total_intersections


    def resolve_intersections(self, _start:int) -> int:
        module_names_indices:list[list[int]] = []
        current_candidates:list[int] = []

        # Find resolve candidate
        start_candidate:int
        for k in range(_start, -1, -1):
            if (start_candidate := self.cm_flag[k]) != 0:
                break

        intersections_resolved = False

        for k in range(start_candidate, -1, -1):
            i = self.resolve_candidates[k]
            cm:CurveModule = self.data[i]

            module_names_indices.append(range(len(cm.module_names)))
            current_candidates.append(i)
        
            for permutation in product(*module_names_indices):
                self.apply_configuration(current_candidates, permutation)

                if self.check_intersections_range(_start) == 0:
                    intersections_resolved = True
                    break
        
            if intersections_resolved:
                break


    def apply_configuration(self, _indices:list[int], _permutation:tuple[int, ...]) -> int:
        print(f'Tested permutation: {_permutation}')
        lowest_idx = len(self.data) - 1

        # Apply permutation
        for i, p in zip(_indices, _permutation):
            cm:CurveModule = self.data[i]
            cm.next_module(p)

            if i < lowest_idx: 
                lowest_idx = i

        # Align modules
        for k in range(lowest_idx, len(self.data), 1):
            self.align_module(k)


    def align_module(self, _index:int):
        cm:CurveModule = self.data[_index]
        if not cm.curve: return

        if _index == 0:
            cm.align(None)
        else:
            cm.align(self.data[_index - 1], self.settings.align_orientation)


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

    # Generation data
    np.random.seed(_settings.seed)

    states = _gen_chain.split()

    map = Map(None, _settings)

    # Instantiate all CurveModules
    for k, str_state in enumerate(states):
        state = int(str_state)

        # Handle specific cases:
        # Handle state compared to the next state
        if (n := k + 1) < len(states):
            next_state = int(states[n])

            # Case 1: Jump -> WallClimbing
            # To go into WallCLimbing the jump distance should be so short we can just ignore it
            if state == State.Jump:
                if next_state == State.WallClimbing:
                    continue

            # Case 2: WallClimbing -> WallClimb180TurnJump
            # To do a WallClimb180TurnJump the height of the wall can be longer than the player can climb
            # The WallClimb180TurnJump should have its own wall
            elif state == State.WallClimbing:
                if next_state == State.WallClimb180TurnJump:
                    continue

        # Handle state compared to the previous state
        if (p := k - 1) >= 0:
            prev_state = int(states[p])

            # Case 3: WallClimb180TurnJump -> Falling
            # There are falling modules the could end up back where the player came from
            # Falling should be included in the WallClimb180TurnJump module
            if state == State.Falling:
                if prev_state == State.WallClimb180TurnJump:
                    continue

        if not (mn := _module_group[state].collect_curve_names()): 
            continue

        cm = CurveModule(state, mn)
        map.append(cm)
        
    # Build the map
    map.build(_target_collection)

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