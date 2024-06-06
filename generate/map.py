import bpy
from bpy.types import Object, Collection, Spline, Operator
from mathutils import Vector, Matrix

import itertools
import numpy     as     np
from math        import radians, pi
from dataclasses import dataclass
from collections import UserList

from ..                 import b3d_utils
from ..b3d_utils        import rotation_matrix
from ..dataset.movement import State
from .props             import MET_PG_CurveModuleGroup, MET_PG_GeneratedChain, get_population_prop, get_curve_module_prop


# -----------------------------------------------------------------------------
# Map Generation Settings
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
@dataclass
class MapGenSettings:
    seed               = 0
    align_orientation  = True
    resolve_overlap    = True
    max_depth          = 3
    max_angle          = 180
    angle_step         = 45
    random_angles      = False
    

    def __str__(self):
        return f"\
{self.seed}_\
{str(self.align_orientation)[0]}_\
{str(self.resolve_overlap)[0]}_\
{self.max_depth}_\
{self.max_angle}_\
{self.angle_step}_\
{str(self.random_angles)[0]}\
"


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
        return get_curve_module_prop(self.curve).volume

    def __len__(self):
        return len(self.path.points)

    def __getitem__(self, _key:int):
        return self.path.points[_key].co


    def resize(self, _scale:float):
        self.curve.scale = _scale, _scale, _scale


    def align(self, _gen_map:'GeneratedMap|list[CurveModule]', _align_direction=False, _rotation_offset=0):
        if len(_gen_map) == 0:
            self.curve.location.xyz = Vector()
            return

        # My direction
        my_mw = self.curve.matrix_world
        my_dir = my_mw @ self.points[1].co - my_mw @ self.points[0].co

        # Other direction
        cm = _gen_map[-1]
        other_wm = cm.curve.matrix_world
        other_dir = ( end := other_wm @ cm.points[-1].co ) - other_wm @ cm.points[-2].co

        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')

        if _align_direction:
            # Get rotation matrix around z-axis from direction vectors
            a = my_dir.xyz    * Vector((1, 1, 0))
            b = other_dir.xyz * Vector((1, 1, 0))

            A = rotation_matrix(a, b)
            R = R @ A

        self.curve.matrix_world = my_mw @ R.to_4x4()

        # Move chain to the end of the other chain
        self.curve.location = end.xyz
        bpy.context.view_layer.update()

    
    def overlap(self, _other:'CurveModule') -> list[tuple[int, int]]:
        if not (vol1 := self.volume) or not (vol2 := _other.volume):
            return False

        return b3d_utils.check_objects_overlap(vol1, vol2)
        

# -----------------------------------------------------------------------------
# Generated Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class GeneratedMap(UserList):
    """` list[CurveModule] `"""

    def __init__(self, _data=None, _settings:MapGenSettings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings:MapGenSettings = _settings

        self.angles = [0]

        for k in range(_settings.angle_step, _settings.max_angle + 1, _settings.angle_step):
            if k != 180:
                self.angles.append(-k)
            self.angles.append(k)


    def resolve_overlap(self, _curr_iteration:int, _curr_state:str):
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
                self.apply_configuration(self.data, k, angle_perm)

                total_hits = self.check_overlaps(self.data)

                print(f'Iteration: {_curr_iteration}, State: {_curr_state}, Max depth: {max_depth}, Current depth: {k}, Tested angle perm: {angle_perm}), total penetration: {total_hits}')
                
                if total_hits < lowest_amount_hits: 
                    lowest_amount_hits = total_hits
                    best_angle_perm    = angle_perm
                
                # Reset angles
                for k, cm in enumerate(self.data):
                    cm.curve.rotation_euler.z = original_angles[k]

                if (found_zero_collisions := total_hits == 0): break
                
            if found_zero_collisions:
                print(f'0 Collisions with angle perm: {angle_perm}')
                break
            
        # Apply the best configuration
        print(f'Best angle perm: {best_angle_perm}, with total depth: {lowest_amount_hits}')
        self.apply_configuration(self.data, k, best_angle_perm)
        

    def check_overlaps(self, _data:list[CurveModule]) -> float:
        overlapping_indices = 0
        
        for j in range(len(_data) - 1, -1, -1):
            for k in range(len(_data)):
                if j == k: break

                cm1 = _data[j]
                cm2 = _data[k]

                if (hits := cm1.overlap(cm2)):
                    overlapping_indices += len(hits)

        return overlapping_indices 
    

    def apply_configuration(self, _data:list[CurveModule], _start_idx:int, _angle_permutation:list[int]):
        # Mirror data 
        end = len(_data)
        p = 0

        for k in range(_start_idx, end, 1):
            angle = _angle_permutation[p]
            _data[k].align(_data[:k], self.settings.align_orientation, angle)

            p += 1


# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def generate(_gen_chain:MET_PG_GeneratedChain, _module_group:list[MET_PG_CurveModuleGroup], _dataset_name:str, _settings:MapGenSettings):
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    main_collection = b3d_utils.new_collection(f'POPULATED_{_dataset_name}[{_settings}]' )
    b3d_utils.new_collection('PrepareForExport', main_collection)

    states = _gen_chain.split()

    generated_map = GeneratedMap(None, _settings)

    print()
    print('Duplicating and aligning modules...')
    for k, str_state in enumerate(states):
        state = int(str_state)

        # Get module
        module = _module_group[state].random_module()

        if not module: continue

        # Duplicate module
        curve = b3d_utils.duplicate_object_with_children(module, False, main_collection, False)
        curve.name = f'{k}_{State(state).name}_{curve.name}'

        cm = CurveModule(curve, state)

        cm.align(generated_map, _settings.align_orientation)

        generated_map.append(cm)

        if _settings.resolve_overlap:
            generated_map.resolve_overlap(k, State(state).name)
        
    # Update collection property
    get_population_prop(main_collection).has_content = True

    print('Finished')

    
# -----------------------------------------------------------------------------
def prepare_for_export(_collection:Collection):
    new_collection = b3d_utils.new_collection('PrepareForExport', _collection)

    # Add player start
    bpy.ops.medge_map_editor.add_actor(type='PLAYER_START')
    ps = bpy.context.object

    b3d_utils.link_object_to_scene(ps, new_collection)
    
    ps.location = Vector((0, 0, 2))

    # Add directional light
    bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 3), scale=(1, 1, 1))
    light = bpy.context.object

    b3d_utils.link_object_to_scene(light, new_collection)

    # Add skybox top
    bpy.ops.medge_map_editor.add_skydome()
    sd = bpy.context.object
    scale = 7000

    b3d_utils.link_object_to_scene(sd, new_collection)

    sd.location = (0, 0, 0)
    sd.scale = (scale, scale, scale)

    # Add skybox bottom
    bpy.ops.medge_map_editor.add_skydome()
    sd = bpy.context.object
    b3d_utils.link_object_to_scene(sd, new_collection)

    sd.location = (0, 0, 0)
    sd.scale = (scale, scale, scale)
    sd.rotation_euler.x = pi


# -----------------------------------------------------------------------------
def export(_collection:Collection):
    b3d_utils.deselect_all_objects()

    for obj in _collection.all_objects:
        if obj.type != 'LIGHT':
            if obj.medge_actor.type == 'NONE': continue
        
        b3d_utils.select_object(obj)

    bpy.ops.medge_map_editor.t3d_export('INVOKE_DEFAULT', selected_objects=True)