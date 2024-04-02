from mathutils import Vector


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
        n = (self.tip - self.base).normalized()
        line_offset = n * self.radius; 
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