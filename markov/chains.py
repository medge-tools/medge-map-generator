from bpy.types import Object
from mathutils import Vector, Matrix

import copy
import itertools
import numpy as np
from sys            import float_info
from collections    import UserList
from math           import radians, floor
from dataclasses    import dataclass

from ..b3d_utils       import rotation_matrix
from ..dataset.dataset import Dataset, DatabaseEntry, Attribute, get_dataset, create_polyline
from .bounds           import AABB, Capsule, Hit


# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, 
                 _state:int, 
                 _points:list[Vector], 
                 _height:float = 1.92,
                 _radius:int = 1,
                 _to_origin:bool = True):
        super().__init__(copy.deepcopy(_points))

        self.state = _state
        self._height_ = _height
        self._radius_ = _radius
        
        if _to_origin:
            self.to_origin()

        self.capsules:list[Capsule] = None
        self.aabb:AABB=AABB()
        self.update()

    # Height
    @property
    def height(self):
        return self._height_
    
    @height.setter
    def height(self, _value:float):
        self._height_ = _value
        for cap in self.capsules:
            cap.height = _value

    # Radius
    @property
    def radius(self):
        return self._radius_

    @radius.setter
    def radius(self, _value:float):
        self._radius_ = _value
        for cap in self.capsules:
            cap.radius = _value


    def to_origin(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset


    def resize(self, _scale:float):
        for p in self.data:
            p *= _scale

        self.update()


    def update(self):
        self.update_capsules()
        self.update_aabb()

    
    def update_capsules(self):
        self.capsules = []
        height = Vector( (0, 0, self.height) )
        
        for p in self.data:
            cap = Capsule(p, p + height, self.radius)
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


    def align(self, _gen_chain:list['Chain'], _align_direction=False, _rotation_offset=0):
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

        # Update 
        self.update()

    
    def get_directions(self, _gen_chain:list['Chain']) -> tuple[Vector, Vector]:
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


    def collides(self, _other:'Chain', _force=False, _quick=False) -> list[Hit]:
        if not _force and not self.aabb.contains(_other.aabb): return None
        hits = []
        for k, my_cap in enumerate(self.capsules):
            for j, other_cap in enumerate(_other.capsules):
                if (hit := my_cap.collides(other_cap)): 
                    hits.append(hit)
                    if _quick: return hits
        
        return hits
    

    def mirror_xy(self):
        """Mirrors the chains in the xy-plane along it's starting direction"""
        if len(self.data) <= 2: return

        # Project point to the line along the direction
        # https://textbooks.math.gatech.edu/ila/projections.html

        offset = copy.deepcopy(self.data[0])
        u = self.data[1] - self.data[0]

        for p in self.data:
            p -= offset
            v = (p.dot(u) / u.dot(u)) * u
            a = Vector( (v.x, v.y, p.z) )

            # Mirror data by adding the distance vector between data and projection
            d = a - p
            p += d * 2
            p += offset

        self.update()


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
    player_height:float        = 1.92
    collision_radius:float     = 1
    align_orientation:bool     = False


# -----------------------------------------------------------------------------
class GeneratedChain(UserList):
    def __init__(self, _data=None, _settings=None):
        super().__init__(_data)
        self.obj:Object = None
        self.settings:GenChainSettings = _settings


    def resolve_collisions(self):
        smallest_depth = float_info.max
        best_perm = None


        def test_permutation(_start_idx, _permutation:str):
            nonlocal smallest_depth
            nonlocal best_perm
            
            total_depth = self.try_permutation(_start_idx, _permutation)
            
            if total_depth > 0:
                print(f'Start index: {_start_idx}, Tested permutation: {_permutation}, with total depth: {total_depth}')

                if total_depth < smallest_depth: 
                    smallest_depth = total_depth
                    best_perm = _permutation

                return False
            
            print(f'0 Collisions with permutation: {_permutation}')
            self.apply_permutation(self.data, k, _permutation)

            return True


        # Max depth
        max_depth = len(self.data)

        for k, ch1 in reversed(list(enumerate(self.data))):
            for j, ch2 in enumerate(self.data):
                if k == j: break
                if not ch1.collides(ch2, _quick=True): continue
                if j < max_depth:
                    max_depth = j
        
        print(f'Max depth: {max_depth}')

        # Resolve any collisions by testing permutations
        # A permutation is a string consisting of '0' and '1'
        # '1' means mirror, '0' means do nothing
        for k in range(len(self.data) - 1, max_depth - 1, -1):
            r = len(self.data) - k

            permutations = [''.join(seq) for seq in itertools.product('01', repeat=r) if r == 1 or seq[0] != '0']

            for perm in permutations:
                if(test_permutation(k, perm)): return
        
        if best_perm:
            print(f'Best permutation: {best_perm}, with total depth: {smallest_depth}')
            start_idx = len(self.data) - len(best_perm)
            self.apply_permutation(self.data, start_idx, best_perm)
        

    def check_collisions(self, _data:list[Chain]) -> float:
        total_depth = 0
        for k in range(len(_data) - 1, -1, -1):
            for j in range(len(_data)):
                if k == j: break

                ch1 = _data[k]
                ch2 = _data[j]

                if (hits := ch1.collides(ch2)):
                    for h in hits:
                        total_depth += h.depth

        return total_depth 


    def try_permutation(self, _start_idx:int, _permutation:str) -> float:
        temp:list[Chain] = copy.deepcopy(self.data)
        self.apply_permutation(temp, _start_idx, _permutation)
        return self.check_collisions(temp)
    

    def apply_permutation(self, data:list[Chain], _start_idx:int, _permutation:str):
        # Mirror data 
        p = 0
        end = min(_start_idx + len(_permutation), len(data))
        for k in range(_start_idx, end, 1):
            if _permutation[p] == '1':
                data[k].mirror_xy()
            p += 1

        # Align mirrored data
        for k in range(_start_idx + 1, len(data)):
            data[k].align(data[:k], self.settings.align_orientation)


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