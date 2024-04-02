from bpy.types import Object
from mathutils import Vector

import copy
import numpy as np
from sys            import float_info
from collections    import UserList

from ..dataset.dataset  import Dataset, DatabaseEntry, Attribute, create_polyline
from .bounds            import AABB, Capsule

# -----------------------------------------------------------------------------
class Chain(UserList):
    def __init__(self, state, points: list[Vector], radius = 1):
        super().__init__(copy.deepcopy(points))

        self.state = state
        self.radius = radius
        self.to_center()
        self.init_capsules()
        self.update_orientation()
        self.update_aabb()


    def to_center(self):
        points = self.data
        offset = copy.deepcopy(points[0])
        
        for p in points:
            p -= offset

    
    def init_capsules(self):
        self.capsules = []

        for p1, p2 in zip(self.data, self.data[1:]):
            cap = Capsule(p1, p2, self.radius)
            self.capsules.append(cap)


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

   

    def update_radius(self, radius: float):
        self.radius = radius
        for cap in self.capsules:
            cap.radius = radius


    def align(self, livechain: 'GeneratedChain'):
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
class GeneratedChain(UserList):
    def __init__(self):
        super().__init__()
        self.sections = []
        self.obj = None


    def append(self, chain: Chain):
        self.data.extend(chain)
        self.sections.append(chain)


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