from mathutils import Vector

import copy
import numpy as np
from sys            import float_info
from collections    import UserList

from ..b3d_utils import rotation_matrix
from ..dataset.dataset  import Dataset


# -----------------------------------------------------------------------------
# Collision Volumes
# -----------------------------------------------------------------------------
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
        
        raise(Exception('object is neither Vector or AABB'))


# -----------------------------------------------------------------------------
# https://wickedengine.net/2020/04/26/capsule-collision-detection/
class Capsule:
    def __init__(self, base: Vector, tip: Vector, radius: float = .5):
        self.base = base
        self.tip = tip
        self.radius = radius


    @property
    def radius(self):
        return self._radius
    

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.update_hemispheres()


    def update_hemispheres(self):
        normal = (self.tip - self.base).normalized()
        line_offset = normal * self.radius; 
        self.hem_base = self.base + line_offset; 
        self.hem_tip = self.tip - line_offset;


    def collides(self, other: 'Capsule'):
        return self.capsule_collision(other)


    def closest_point_on_segment(self, other: Vector):
        ab = self.base - self.tip
        t = ab.dot(other - self.tip) / ab.dot(ab)
        return self.tip + min(max(t, 0), 1) * ab


    def sphere_collision(self, other: Vector, radius: float):
        closest_point = self.closest_point_on_segment(other)
        pen_normal = closest_point - other
        pen_depth = self.radius + radius - pen_normal.length
        return pen_depth > 0


    def capsule_collision(self, other: 'Capsule'):
        v0 = other.hem_base - self.hem_base
        v1 = other.hem_tip  - self.hem_base
        v2 = other.hem_base - self.hem_tip
        v3 = other.hem_tip  - self.hem_tip

        d0 = v0.dot(v0)
        d1 = v1.dot(v1)
        d2 = v2.dot(v2)
        d3 = v3.dot(v3)

        best_self = self.hem_tip
        if (d2 < d0 or d2 < d1 or d3 < d0 or d3 < d1):
            best_self = self.hem_base

        best_other = other.closest_point_on_segment(best_self)
        return self.sphere_collision(best_other, other.radius)


# -----------------------------------------------------------------------------
# Chain
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, state, points: list[Vector]):
        super().__init__(copy.deepcopy(points))

        self.state = state
        self.to_center()
        self.update_orientation()
        self.update_aabb()
        self.update_capsules()


    def to_center(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset


    def update_orientation(self):
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


    def update_capsules(self):
        self.capsules = []

        for p1, p2 in zip(self.data, self.data[1:]):
            cap = Capsule(p1, p2, 1)
            self.capsules.append(cap)
    

    def update_radius(self, radius: float):
        for cap in self.capsules:
            cap.radius = radius


    def align(self, livechain: 'LiveChain'):
        offset  = livechain[-1]
        offset += livechain[-1] - livechain[-2]

        for p in self.data:
            p += offset

        self.update_aabb()


    def collides(self, other: 'Chain', radius: float):
        if not other.aabb.contains(self.aabb): return False
        for my_cap in self.capsules:
            for other_cap in other.capsules:
                if my_cap.collides(other_cap): return True
            


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


    def to_dataset(self) -> Dataset:
        dataset = Dataset()

        for chain in self.sections:
            bmin = chain.aabb.bmin
            bmax = chain.aabb.bmax

            for k, p in enumerate(chain):
                if k == 0:
                    dataset.append(chain.state, p, aabb_min=bmin, aabb_max=bmax, length=len(chain), chain_start=True)
                else:
                    dataset.append(chain.state, p, aabb_min=bmin, aabb_max=bmax, length=k)

        return dataset