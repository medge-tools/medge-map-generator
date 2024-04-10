from bpy.types import Object
from mathutils import Vector, Matrix

import copy
import numpy as np
from sys            import float_info
from collections    import UserList
from math           import radians

from ..b3d_utils        import rotation_matrix
from ..dataset.dataset  import Dataset, DatabaseEntry, Attribute, get_dataset, create_polyline
from .bounds            import AABB, Capsule, Hit

# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, 
                 state, 
                 points: list[Vector], 
                 radius = 1):
        super().__init__(copy.deepcopy(points))

        self.state = state
        self._radius = radius
        self.capsules = []
        
        self.to_origin()
        self.init_capsules()
        self.update_aabb()


    @property
    def radius(self):
        return self._radius
    

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.update_capsules()


    def to_origin(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset

    
    def init_capsules(self):
        self.capsules = []

        for p1, p2 in zip(self.data, self.data[1:]):
            cap = Capsule(p1, p2, self._radius)
            self.capsules.append(cap)


    def update_capsules(self):
        for cap in self.capsules:
            cap.radius = self._radius


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

        self.aabb = AABB(bmin, bmax)


    def align(self, _other: list[Vector], _align_direction = False, _rotation_offset = 0):
        # To origin for the rotations to be applied properly
        self.to_origin()

        # Direction vectors 
        my_dir = Vector((0, 1, 0))
        if len(self.data) >= 2:
            my_dir = self.data[1] - self.data[0]

        other_dir = Vector((0, 1, 0))
        if len(_other) >= 2:
            other_dir = _other[-1] - _other[-2]
            if other_dir.length <= 0.0001:
                other_dir = _other[-1] - _other[-3]

        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')

        # Get rotation matrix around z-axis from direction vectors
        if _align_direction:
            a = my_dir * Vector((1, 1, 0))
            b = other_dir * Vector((1, 1, 0))
            A = rotation_matrix(a, b)
            R = R @ A

        for p in self.data:
            p.rotate(R)

        # Move chain to the end of the other chain
        offset  = copy.deepcopy(_other[-1])
        offset += other_dir

        for p in self.data:
            p += offset

        # Update bounds
        self.update_aabb()


    def collides(self, other: 'Chain') -> Hit | None:
        if not self.aabb.contains(other.aabb): return False
        for my_cap in self.capsules:
            for other_cap in other.capsules:
                if (hit := my_cap.collides(other_cap)): return hit
        return None
            
    
    def rotate(self, degree: float):
        pass

# -----------------------------------------------------------------------------
class ChainPool(UserList):
    def append(self, state, sequence: list[Vector]):
        self.data.append(Chain(state, sequence))
                    

    def random_chain(self) -> Chain:
        n = len(self.data)
        k = np.random.choice(n)
        return copy.deepcopy(self.data[k])
 

# -----------------------------------------------------------------------------
class GeneratedChain(UserList):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.obj = None


    def append(self, chain: Chain):
        self.data.extend(chain)
        self.sections.append(chain)


    def pop(self):
        k = len(self.data)

        chain = self.sections.pop()

        if not chain: return

        n = len(chain)
        l = k - n
        del self.data[l:]

        return chain


    def from_dataset(self, dataset_object: Object):
        if not (dataset := get_dataset(dataset_object)): return

        self.obj = dataset_object

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


    def to_dataset(self) -> Dataset:
        dataset = Dataset()

        for chain in self.sections:
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
    

    def to_polyline(self, name: str) -> Object:
        self.obj = create_polyline(self.to_dataset(), name)
        return self.obj