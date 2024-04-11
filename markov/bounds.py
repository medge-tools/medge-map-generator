from mathutils import Vector


# -----------------------------------------------------------------------------
class Hit:
    def __init__(self, _result:bool, _direction:Vector, _my_loc:Vector, _other_loc:Vector) -> None:
        self.result = _result
        self.my_loc = _my_loc
        self.other_loc = _other_loc
        self.direction = _direction

    @property
    def length(self):
        return self.direction.length

    def __bool__(self):
        return self.result

    def __mul__(self, other):
        return self.direction * other
    
    def __rmul__(self, other):
        return self * other


# -----------------------------------------------------------------------------
class AABB:
    def __init__(self, bmin:Vector, bmax:Vector):
        self.bmin = bmin
        self.bmax = bmax


    def __str__(self) -> str:
        return f'Min: {self.bmin}, Max: {self.bmax}'


    def contains(self, other:'Vector|AABB'):
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
    def __init__(self, _base:Vector, _tip:Vector, _radius:float = .5):
        self.base = _base
        self.tip = _tip
        self.radius = _radius

    
    @property
    def is_sphere(self):
        return self.base == self.tip


    def collides(self, _other:'Capsule') -> Hit:
        if self.is_sphere:
            best_other = _other.closest_point_on_segment(self.base)
            return self.sphere_collision(best_other, _other.radius)
        return self.capsule_collision(_other)


    def closest_point_on_segment(self, _point:Vector):
        if self.is_sphere: return self.base

        ab = self.tip - self.base
        t = ab.dot(_point - self.base) / ab.dot(ab)
        return self.base + min(max(t, 0), 1) * ab


    def sphere_collision(self, _point:Vector, _radius:float) -> Hit:
        closest_point = self.closest_point_on_segment(_point)
        pen_normal = _point - closest_point
        pen_depth = self.radius + _radius - pen_normal.length
        return Hit(pen_depth > 0, pen_normal.normalized() * pen_depth, closest_point, _point)


    def capsule_collision(self, _other:'Capsule')  -> Hit:
        v0 = _other.base - self.base
        v1 = _other.tip  - self.base
        v2 = _other.base - self.tip
        v3 = _other.tip  - self.tip

        d0 = v0.dot(v0)
        d1 = v1.dot(v1)
        d2 = v2.dot(v2)
        d3 = v3.dot(v3)

        best_self = self.base
        if (d2 < d0 or d2 < d1 or d3 < d0 or d3 < d1):
            best_self = self.tip

        best_other = _other.closest_point_on_segment(best_self)
        return self.sphere_collision(best_other, _other.radius)