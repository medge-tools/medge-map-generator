from bpy.types import Object
from mathutils import Vector, Matrix

import itertools
import random
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
        self.total_length = 0
        
        self.capsules:list[Capsule] = None
        self.aabb:AABB=AABB()
        
        if _to_origin:
            self.to_origin()

        self.calc_total_length()
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


    def calc_total_length(self):
        self.total_length = 0

        p1 = self.data[0]

        for k in range(1, len(self.data), 1):
            p2 = self.data[k]
            self.total_length += (p2 - p1).length
            p1 = p2.copy()


    def resize(self, _scale:float):
        for p in self.data:
            p *= _scale

        self.total_length *= _scale

        self.update()


    def update(self):
        # Order is important!!!
        self.update_capsules()
        self.update_aabb()

    
    def update_capsules(self):
        self.capsules = []
        height = Vector((0, 0, self.height))
        

        def add_capsule(point:Vector):
            nonlocal height

            cap = Capsule(point, point + height, self.radius)
            self.capsules.append(cap)


        if len(self.data) == 1:
            p = self.data[0]
            add_capsule(p)
            return

        total_length_left = self.total_length

        p1 = self.data[0].copy()
        idx = 1
        p2 = self.data[idx].copy()

        dir = p2 - p1
        edge_length_left = dir.length
        dir.normalize()
    
        diameter = self.radius * 2

        # Fit capsules along the chain
        while True:

            # Place capsules on current edge while they do not overextend
            while diameter <= edge_length_left:
                offset = dir * self.radius
                P = p1 + offset

                add_capsule(P)

                edge_length_left -= diameter
                total_length_left -= diameter

                p1 = P + offset

            # If this is the last edge
            if idx == len(self.data) - 1: return
                
            # See if we can fit a capsule that will overlap with the next edge
            if diameter <= total_length_left:
                if self.radius <= edge_length_left:
                    offset = dir * self.radius
                    P = p1 + offset

                    add_capsule(P)

                    total_length_left -= self.radius

            # Find starting point on next edge
            p1 = p2
            idx += 1
            p2 = self.data[idx].copy()

            dir = p2 - p1
            edge_length_left = dir.length
            dir.normalize()


    def update_aabb(self):
        fmin = float('-inf')
        fmax = float('inf')
        bmin = Vector((fmax, fmax, fmax))
        bmax = Vector((fmin, fmin, fmin))
        
        for p in self.data:
            bmin.x = min(bmin.x, p.x)
            bmin.y = min(bmin.y, p.y)
            bmin.z = min(bmin.z, p.z)

            bmax.x = max(bmax.x, p.x)
            bmax.y = max(bmax.y, p.y)
            bmax.z = max(bmax.z, p.z) 

        for c in self.capsules:
            points = [
                c.base - Vector((c.radius, 0, 0)),
                c.base - Vector((0, c.radius, 0)),
                c.base + Vector((c.radius, 0, 0)),
                c.base + Vector((0, c.radius, 0)),
            ]

            for p in points:
                bmin.x = min(bmin.x, p.x)
                bmin.y = min(bmin.y, p.y)

                bmax.x = max(bmax.x, p.x)
                bmax.y = max(bmax.y, p.y)

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

            if a.length == 0:
                a = Vector((1, 0, 0))

            b = other_dir * Vector((1, 1, 0))
            
            if b.length == 0:
                b = Vector((1, 0, 0))

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
        my_dir = Vector((1, 0, 0))
        start = self.data[0]

        for k in range(1, len(self.data), 1):
            d = self.data[k] - start

            if d.length > 0:
                my_dir = d
                break

        # Get the last two points from the generated chain
        other_dir = Vector((1, 0, 0))

        c1:Chain = _gen_chain[-1]
        p1 = c1[-1]
        p2 = None

        if len(c1) >= 2:
            p2 = c1[-2]
            other_dir = p1 - p2

        else:            
            if len(_gen_chain) >= 2:
                c2 = _gen_chain[-2]
                p2 = c2[-1]
                other_dir = p1 - p2
        
        return my_dir, other_dir


    def collides(self, _other:'Chain', _quick=False) -> list[Hit]:
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
    

    # Project point to the line along the direction
    # https://textbooks.math.gatech.edu/ila/projections.html
    def mirror_xy(self):
        """
        Mirrors the chains in the xy-plane along it's starting direction
        """
        if len(self.data) <= 2: return

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
    def append(self, _state, _locations:list[Vector]):
        self.data.append(Chain(_state, _locations))


    def random_chain(self) -> Chain:
        n = len(self.data)
        k = np.random.choice(n)
        return deepcopy(self.data[k])
 

# -----------------------------------------------------------------------------
@dataclass
class GenChainSettings:
    length             = 1
    seed               = 0
    collision_height   = 1.92
    collision_radius   = .5
    max_depth          = 3
    max_angle          = 180
    angle_step         = 45
    align_orientation  = True
    resolve_collisions = True
    random_angles      = False
    random_mirror      = False
    debug_capsules     = False
    

    def __str__(self):
        return f'\
{self.length}_\
{self.seed}_\
{self.collision_height}_\
{self.collision_radius}_\
{self.max_depth}_\
{self.max_angle}_\
{self.angle_step}_\
{str(self.align_orientation)[0]}_\
{str(self.resolve_collisions)[0]}_\
{str(self.random_angles)[0]}_\
{str(self.debug_capsules)[0]}\
'


# -----------------------------------------------------------------------------
class GeneratedChain(UserList):
    def __init__(self, _data=None, _settings:GenChainSettings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings:GenChainSettings = _settings

        self.angles = [0]

        for k in range(_settings.angle_step, _settings.max_angle + 1, _settings.angle_step):
            if k != 180:
                self.angles.append(-k)
            self.angles.append( k)


    def resolve_collisions(self, _print_iteration:int, _print_state:str):
        smallest_pen_depth = float_info.max

        best_mirror_perm = None
        best_angle_perm = None
        max_depth = 0

        def test_configuration(_start_idx:int, _mirror_permutation:str) -> bool:
            """
            Returns true if it finds a configuration with 0 collisions
            """
            nonlocal smallest_pen_depth, best_mirror_perm, best_angle_perm
            nonlocal max_depth
            
            r = len(self.data) - _start_idx

            if self.settings.random_angles:
                np.random.shuffle(self.angles)

            for angle_permutation in itertools.product(self.angles, repeat=r):
                total_pen_depth = self.try_configuration(_start_idx, _mirror_permutation, angle_permutation)

                print(f'Iteration: {_print_iteration}, State: {_print_state}, Max depth: {max_depth}, Current depth: {_start_idx}, Tested config: (mirror perm: {_mirror_permutation}, angle perm: {angle_permutation}), total penetration: {total_pen_depth}')
                
                if total_pen_depth < smallest_pen_depth: 
                    smallest_pen_depth = total_pen_depth
                    best_mirror_perm   = _mirror_permutation
                    best_angle_perm    = angle_permutation

                if total_pen_depth == 0:
                    print(f'0 Collisions with permutation: {_mirror_permutation} and angle: {angle_permutation}')
                    return True
                
            return False


        # Resolve any collisions by testing permutations
        # A permutation is a string consisting of '0' and '1'
        # '1' means mirror, '0' means do nothing
        start = len(self.data) - 1
        max_depth = max(len(self.data) - self.settings.max_depth - 1, 0)

        for k in range(start, max_depth, -1):
            r = len(self.data) - k

            mirror_perms = [''.join(seq) for seq in itertools.product('01', repeat=r) if r == 1 or seq[0] != '0']

            for mp in mirror_perms:
                if test_configuration(k, mp):
                    start_idx = len(self.data) - len(best_mirror_perm)
                    self.apply_configuration(self.data, start_idx, best_mirror_perm, best_angle_perm)
                    
                    return

        # Apply the best configuration
        print(f'Best configuration: (mirror perm: {best_mirror_perm}, angle perm: {best_angle_perm}), with total depth: {smallest_pen_depth}')
        start_idx = len(self.data) - len(best_mirror_perm)
        self.apply_configuration(self.data, start_idx, best_mirror_perm, best_angle_perm)
        

    def check_collisions(self, _data:list[Chain]) -> float:
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


    def try_configuration(self, _start_idx:int, _mirror_permutation:str, _angle_permutation:int) -> float:
        temp:list[Chain] = deepcopy(self.data)
        self.apply_configuration(temp, _start_idx, _mirror_permutation, _angle_permutation)

        return self.check_collisions(temp)
    

    def apply_configuration(self, _data:list[Chain], _start_idx:int, _mirror_permutation:str, _angle_permutation:list[int]):
        assert(len(_mirror_permutation) == len(_angle_permutation))

        # Mirror data 
        end = len(_data)
        p = 0

        for k in range(_start_idx, end, 1):
            if _mirror_permutation[p] == '1':
                _data[k].mirror_xy()

            p += 1

        # Align mirrored data
        p = 0

        for k in range(_start_idx, end, 1):
            angle = _angle_permutation[p]
            _data[k].align(_data[:k], self.settings.align_orientation, angle)

            p += 1


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