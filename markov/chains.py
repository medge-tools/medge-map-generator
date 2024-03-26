from mathutils import Vector

import copy
import numpy as np
from sys            import float_info
from collections    import UserList

from ..b3d_utils import rotation_matrix


# -----------------------------------------------------------------------------
class AABB:
    def __init__(self, bmin: Vector, bmax: Vector):
        self.bmin = bmin
        self.bmax = bmax


    def contains(self, other: 'Vector | AABB'):
        if isinstance(other, Vector):
            a = other - self.bmin
            b = self.bmax - other
            return a >= 0 and b >= 0
        
        if isinstance(other, AABB):
            if other.bmax < self.bmin: return False
            if other.bmin > self.bmax: return False
            return True

# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, state, points: list[Vector]):
        super().__init__(copy.deepcopy(points))

        self.state = state
        self.to_center()
        self.update_aabb()
        self.calc_orientation()


    def to_center(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset


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


    def calc_orientation(self):
        points = self.data
        oin = Vector((0, 1, 0))
        oout = Vector((0, 1, 0))

        if len(points) >= 2:
            oin  = points[ 1] - points[ 0]
            oout = points[-1] - points[-2]
            oin.normalize()
            oout.normalize()
        
        self.orientation_in  = oin
        self.orientation_out = oout
    

    def align(self, livechain: 'LiveChain'):
        oin = self.orientation_in
        # oout = other.orientation_out
        
        points = self.data

        # Rotate
        # R = rotation_matrix(oin, oout)

        # for p in points:
        #     p.rotate(R)

        # self.orientation_in.rotate(R)
        # self.orientation_out.rotate(R)

        # Translate
        offset = livechain[-1]
        if len(livechain) >= 2:
            offset += livechain[-1] - livechain[-2]

        for p in points:
            p += offset

        self.update_aabb()

    
    def collides(self, other: 'Chain'):
        return other.aabb.contains(self.aabb)


# -----------------------------------------------------------------------------
class ChainPool(UserList):
    def append(self, state, sequence: list[Vector]):
        self.data.append(Chain(state, sequence))
                    

    def random_chain(self) -> Chain:
        n = len(self.data)
        k = np.random.choice(n)

        return copy.deepcopy(self.data[k])
    

# -----------------------------------------------------------------------------
class LiveChain(UserList):
    def __init__(self):
        super().__init__()
        self.sections = []

    
    def append(self, chain: Chain):
        self.data.extend(chain)
        self.sections.append(chain)