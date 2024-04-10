from mathutils import Vector


# -----------------------------------------------------------------------------
class Hit:
    def __init__(self, result: bool, impact_vector: Vector) -> None:
        self.result = result
        self.impact_vector = impact_vector

    @property
    def length(self):
        return self.impact_vector.length

    def __bool__(self):
        return self.result

    def __mul__(self, other):
        return self.impact_vector * other
    
    def __rmul__(self, other):
        return self * other


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
            if (self.bmin.x > other.bmax.x or
                self.bmin.y > other.bmax.y or
                self.bmin.z > other.bmax.z):
                return False

            if (self.bmax.x < other.bmin.x or 
                self.bmax.y < other.bmin.y or 
                self.bmax.z < other.bmin.z):
                return False

            return True
        
        raise(Exception('object is neither Vector or AABB'))


# -----------------------------------------------------------------------------
# https://wickedengine.net/2020/04/26/capsule-collision-detection/
class Capsule:
    def __init__(self, base: Vector, tip: Vector, radius: float = .5):
        self.base = base
        self.tip = tip
        self._radius = radius
        self.update_hemispheres()


    @property
    def radius(self):
        return self._radius
    

    @radius.setter
    def radius(self, value: float):
        self._radius = value
        self.update_hemispheres()


    # TODO: Check if tip == base
    def update_hemispheres(self):
        n = (self.tip - self.base).normalized()
        line_offset = n * self.radius; 
        self.hem_base = self.base + line_offset; 
        self.hem_tip = self.tip - line_offset;


    def collides(self, other: 'Capsule') -> Hit:
        return self.capsule_collision(other)


    # TODO: Check if tip == base
    def closest_point_on_segment(self, other: Vector):
        ab = self.base - self.tip
        t = ab.dot(other - self.tip) / ab.dot(ab)
        return self.tip + min(max(t, 0), 1) * ab


    def sphere_collision(self, other: Vector, radius: float) -> Hit:
        closest_point = self.closest_point_on_segment(other)
        pen_normal = other - closest_point
        pen_depth = self.radius + radius - pen_normal.length
        return Hit(pen_depth > 0, pen_normal.normalized() * pen_depth)


    def capsule_collision(self, other: 'Capsule')  -> Hit:
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