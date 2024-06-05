from mathutils import Vector

from .. import b3d_utils

# -----------------------------------------------------------------------------
class Hit:
    def __init__(self, _result:bool, _pen:Vector, _my_point:Vector, _other_point:Vector) -> None:
        self.result = _result
        self.pen = _pen
        self.my_point = _my_point
        self.other_point = _other_point

    @property
    def depth(self):
        return self.pen.length

    def __bool__(self):
        return self.result

    def __mul__(self, _other):
        return self.pen * _other
    
    def __rmul__(self, _other):
        return self * _other


# -----------------------------------------------------------------------------
class AABB:
    def __init__(self, 
                 _bmin:Vector=Vector(), 
                 _bmax:Vector=Vector(), 
                 _margin:float=0):
        self._margin_ = Vector((_margin, _margin, _margin))
        self._bmin_ = _bmin - self._margin_
        self._bmax_ = _bmax + self._margin_

    # BMin
    @property
    def bmin(self):
        return self._bmin_
    
    @bmin.setter
    def bmin(self, _value:Vector):
        self._bmin_ = _value - self._margin_
    
    #BMax
    @property
    def bmax(self):
        return self._bmax_
    
    @bmax.setter
    def bmax(self, _value:Vector):
        self._bmax_ = _value + self._margin_

    # Margin
    @property
    def margin(self):
        return self._margin_
    
    @margin.setter
    def margin(self, _value:float):
        new_margin = Vector((_value, _value, _value))
        self.bmin += self._margin_ - new_margin
        self.bmax -= self._margin_ + new_margin
        self._margin_ = new_margin


    def __str__(self) -> str:
        return f'(Margin included) Min: {self.bmin}, Max: {self.bmax}, Margin: {self.margin}'


    def contains(self, _other:'Vector|AABB'):
        if isinstance(_other, Vector):
            a = _other - self.bmin
            b = self.bmax - _other
            return a >= 0 and b >= 0
        
        if isinstance(_other, AABB):
            if (self.bmin.x > _other.bmax.x or
                self.bmin.y > _other.bmax.y or
                self.bmin.z > _other.bmax.z):
                return False

            if (self.bmax.x < _other.bmin.x or 
                self.bmax.y < _other.bmin.y or 
                self.bmax.z < _other.bmin.z):
                return False

            return True
        
        raise(Exception('object is neither Vector or AABB'))


# -----------------------------------------------------------------------------
# https://wickedengine.net/capsule-collision-detection/
class Capsule:
    def __init__(self, _location:Vector, _height:float, _radius:float):
        self.base = Vector()
        self.tip = Vector() 

        self._location_ = _location
        self._radius_ = _radius
        self._height_ = _height
        
        self.update()
    
    @property
    def is_sphere(self):
        return self.base == self.tip

    @property
    def location(self):
        return self._location_
    
    @location.setter
    def location(self, _value:Vector):
        self._location_ = _value
        self.update()

    @property
    def height(self):
        return self._height_
    
    @height.setter
    def height(self, _value:float):
        self._height_ = _value
        self.update()
        
    @property
    def radius(self):
        return self._radius_
    
    @radius.setter
    def radius(self, _value:float):
        self._radius_ = _value
        self.update()


    def update(self):
        self.base.xyz = self._location_.xyz
        self.base.z += self._radius_

        self.tip.xyz = self._location_.xyz
        self.tip.z += self._height_ - self._radius_


    def collides(self, _other:'Capsule') -> Hit:
        if self.is_sphere:
            best_other = _other.closest_point_on_segment(self.base)
            return self.sphere_collision(best_other, _other._radius_)
        
        return self.capsule_collision(_other)


    def closest_point_on_segment(self, _point:Vector):
        if self.is_sphere: return self.base

        ab = self.tip - self.base
        t = ab.dot(_point - self.base) / ab.dot(ab)

        return self.base + min(max(t, 0), 1) * ab


    def sphere_collision(self, _point:Vector, _radius:float) -> Hit:
        closest_point = self.closest_point_on_segment(_point)
        pen_normal = _point - closest_point
        pen_depth = self._radius_ + _radius - pen_normal.length

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

        return self.sphere_collision(best_other, _other._radius_)
    

    def to_mesh(self):
        height = self.location + Vector((0, 0, self.height))
        verts = [
            self.base, #0
            self.tip,  #1

            self.location,                                          #2
            self.location + Vector(( self.radius, 0, self.radius)), #3
            self.location + Vector((-self.radius, 0, self.radius)), #4
            self.location + Vector((0,  self.radius, self.radius)), #5
            self.location + Vector((0, -self.radius, self.radius)), #6

            height,                                           #7
            height + Vector(( self.radius, 0, -self.radius)), #8
            height + Vector((-self.radius, 0, -self.radius)), #9
            height + Vector((0,  self.radius, -self.radius)), #10
            height + Vector((0, -self.radius, -self.radius)), #11
        ]

        edges = [
            (0, 1),
            (2, 3), (2, 4), (2, 5), (2, 6),
            (7, 8), (7, 9), (7, 10), (7, 11),
            (3, 8), (4, 9), (5, 10), (6, 11)
        ]

        mesh = b3d_utils.new_mesh(verts, edges, [], 'Capsule')
        b3d_utils.new_object(mesh, 'Capsule', 'Capsules')