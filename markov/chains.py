from bpy.types import Object
from mathutils import Vector, Matrix

import copy
import numpy as np
from sys            import float_info
from collections    import UserList
from math           import radians
from dataclasses    import dataclass

from ..b3d_utils        import rotation_matrix
from ..dataset.dataset  import Dataset, DatabaseEntry, Attribute, get_dataset, create_polyline
from .bounds            import AABB, Capsule, Hit

# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, 
                 _state:int, 
                 _points:list[Vector], 
                 _radius:int = 1,
                 _to_origin = True):
        super().__init__(copy.deepcopy(_points))

        self.state = _state
        self._radius_ = _radius
        self.capsules:list[Capsule] = None
        self.aabb:AABB=AABB()
        
        if _to_origin:
            self.to_origin()
        self.update_capsules()
        self.update_aabb()


    @property
    def radius(self):
        return self._radius_
    

    @radius.setter
    def radius(self, value:float):
        self._radius_ = value
        for cap in self.capsules:
            cap.radius = self.radius


    def to_origin(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset

    
    def update_capsules(self):
        self.capsules = []

        if len(self.data) == 1:
            p = self.data[0]
            cap = Capsule(p, p, self.radius)
            self.capsules.append(cap)
            return
        
        for p1, p2 in zip(self.data, self.data[1:]):
            cap = Capsule(p1, p2, self.radius)
            self.capsules.append(cap)


    def update_aabb(self):
        fmax = float_info.max
        fmin = -fmax
        bmin = Vector((fmax, fmax, fmax))
        bmax = Vector((fmin, fmin, fmin))
        
        for p in self.data:
            if p.x < bmin.x: bmin.x = p.x
            if p.y < bmin.y: bmin.y = p.y
            if p.z < bmin.z: bmin.z = p.z

            if p.x > bmax.x: bmax.x = p.x
            if p.y > bmax.y: bmax.y = p.y
            if p.z > bmax.z: bmax.z = p.z

        self.aabb.bmin = bmin
        self.aabb.bmax = bmax


    def align(self, _gen_chain:'GeneratedChain', _rotation_offset=0, _align_direction=False):
        # To origin for the rotations to be applied properly
        self.to_origin()

        my_dir, other_dir = self.get_directions(_gen_chain)

        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')
        
        if _align_direction:
            # Get rotation matrix around z-axis from direction vectors
            a = my_dir * Vector((1, 1, 0))
            b = other_dir * Vector((1, 1, 0))
            A = rotation_matrix(a, b)
            R = R @ A

        for p in self.data:
            p.rotate(R)

        # Move chain to the end of the other chain
        offset  = copy.deepcopy(_gen_chain[-1][-1])
        offset += other_dir

        for p in self.data:
            p += offset

        # Update bounds
        self.update_aabb()

    
    def get_directions(self, _gen_chain:'GeneratedChain') -> tuple[Vector, Vector]:
        # Direction vectors 
        my_dir = Vector((0, 1, 0))
        if len(self.data) >= 2:
            my_dir = self.data[1] - self.data[0]

        # Get the last two points from the generated chain
        other_dir = Vector((0, 1, 0))

        c1:Chain = _gen_chain[-1]
        p1 = c1[-1]
        
        if len(c1) >= 2:
            p2 = c1[-2]
            other_dir = p1 - p2
        else:            
            if len(_gen_chain) >= 2:
                c2 = _gen_chain[-2]
                p2 = c2[-1]
                other_dir = p1 - p2
        
        return my_dir, other_dir


    def collides(self, _other:'Chain', _force=False) -> Hit | None:
        if not _force and not self.aabb.contains(_other.aabb): return None
        for my_cap in self.capsules:
            for other_cap in _other.capsules:
                if (hit := my_cap.collides(other_cap)): return hit
        return None
            
    
# -----------------------------------------------------------------------------
class ChainPool(UserList):
    def append(self, state, sequence:list[Vector]):
        self.data.append(Chain(state, sequence))
                    

    def random_chain(self) -> Chain:
        n = len(self.data)
        k = np.random.choice(n)
        return copy.deepcopy(self.data[k])
 

# -----------------------------------------------------------------------------
@dataclass
class GenChainSettings:
    length:int                 = 1
    seed:int                   = 0
    aabb_margin:float          = 0
    collision_radius:float     = 1
    angle_step:float           = 1
    max_resolve_iterations:int = 10
    align_orientation:bool     = False


# -----------------------------------------------------------------------------
class GeneratedChain(UserList):
    def __init__(self, _settings=None, _data=None):
        super().__init__(_data)
        self.obj:Object = None
        self.settings:GenChainSettings = _settings


    def from_dataset(self, _dataset_object:Object):
        if not (dataset := get_dataset(_dataset_object)): return

        self.obj = _dataset_object

        curr_points = None
        curr_state = None

        for entry in dataset:
            if entry[Attribute.CHAIN_START.value]:
                if curr_points:
                    self.append(Chain(curr_state, curr_points))

                curr_points = []
                curr_state = entry[Attribute.PLAYER_STATE.value]

            point = entry[Attribute.LOCATION.value]
            curr_points.append(point)


    def resolve_collision(self):
        # We only resolve the collision of the last appended chain
        if not (hit := self.check_collision(-1)): return

        

        
    def rotate_chain(self, _chain_idx:Chain):
        # Store the penetration depth with the respective rotation
        smallest_pen_depth = float_info.max
        best_rotation = 0


    def try_rotation(self, _chain_idx:int, _rotation:float):
        chain: Chain = copy.deepcopy(self.data[_chain_idx])
        chain.align(self.data[_chain_idx-1], _rotation, self.settings.align_orientation)


    def check_collision(self, _chain_idx:int) -> Hit | bool:
        chain = self.data[_chain_idx]
        for k, sec in reversed(list(enumerate(self.data))):
            if k == _chain_idx: continue
            if (hit := chain.collides(sec)): return hit
        return False


    def to_dataset(self) -> Dataset:
        dataset = Dataset()

        for chain in self.data:
            bmin = chain.aabb.bmin
            bmax = chain.aabb.bmax

            for k, point in enumerate(chain):
                entry = DatabaseEntry()
                entry[Attribute.PLAYER_STATE.value] = chain.state
                entry[Attribute.LOCATION.value] = point
                entry[Attribute.AABB_MIN.value] = bmin
                entry[Attribute.AABB_MAX.value] = bmax

                if k == 0:
                    entry[Attribute.LENGTH.value] = len(chain)
                    entry[Attribute.CHAIN_START.value] = True
                else:
                    entry[Attribute.LENGTH.value] = k

                dataset.append(entry)
                
        return dataset
    

    def to_polyline(self, _name:str) -> Object:
        self.obj = create_polyline(self.to_dataset(), _name)
        return self.obj