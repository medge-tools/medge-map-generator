import bpy
from bpy.types import Object, Collection, Spline
from mathutils import Vector, Matrix

import itertools
import numpy     as     np
from math        import radians, pi
from copy        import deepcopy
from dataclasses import dataclass
from collections import UserList

from ..                 import b3d_utils
from ..b3d_utils        import rotation_matrix
from ..dataset.movement import State
from .props             import MET_PG_ModuleGroup, get_population_prop, get_module_prop
from .bounds            import AABB, Capsule, Hit


# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
@dataclass
class MapGenSettings:
    seed               = 0
    collision_height   = 1.92
    collision_radius   = .5
    max_angle          = 180
    angle_step         = 45
    align_orientation  = True
    random_angles      = False
    resolve_collisions = True
    max_depth          = 3
    debug_capsules     = False
    

    def __str__(self):
        return f"\
{self.seed}_\
{self.collision_height}_\
{self.collision_radius}_\
{self.max_angle}_\
{self.angle_step}_\
{str(self.align_orientation)[0]}_\
{str(self.random_angles)[0]}_\
{str(self.resolve_collisions)[0]}_\
{self.max_depth}_\
{str(self.debug_capsules)[0]}\
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

        assert(len(self.points) >= 2)

        self.capsules:list[Capsule] = None
        self.aabb:AABB=AABB()
        
        self.update()

    @property
    def path(self) -> Spline:
        return self.curve.data.splines[0]
    
    @property
    def points(self) -> Spline:
        return self.path.points

    def __len__(self):
        return len(self.path.points)

    def __getitem__(self, _key:int):
        return self.path.points[_key].co


    def resize(self, _scale:float):
        self.curve.scale = _scale, _scale, _scale
        self.update()


    def update(self):
        # Order is important!!!
        self.update_capsules()
        self.update_aabb()

    
    def update_capsules(self):
        self.capsules = []
        
        prop = get_module_prop(self.curve)
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        capsule = prop.capsule.evaluated_get(depsgraph)

        vertices = capsule.data.vertices

        for k in range(0, len(vertices), 4):
            # See props.py > MET_SCENE_PG_ModuleGroupList > init_capsule_data 
            v1 = vertices[k]
            v2 = vertices[k + 1]
            #v3 = vertices[k + 2]
            v4 = vertices[k + 3]

            cap = Capsule(v1, (v4 - v1).length, (v2 - v1).length)
            self.capsules.append(cap)


    def update_aabb(self):
        fmin = float('-inf')
        fmax = float('inf')
        bmin = Vector((fmax, fmax, fmax))
        bmax = Vector((fmin, fmin, fmin))
        
        for p in self.points:
            bmin.x = min(bmin.x, p.co.x)
            bmin.y = min(bmin.y, p.co.y)
            bmin.z = min(bmin.z, p.co.z)

            bmax.x = max(bmax.x, p.co.x)
            bmax.y = max(bmax.y, p.co.y)
            bmax.z = max(bmax.z, p.co.z) 

        for c in self.capsules:
            points = [
                c.base - Vector((c._radius_, 0, 0)),
                c.base - Vector((0, c._radius_, 0)),
                c.base + Vector((c._radius_, 0, 0)),
                c.base + Vector((0, c._radius_, 0)),
            ]

            for p in points:
                bmin.x = min(bmin.x, p.x)
                bmin.y = min(bmin.y, p.y)

                bmax.x = max(bmax.x, p.x)
                bmax.y = max(bmax.y, p.y)

        bmax.z += self.height

        self.aabb.bmin = bmin
        self.aabb.bmax = bmax


    def align(self, _gen_map:'GeneratedMap|list[CurveModule]', _align_direction=False, _rotation_offset=0):
        my_dir = self.points[1].co - self.points[0].co

        cm:'CurveModule' = _gen_map[-1]
        other_dir = cm.points[-1].co - cm.points[-2].co

        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')

        if _align_direction:
            # Get rotation matrix around z-axis from direction vectors
            a = my_dir    * Vector((1, 1, 0))
            b = other_dir * Vector((1, 1, 0))

            A = rotation_matrix(a, b)
            R = R @ A

        W = self.curve.matrix_world
        self.curve.matrix_world = W @ R

        # Move chain to the end of the other chain
        end  = deepcopy(_gen_map[-1][-1])
        end += other_dir

        self.curve.location = end
        bpy.context.view_layer.update()

        # Update capsules and AABB
        self.update()

    
    def collides(self, _other:'CurveModule', _quick=False) -> list[Hit]:
        if not self.aabb.contains(_other.aabb): return None
        
        hits = []
        
        for j, my_cap in enumerate(self.capsules):
            # The first capsule seems to always overlap with the last capsule of the previous chain
            if j == 0: continue
        
            for other_cap in reversed(_other.capsules):
                if (hit := my_cap.collides(other_cap)): 
                    hits.append(hit)
        
                    if _quick: return hits
        
        return hits

# -----------------------------------------------------------------------------
# Generated Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class GeneratedMap(UserList):
    def __init__(self, _data=None, _settings:MapGenSettings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings:MapGenSettings = _settings

        self.angles = [0]

        for k in range(_settings.angle_step, _settings.max_angle + 1, _settings.angle_step):
            if k != 180:
                self.angles.append(-k)
            self.angles.append(k)


    def resolve_collisions(self, _print_iteration:int, _print_state:str):
        smallest_pen_depth = float('inf')

        best_angle_perm = None
        max_depth = 0

        # Resolve any collisions by testing angle product permutations
        start = len(self.data) - 1
        max_depth = max(len(self.data) - self.settings.max_depth - 1, 0)
        
        if self.settings.random_angles:
            np.random.shuffle(self.angles)

        found_zero_collisions = False

        for k in range(start, max_depth, -1):
            r = len(self.data) - k

            # Try different angle permutations to solve collisions
            for angle_perm in itertools.product(self.angles, repeat=r):
                total_pen_depth = self.try_configuration(k, angle_perm)

                print(f'Iteration: {_print_iteration}, State: {_print_state}, Max depth: {max_depth}, Current depth: {k}, Tested angle perm: {angle_perm}), total penetration: {total_pen_depth}')
                
                if total_pen_depth < smallest_pen_depth: 
                    smallest_pen_depth = total_pen_depth
                    best_angle_perm    = angle_perm

                found_zero_collisions = total_pen_depth == 0
                
            if found_zero_collisions:
                print(f'0 Collisions with angle perm: {angle_perm}')
                break
            
        # Apply the best configuration
        print(f'Best angle perm: {best_angle_perm}, with total depth: {smallest_pen_depth}')
        self.apply_configuration(self.data, k, best_angle_perm)
        

    def check_collisions(self, _data:list[CurveModule]) -> float:
        total_depth = 0
        
        for j in range(len(_data) - 1, -1, -1):
            for k in range(len(_data)):
                if j == k: break

                ch1 = _data[j]
                ch2 = _data[k]

                if (hits := ch1.collides(ch2)):
                    for h in hits:
                        total_depth += h.depth

        return total_depth 


    def try_configuration(self, _start_idx:int, _angle_permutation:int) -> float:
        temp:list[CurveModule] = deepcopy(self.data)
        self.apply_configuration(temp, _start_idx, _angle_permutation)

        return self.check_collisions(temp)
    

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
def generate(_chain:str, _seperator:str, _module_group:list[MET_PG_ModuleGroup], _dataset_name:str, _settings:MapGenSettings):
    main_collection = b3d_utils.new_collection(f'POPULATED_{_dataset_name} : {_settings}' )
    b3d_utils.new_collection('PrepareForExport', main_collection)

    states = _chain.split(_seperator)

    generated_map = GeneratedMap(None, _settings)

    print()
    print('Duplicating and aligning modules...')
    for k, str_state in enumerate(states):
        state = int(str_state)

        if k == 10:
            break

        # Get module
        module = _module_group[state].random_object()

        if not module: continue

        # Duplicate module
        curve = b3d_utils.duplicate_object_with_children(module, False, main_collection)
        curve.name = f'{k}_{str_state}_{curve.name}'

        cm = CurveModule(curve, state)
        cm.align(generated_map, _settings.align_orientation)

        generated_map.append(cm)

        #generated_map.resolve_collisions(k, State(state).name)
        
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