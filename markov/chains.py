from bpy.types import Object
from mathutils import Vector, Matrix

import itertools, random
import numpy     as np
from copy        import deepcopy
from sys         import float_info
from collections import UserList
from math        import radians
from dataclasses import dataclass

from ..b3d_utils       import rotation_matrix
from ..dataset.dataset import Dataset, DatabaseEntry, Attribute, dataset_entries, create_polyline
from .bounds           import AABB, Capsule, Hit


# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, 
                 _state:int, 
                 _points:list[Vector], 
                 _height:float = 1.92,
                 _radius:int = 1,
                 _to_origin:bool = True):
        super().__init__(deepcopy(_points))

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
        offset = deepcopy(points[0])
        
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
        
        def add_capsule(point:Vector):
            nonlocal height
            cap = Capsule(point, point + height, self.radius)
            self.capsules.append(cap)

        if len(self.data) == 1:
            p = self.data[0]
            cap = Capsule(p, p + height, self.radius)
            self.capsules.append(cap)
            return

        p1 = self.data[0]
        idx = 1
        p2 = self.data[idx]

        dir = p2 - p1
        length = dir.length
        dir.normalize()
    
        diameter = self.radius * 2

        # Fit capsules along the chain
        while True:

            # Place capsules on current edge while they do not overextend
            while diameter <= length:
                offset = dir * self.radius
                P = p1 + offset

                add_capsule(P)

                length -= diameter
                p1 = P + offset

            # If we are at the last edge, place a capsule that doesn't overextend
            if idx == len(self.data) - 1:
                dir = p1 - p2

                offset = dir.normalized() * self.radius
                P = p2 + offset

                add_capsule(P)
                return
            
            # Check if we can fit a capsule that will overlap with the next edge
            if self.radius <= length:
                offset = dir * self.radius
                P = p1 + offset
                add_capsule(P)

            # Find starting point on next edge
            rest = length

            p1 = p2
            idx += 1
            p2 = self.data[idx]

            dir = p2 - p1
            length = dir.length
            dir.normalize()

            s = self.radius - rest
            offset = dir * s
            P = p1 + offset

            add_capsule(P)

            length -= s
            p1 = P + dir * self.radius


    def update_aabb(self):
        fmax = float('inf')
        fmin = float('-inf')
        bmin = Vector((fmax, fmax, fmax))
        bmax = Vector((fmin, fmin, fmin))
        
        for p in self.data:
            bmin.x = min(bmin.x, p.x)
            bmin.y = min(bmin.y, p.y)
            bmin.z = min(bmin.z, p.z)

            bmax.x = max(bmax.x, p.x)
            bmax.y = max(bmax.y, p.y)
            bmax.z = max(bmax.z, p.z) 

        bmax.z += self.height

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
        offset  = deepcopy(_gen_chain[-1][-1])
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

        offset = deepcopy(self.data[0])
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
        return deepcopy(self.data[k])
 

# -----------------------------------------------------------------------------
@dataclass
class GenChainSettings:
    length:int             = 1
    seed:int               = 0
    collision_height:float = 1.92
    collision_radius:float = 1
    angle_range:int        = 180
    angle_step:int         = 10
    align_orientation:bool = True
    random_angle:bool      = False

    def __str__(self):
        return f'\
{self.length}_\
{self.seed}_\
{self.collision_height}_\
{self.collision_radius}_\
{self.angle_range}_\
{self.angle_step}_\
{str(self.align_orientation)[0]}_\
{str(self.random_angle)[0]}'


# -----------------------------------------------------------------------------
class GeneratedChain(UserList):
    def __init__(self, _data=None, _settings:GenChainSettings=None):
        super().__init__(_data)
        self.obj:Object = None
        self.settings:GenChainSettings = _settings

        self.angles = []

        for a in range(0, _settings.angle_range + 1, _settings.angle_step):
            self.angles.append(a)
            self.angles.append(-a)


    def resolve_collisions(self):
        smallest_depth = float_info.max
        best_mirror_perm = None
        best_rotation_offset = []

        def test_configuration(_start_idx:int, _mirror_permutation:str) -> bool:
            nonlocal smallest_depth
            nonlocal best_mirror_perm
            nonlocal best_rotation_offset
            
            if self.settings.random_angle:
                random.shuffle(self.angles)

            for angle in self.angles:
                total_depth = self.try_configuration(_start_idx, _mirror_permutation, angle)
                
                if total_depth > 0:
                    depth = len(self.data) - _start_idx
                    print(f'Chain depth: {depth}, Tested configuration: (permutation: {_mirror_permutation}, angle: {angle}), with total penetration: {total_depth}')

                    if total_depth < smallest_depth: 
                        smallest_depth = total_depth
                        best_mirror_perm = _mirror_permutation
                        best_rotation_offset = angle

                else:            
                    print(f'0 Collisions with permutation: {_mirror_permutation}')
                    self.apply_configuration(self.data, k, _mirror_permutation, angle)

                    return True
                
            return False

        # Max depth
        max_depth = len(self.data)

        found_collision = False

        for k, ch1 in reversed(list(enumerate(self.data))):
            for j, ch2 in enumerate(self.data):
                if k == j: break
                if not ch1.collides(ch2, _quick=True): continue

                found_collision = True

                if j < max_depth:
                    max_depth = j

        if not found_collision: return
        
        print(f'Max depth: {max_depth}')

        # Resolve any collisions by testing permutations
        # A permutation is a string consisting of '0' and '1'
        # '1' means mirror, '0' means do nothing
        for k in range(len(self.data) - 1, max_depth - 1, -1):
            r = len(self.data) - k

            mirror_perms = [''.join(seq) for seq in itertools.product('01', repeat=r) if r == 1 or seq[0] != '0']

            for mp in mirror_perms:
                if test_configuration(k, mp): return
        
        # We have not found a configuration with 0 collisions, so apply the best configuration
        print(f'Best configuration: (permutation: {best_mirror_perm}, angle: {best_rotation_offset}), with total depth: {smallest_depth}')
        start_idx = len(self.data) - len(best_mirror_perm)
        self.apply_configuration(self.data, start_idx, best_mirror_perm, best_rotation_offset)
        

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


    def try_configuration(self, _start_idx:int, _mirror_permutation:str, _rotation_offset:int) -> float:
        temp:list[Chain] = deepcopy(self.data)
        self.apply_configuration(temp, _start_idx, _mirror_permutation, _rotation_offset)
        return self.check_collisions(temp)
    

    def apply_configuration(self, _data:list[Chain], _start_idx:int, _mirror_permutation:str, _rotation_offset:int):
        # Mirror data 
        p = 0
        end = min(_start_idx + len(_mirror_permutation), len(_data))
        for k in range(_start_idx, end, 1):
            if _mirror_permutation[p] == '1':
                _data[k].mirror_xy()
            p += 1

        # Align mirrored data
        for k in range(_start_idx + 1, len(_data)):
            _data[k].align(_data[:k], self.settings.align_orientation, _rotation_offset)


    def from_dataset(self, _dataset_object:Object):
        self.obj = _dataset_object

        curr_points = None
        curr_state = None

        for entry in dataset_entries(_dataset_object):
            if entry[Attribute.CHAIN_START.value]:
                if curr_points:
                    self.append(Chain(curr_state, curr_points))

                curr_points = []
                curr_state = entry[Attribute.STATE.value]

            point = entry[Attribute.LOCATION.value]
            curr_points.append(point)


    def to_dataset(self) -> Dataset:
        dataset = Dataset()

        for chain in self.data:
            bmin = chain.aabb.bmin
            bmax = chain.aabb.bmax

            for k, point in enumerate(chain):
                entry = DatabaseEntry()
                entry[Attribute.STATE.value] = chain.state
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