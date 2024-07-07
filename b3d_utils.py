"""
Place this file in the root folder
"""

import bpy
import bmesh
import gpu
from   gpu_extras.batch  import batch_for_shader
from   bpy.types         import Object, Mesh, Operator, Context, UIList, UILayout, PropertyGroup, ID, Collection, Curve, Spline, Driver, DriverVariable
from   bpy.props         import *
from   bmesh.types       import BMesh
from   mathutils         import Vector, Matrix, Euler
from   mathutils.bvhtree import BVHTree

import math
import numpy as np
from typing import Callable
import textwrap


# -----------------------------------------------------------------------------
# Collection
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def new_collection(_name:str, _parent:Collection|str=None):
    """
    Collection will be automatically created if it doesn't exists
    If the _collection == None, then the object will be linked to the root collection
    """
    coll = bpy.context.blend_data.collections.get(_name)

    if coll: return coll
    
    coll = bpy.data.collections.new(_name)

    if _parent:
        p_coll = _parent

        if isinstance(_parent, str):
            p_coll:Collection = bpy.context.blend_data.collections.get(_parent)

            if not p_coll:
                p_coll = bpy.data.collections.new(_parent)
                bpy.context.scene.collection.children.link(p_coll)

        p_coll.children.link(coll)

    else:
        bpy.context.scene.collection.children.link(coll)

    return coll


# -----------------------------------------------------------------------------
# Object
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def set_object_mode(_obj:Object, _mode:str):
    bpy.context.view_layer.objects.active = _obj
    bpy.ops.object.mode_set(mode=_mode)


# -----------------------------------------------------------------------------
def set_object_selectable(_obj:Object, _select:bool):
    _obj.hide_select = not _select


# -----------------------------------------------------------------------------
def select_object(_obj:Object):
    _obj.select_set(True)
    bpy.context.view_layer.objects.active = _obj


# -----------------------------------------------------------------------------
def select_all_objects():
    for obj in bpy.context.scene.objects:
        select_object(obj)


# -----------------------------------------------------------------------------
def deselect_all_objects():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


# -----------------------------------------------------------------------------
def set_active_object(_obj:Object):
    active = bpy.context.active_object
    if active: active.select_set(False)
    select_object(_obj)

# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def unparent(_obj:Object, _keep_world_location=True):
    if not _obj.parent: return

    parented_wm = _obj.matrix_world.copy()
    _obj.parent = None
    
    if _keep_world_location:
        _obj.matrix_world = parented_wm


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def set_parent(_child:Object, _parent:Object, _keep_world_location=True):
    _child.parent = _parent

    if _keep_world_location:
        _child.matrix_parent_inverse = _parent.matrix_world.inverted()


# -----------------------------------------------------------------------------
def reparent(_child:Object, _parent:Object, _keep_world_location=True):
    unparent(_child, _keep_world_location)
    set_parent(_child, _parent, _keep_world_location)


# -----------------------------------------------------------------------------
def link_object_to_scene(_obj:Object, _collection:Collection|str=None, _clear_users_collection=True):
    """
    Collection will be automatically created if it doesn't exists
    If the _collection == None, then the object will be linked to the root collection
    """
    if not _obj: return

    if _clear_users_collection:
        for uc in _obj.users_collection:
            uc.objects.unlink(_obj)

    if _collection:
        coll = _collection

        if isinstance(_collection, str):
            coll = new_collection(_collection)

        coll.objects.link(_obj)

    else:
        if (coll := bpy.context.collection):
            coll.objects.link(_obj)
            
        else:
            bpy.context.scene.collection.objects.link(_obj)


# -----------------------------------------------------------------------------
def new_object(_data:ID, _name:str, _collection:Collection|str=None, _parent:Object=None, _set_active=True):
    obj = bpy.data.objects.new(_name, _data)
    obj.location = bpy.context.scene.cursor.location

    link_object_to_scene(obj, _collection)

    if _parent: 
        set_parent(obj, _parent)

    if _set_active:
        set_active_object(obj)

    return obj


# -----------------------------------------------------------------------------
def remove_object(_obj:Object):
    if not _obj: return
    bpy.data.objects.remove(_obj)


# -----------------------------------------------------------------------------
def remove_object_with_children(_obj:Object):
    if not _obj: return

    for child in _obj.children_recursive:
        bpy.data.objects.remove(child)

    bpy.data.objects.remove(_obj)
    

# -----------------------------------------------------------------------------
def duplicate_object(_obj:Object, _instance=False, _collection:Collection|str=None) -> Object:
    if _instance:
        instance = new_object(_obj.data, 'INST_' + _obj.name, _collection)
        set_active_object(instance)

        return instance
    
    else:
        copy = _obj.copy()
        copy.data = _obj.data.copy()
        copy.name = 'COPY_' + _obj.name

        link_object_to_scene(copy, _collection)
        set_active_object(copy)

        return copy
    

# -----------------------------------------------------------------------------
def duplicate_object_with_children(_obj:Object, _instance=False, _collection:Collection|str=None, _link_modifiers=True) -> Object:
    if _link_modifiers: 
        root = duplicate_object(_obj, _instance, _collection)

        for child in _obj.children:
            copy = duplicate_object(child, _instance, _collection)
            reparent(copy, root)

        return root
        
    else:
        with bpy.context.temp_override(active_object=_obj, selected_objects=[_obj, *_obj.children]):
            bpy.context.view_layer.objects.active = _obj
            bpy.ops.object.duplicate()

        for obj in bpy.context.selected_objects:
            link_object_to_scene(obj, _collection)

        return bpy.context.object


# -----------------------------------------------------------------------------
def join_objects(_objects:list[Object]) -> Object:
    with bpy.context.temp_override(selected_objects=_objects):
        bpy.ops.object.join()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    return bpy.context.object


# -----------------------------------------------------------------------------
# Object Transformations
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Rotation mode: 
#   https://gist.github.com/behreajj/2dbb6fb7cee78c167cd85085e67bcdf6
# Mirror rotation: 
#   https://www.gamedev.net/forums/topic/#599824-mirroring-a-quaternion-against-the-yz-plane/
def get_rotation_mirrored_x_axis(_obj:Object) -> Euler:
    prev_rot_mode = _obj.rotation_mode
    _obj.rotation_mode = 'QUATERNION'

    q = _obj.rotation_quaternion.copy()
    q.x *= -1
    q.w *= -1
    _obj.rotation_mode = prev_rot_mode

    return q.to_euler()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/159538/how-to-apply-all-transformations-to-an-object-at-low-level
def apply_all_transforms(_obj:Object):
    mb = _obj.matrix_basis
    if hasattr(_obj.data, 'transform'):
        _obj.data.transform(mb)
    for c in _obj.children:
        c.matrix_local = mb @ c.matrix_local
        
    _obj.matrix_basis.identity()

# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/13840418/force-matrix-world-to-be-recalculated-in-blender/57485640#57485640
def update_matrices(_obj:Object):
    """
    Calls to bpy.context.scene.update() can become expensive when called within a loop. 
    If your objects have no complex constraints (e.g. plain or parented), the following can be used to recompute the world matrix after changing object's .location, .rotation_euler\quaternion, or .scale. 
    """
    if _obj.parent is None:
        _obj.matrix_world = _obj.matrix_basis

    else:
        _obj.matrix_world = _obj.parent.matrix_world * \
                           _obj.matrix_parent_inverse * \
                           _obj.matrix_basis
        

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blenderartists.org/t/how-to-replace-a-mesh/596225/4
def remove_data(_mesh:Mesh):
    # Extra test because this can crash Blender if not done correctly.
    result = False
    if _mesh and _mesh.users == 0: 
        try:
            _mesh.user_clear()
            can_continue = True
        except: can_continue = False
        if can_continue == True:
            try:
                bpy.data.meshes.remove(_mesh)
                result = True
            except: result = False
    else: result = True
    return result


# -----------------------------------------------------------------------------
def set_data(_obj:Object, _data:ID):
    old_data = _obj.data
    _obj.data = _data
    remove_data(old_data)


# -----------------------------------------------------------------------------
# Mesh
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def new_mesh(
        _verts:list[tuple[float, float, float]], 
        _edges:list[tuple[int, int]], 
        _faces:list[tuple[int, ...]], 
        _name: str) -> Mesh:
    mesh = bpy.data.meshes.new(_name)
    mesh.from_pydata(_verts, _edges, _faces)

    return mesh


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
def join_meshes(_meshes:list[Mesh]):
    bm = bmesh.new()
    bm_verts = bm.verts.new
    bm_faces = bm.faces.new
    bm_edges = bm.edges.new

    for mesh in _meshes:
        bm_to_add = bmesh.new()
        bm_to_add.from_mesh(mesh)
        offset = len(bm.verts)

        for v in bm_to_add.verts:
            bm_verts(v.co)

        bm.verts.index_update()
        bm.verts.ensure_lookup_table()

        if bm_to_add.faces:
            for face in bm_to_add.faces:
                bm_faces(tuple(bm.verts[i.index+offset] for i in face.verts))
            bm.faces.index_update()

        if bm_to_add.edges:
            for edge in bm_to_add.edges:
                edge_seq = tuple(bm.verts[i.index+offset] for i in edge.verts)
                try: bm_edges(edge_seq)
                except ValueError: # edge exists!
                    pass
            bm.edges.index_update()
        bm_to_add.free()

    bm.normal_update()
    bm.to_mesh(_meshes[0])
    bm.free()

    return _meshes[0]


# -----------------------------------------------------------------------------
def convert_to_mesh_in_place(_obj:Object):
    set_active_object(_obj)
    bpy.ops.object.convert(target='MESH') 


# -----------------------------------------------------------------------------
def convert_to_new_mesh(_obj:Object) -> Object:
    mesh = bpy.data.meshes.new_from_object(_obj)
    new_obj = new_object(mesh, _obj.name)
    new_obj.matrix_world = _obj.matrix_world 

    return new_obj


# -----------------------------------------------------------------------------
def get_bmesh_from_object(_obj:Object) -> BMesh | None:
    if _obj.mode == 'OBJECT':
        bm = bmesh.new()
        bm.from_mesh(_obj.data)
        
        return bm
    
    if _obj.mode == 'EDIT':
        return bmesh.from_edit_mesh(_obj.data)
    
    return None


# -----------------------------------------------------------------------------
def get_bmesh_from_mesh(_mesh:Mesh) -> BMesh | None:
    mode = bpy.context.mode

    if mode == 'OBJECT':
        bm = bmesh.new()
        bm.from_mesh(_mesh)
        return bm

    elif mode == 'EDIT_MESH':
        bm = bmesh.new()
        bm = bmesh.from_edit_mesh(_mesh)
        return bm
    
    return None

# -----------------------------------------------------------------------------
def update_mesh_from_bmesh(_mesh:Mesh, _bm:BMesh):
    mode = bpy.context.mode

    if mode == 'OBJECT':
        _bm.to_mesh(_mesh)

    elif mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(_mesh) 


# -----------------------------------------------------------------------------
def select_all_vertices(_bm:BMesh):
    for v in _bm.verts:
        v.select = True

    _bm.select_flush_mode()   


# -----------------------------------------------------------------------------
def deselect_all_vertices(_bm:BMesh):
    for v in _bm.verts:
        v.select = False

    _bm.select_flush_mode()   
    

# -----------------------------------------------------------------------------
def transform(_mesh:Mesh, _transforms:list[Matrix]):
    bm = get_bmesh_from_mesh(_mesh)

    for m in _transforms:
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
 
    update_mesh_from_bmesh(_mesh, bm)


# -----------------------------------------------------------------------------
def snap_to_grid(_mesh:Mesh, _spacing:float):
    bm = get_bmesh_from_mesh(_mesh)

    for v in bm.verts:
        v.co.x = round(v.co.x / _spacing) * _spacing
        v.co.y = round(v.co.y / _spacing) * _spacing
        v.co.z = round(v.co.z / _spacing) * _spacing

    update_mesh_from_bmesh(_mesh, bm)


# -----------------------------------------------------------------------------
def mesh_bounds(_obj:Object) -> tuple[Vector, Vector]:
    bbmin = Vector((float('inf'), float('inf'), float('inf')))
    bbmax = Vector((float('-inf'), float('-inf'), float('-inf')))

    for vertex in _obj.data.vertices:
        world_co = _obj.matrix_world @ vertex.co
        bbmin.x = min(bbmin[0], world_co[0])
        bbmin.y = min(bbmin[1], world_co[1])
        bbmin.z = min(bbmin[2], world_co[2])

        bbmax.x = max(bbmax[0], world_co[0])
        bbmax.y = max(bbmax[1], world_co[1])
        bbmax.z = max(bbmax[2], world_co[2])

    return bbmin, bbmax


# -----------------------------------------------------------------------------
# Collection
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_active_collection():
    return bpy.context.view_layer.active_layer_collection.collection


# -----------------------------------------------------------------------------
# Create
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def create_cube(_size:tuple[float, float, float]=(1, 1, 1)) -> Mesh:
    s = Vector(_size)
    s *= .5

    verts = [
        Vector((-1 * s[0], -1 * s[1], -1 * s[2])),
        Vector((-1 * s[0],  1 * s[1], -1 * s[2])),
        Vector(( 1 * s[0],  1 * s[1], -1 * s[2])),
        Vector(( 1 * s[0], -1 * s[1], -1 * s[2])),
        Vector((-1 * s[0], -1 * s[1],  1 * s[2])),
        Vector((-1 * s[0],  1 * s[1],  1 * s[2])),
        Vector(( 1 * s[0],  1 * s[1],  1 * s[2])),
        Vector(( 1 * s[0], -1 * s[1],  1 * s[2])),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (4, 5, 1, 0),
        (7, 4, 0, 3),
        (6, 7, 3, 2),
        (5, 6, 2, 1),
    ]
    return new_mesh(verts, [], faces, 'CUBE')


# -----------------------------------------------------------------------------
def create_arrow(_size:tuple[float, float]=(1, 1)) -> Mesh:
    s = Vector(_size)
    s *= .5

    verts = [
        Vector((-1 * s[0],  0.4 * s[1], 0)),
        Vector(( 0 * s[0],  0.4 * s[1], 0)),
        Vector(( 0 * s[0],  1   * s[1], 0)), 
        Vector(( 1 * s[0],  0   * s[1], 0)), 
        Vector(( 0 * s[0], -1   * s[1], 0)), 
        Vector(( 0 * s[0], -0.4 * s[1], 0)),
        Vector((-1 * s[0], -0.4 * s[1], 0)),
    ]
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (6, 0),
    ]

    return new_mesh(verts, edges, [], 'ARROW')


# -----------------------------------------------------------------------------
def create_bounding_box(_obj:Object) -> Object:
    """_obj: Object of type Mesh"""
    bbox_min, bbox_max = mesh_bounds(_obj)

    # Calculate box dimensions based on bounding box
    center = (bbox_max + bbox_min) * 0.5
    size = (bbox_max - bbox_min) * 0.5

    # Create the box object
    bpy.ops.mesh.primitive_cube_add(location=center, scale=size)

    return bpy.context.object


# -----------------------------------------------------------------------------
def get_circle_vertices(_radius:float, 
           _location:tuple[float, float,float], 
           _angle_step=10) -> list[tuple[float, float, float]]:
    (a, b, c) = _location

    verts = []
    for angle in range(0, 360, _angle_step):
        angle_radius = math.radians(angle)
        x = a + _radius * math.cos(angle_radius)
        y = b + _radius * math.sin(angle_radius)
        verts.append((x, y, c))
        
    # Adding the first vertex as last vertex to close the loop
    verts.append(verts[0])
    
    return verts


# -----------------------------------------------------------------------------
def create_cylinder(_radius=2, 
                    _height=2, 
                    _row_height=1, 
                    _angle_step=10, 
                    _make_faces=True) -> Mesh:
    _height += 1
    verts = []
    per_circle_verts = 0

    for z in np.arange(0, _height, _row_height):
        c = get_circle_vertices(_radius, (0, 0, z), _angle_step)
        per_circle_verts = len(c)
        verts += c

    rows = int(_height / _row_height)
    faces = []

    if _make_faces:
        for row in range(0, rows - 1):
            for index in range(0, per_circle_verts - 1):
                v1 = index + (row * per_circle_verts)
                v2 = v1 + 1
                v3 = v1 + per_circle_verts
                v4 = v2 + per_circle_verts
                faces.append((v1, v3, v4, v2))

    return new_mesh(verts, [], faces, 'CYLINDER')


# -----------------------------------------------------------------------------
#https://blender.stackexchange.com/questions/127603/how-to-specify-nurbs-path-vertices-in-python
def create_curve(_type='NURBS', _num_points=3, _resolution=12) -> tuple[Curve, Spline]:
    curve = bpy.data.curves.new('CURVE', 'CURVE')
    curve.dimensions = '3D'

    path = curve.splines.new(_type)

    if _type != 'BEZIER':
        path.points.add(_num_points - 1)
        points = path.points

    else:
        path.bezier_points.add(_num_points - 1)
        points = path.bezier_points
        
    for k, p in enumerate(points):
        x = 1 * k
        p.co = x, 0, 0

    path.resolution_u = _resolution
    path.use_endpoint_u = True

    return curve, path


# -----------------------------------------------------------------------------
# Handler Callback
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def add_callback(_handler, _callback:Callable):
    for fn in _handler:
        if fn.__name__ == _callback.__name__: return
    _handler.append(_callback)


# -----------------------------------------------------------------------------
def remove_callback(_handler, _callback:Callable):
    for fn in _handler:
        if fn.__name__ == _callback.__name__:
            _handler.remove(fn)


# -----------------------------------------------------------------------------
# Math
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def map_range(_value:float, _in_min:float, _in_max:float, _out_min:float, _out_max:float):
    return _out_min + (_value - _in_min) / (_in_max - _in_min) * (_out_max - _out_min)


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/45142959/calculate-rotation-matrix-to-align-two-vectors-in-3d-space 
def rotation_matrix(_v1:Vector, _v2:Vector):
    """ 
    Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d 'source' vector
    :param vec2: A 3d 'destination' vector
    :return A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    v1 = [_v1[0], _v1[1], _v1[2]]
    v2 = [_v2[0], _v2[1], _v2[2]]

    a, b = (v1 / np.linalg.norm(v1)).reshape(3), (v2 / np.linalg.norm(v2)).reshape(3)
    v = np.cross(a, b)
    
    if not any(v):
        return Matrix.Identity(3)

    d = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    r = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - d) / (s ** 2))
    
    R = Matrix(((r[0][0], r[0][1], r[0][2]),
                (r[1][0], r[1][1], r[1][2]), 
                (r[2][0], r[2][1], r[2][2])))

    return R


# -----------------------------------------------------------------------------
# Graphics
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/61699/how-to-draw-geometry-in-3d-view-window-with-bgl
shader_coords = []
shader_indices = []

def begin_batch():
    global shader_coords
    global shader_indices
    shader_coords = []
    shader_indices = []


# -----------------------------------------------------------------------------
def batch_add_coords(_coords:list[Vector]):
    global shader_coords
    shader_coords.extend(_coords)


# -----------------------------------------------------------------------------
def batch_add_indices(_inds:list[int]):
    global shader_indices
    shader_indices.extend(_inds)


# -----------------------------------------------------------------------------
def draw_batch_3d(_color:tuple, _width=1.0, _type='LINES'):
    global shader_coords
    global shader_indices
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    gpu.state.line_width_set(_width)
    batch = batch_for_shader(shader, _type, {'pos': shader_coords}, indices=shader_indices)
    shader.bind()
    shader.uniform_float('color', _color)
    batch.draw(shader)


# -----------------------------------------------------------------------------
def draw_aabb_lines_3d(_bmin:Vector, _bmax:Vector, _color:tuple, _width=1):
    v0 = _bmin
    v1 = (_bmax.x, _bmin.y, _bmin.z)
    v2 = (_bmin.x, _bmax.y, _bmin.z)
    v3 = (_bmin.x, _bmin.y, _bmax.z)

    v4 = _bmax
    v5 = (_bmin.x, _bmax.y, _bmax.z)
    v6 = (_bmax.x, _bmin.y, _bmax.z)
    v7 = (_bmax.x, _bmax.y, _bmin.z)

    begin_batch()
    batch_add_coords([v0, v1, v2, v3, v4, v5, v6, v7])
    batch_add_indices([
        (0, 1), (0, 2), (0, 3),
        (4, 5), (4, 6), (4, 7),
        (1, 7), (1, 6), 
        (2, 7), (2, 5),
        (3, 5), (3, 6)
    ])

    draw_batch_3d(_color, _width, 'LINES')


# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/39127/how-to-put-together-a-driver-with-python
def add_driver(_target:ID, _prop:str, _index=-1) -> Driver:
    driver = _target.driver_add(_prop, _index).driver
    
    return driver


# -----------------------------------------------------------------------------
def add_driver_variable(_driver:Driver, _source:ID, _source_type:str, _var_type:str, _data_path:str, _var_name='var') -> DriverVariable:
    var = _driver.variables.new()
    
    var.name = _var_name
    var.type = _var_type

    var.targets[-1].id_type    = _source_type
    var.targets[-1].id         = _source
    var.targets[-1].data_path  = _data_path
    
    return var


# -----------------------------------------------------------------------------
# Intersection
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/a/310665
def create_bvh_tree_from_object(_obj:Object, _apply_modifiers=True) -> BVHTree:
    bm = None

    if _apply_modifiers:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = _obj.evaluated_get(depsgraph)
        bm = get_bmesh_from_object(eval_obj)
        bm.transform(eval_obj.matrix_world)

    else:
        bm = get_bmesh_from_object(_obj)
        bm.transform(_obj.matrix_world)
    
    bvh = BVHTree.FromBMesh(bm)
    
    return bvh


# -----------------------------------------------------------------------------
def check_objects_intersection(_obj1:Object, _obj2:Object, _apply_modifiers=True) -> list[tuple[int, int]]:
    bvh1 = create_bvh_tree_from_object(_obj1, _apply_modifiers)
    bvh2 = create_bvh_tree_from_object(_obj2, _apply_modifiers)

    return bvh1.overlap(bvh2)


# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def auto_gui_props(_data:PropertyGroup, _layout:UILayout):
    for key in _data.__annotations__.keys():
        _layout.prop(_data, key)


# -----------------------------------------------------------------------------
def draw_box(_layout:UILayout, _text:str, _alignment='CENTER'):
    box = _layout.box()
    row = box.row()
    row.alignment = _alignment
    row.label(text=_text)


# -----------------------------------------------------------------------------
# https://b3d.interplanety.org/en/multiline-text-in-blender-interface-panels/
def multiline_text(_context:Context, _layout:UILayout, _text:str):
    chars = int(_context.region.width / 7) # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=_text)

    for line in text_lines:
        _layout.label(text=line)


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blenderartists.org/t/print-to-info-area/1383928/3
def print_console(_text:str):
    for w in bpy.context.window_manager.windows:
        s = w.screen
        for a in s.areas:
            if a.type == 'CONSOLE':
                with bpy.context.temp_override(window=w, screen=s, area=a):
                    bpy.ops.console.scrollback_append(text=_text, type="OUTPUT")


# -----------------------------------------------------------------------------
# Generic List
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class B3D_UL_generic_list_draw(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
        layout.label(text=item.name)


# -----------------------------------------------------------------------------
class GenericList:
    """
    This class can't be used as is. Inherit from this class and add an CollectionProperty named 'items'
    """
    def add(self):
        item = self.items.add()
        self.selected_item_idx = len(self.items) - 1
        return item


    def remove(self, _index:int=None):
        if not _index:
            _index = self.selected_item_idx

        self.items.remove(_index)
        self.selected_item_idx = min(max(0, self.selected_item_idx - 1), len(self.items) - 1)

    
    def clear(self):
        self.items.clear()
        self.selected_item_idx = 0


    def move(self, _direction:int):
        new_idx = self.selected_item_idx
        new_idx += _direction
        self.items.move(new_idx, self.selected_item_idx)
        self.selected_item_idx = max(0, min(new_idx, len(self.items) - 1))


    def get_selected(self):
        if self.items:
            return self.items[self.selected_item_idx]
        return None


    selected_item_idx: IntProperty(name='PRIVATE')


# -----------------------------------------------------------------------------
generic_lists:dict[str, GenericList] = dict()


# -----------------------------------------------------------------------------
class B3D_OT_generic_list_add(Operator):
    bl_idname = 'b3d_utils.generic_list_add'
    bl_label = 'Add'

    list_name: StringProperty()
    
    def execute(self, _context:Context):
        global generic_lists
        generic_lists[self.list_name].add()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_generic_list_remove(Operator):
    bl_idname = 'b3d_utils.generic_list_remove'
    bl_label = 'Remove'
    bl_options = {'UNDO'}

    list_name: StringProperty()

    def execute(self, _context:Context):
        global generic_lists
        generic_lists[self.list_name].remove()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_generic_list_clear(Operator):
    bl_idname = 'b3d_utils.generic_list_clear'
    bl_label = 'Clear'
    bl_options = {'UNDO'}

    list_name: StringProperty()

    def execute(self, _context:Context):
        global generic_lists
        generic_lists[self.list_name].clear()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_generic_list_move(Operator):
    bl_idname = 'b3d_utils.generic_list_move'
    bl_label = 'Move'
    
    list_name: StringProperty()

    direction: EnumProperty(items=(
        ('UP', 'Up', ''),
        ('DOWN', 'Down', ''),
    ))


    def execute(self, _context:Context):
        dir = (-1 if self.direction == 'UP' else 1)

        global generic_lists
        generic_lists[self.list_name].move(dir)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
def draw_generic_list_ops(_layout:UILayout, _list_name:str, _filter:set):
    if 'ADD' in _filter:
        _layout.operator(B3D_OT_generic_list_add.bl_idname, icon='ADD', text='').list_name = _list_name

    if 'REMOVE' in _filter:
        _layout.operator(B3D_OT_generic_list_remove.bl_idname, icon='REMOVE', text='').list_name = _list_name
    
    if 'MOVE' in _filter:
        op = _layout.operator(B3D_OT_generic_list_move.bl_idname, icon='TRIA_UP', text='')
        op.list_name = _list_name
        op.direction = 'UP'
        
        op = _layout.operator(B3D_OT_generic_list_move.bl_idname, icon='TRIA_DOWN', text='')
        op.list_name = _list_name
        op.direction = 'DOWN'

    if 'CLEAR' in _filter:
        _layout.operator(B3D_OT_generic_list_clear.bl_idname, icon='TRASH', text='')


# -----------------------------------------------------------------------------
def draw_generic_list(_layout:UILayout, _list:GenericList, _name:str, _rows=4, _generic_ops_filter:set={'ADD', 'REMOVE', 'MOVE', 'CLEAR'}):
    row = _layout.row(align=True)
    row.template_list('B3D_UL_generic_list_draw', _name, _list, 'items', _list, 'selected_item_idx', rows=_rows)

    global generic_lists
    generic_lists[_name] = _list

    col = row.column(align=True)
    draw_generic_list_ops(col, _name, _generic_ops_filter)


# -----------------------------------------------------------------------------
# NURBS Curve Interpolation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/34145/calculate-points-on-a-nurbs-curve-without-converting-to-mesh
def interpolate_nurbs(nu, resolu, stride):
    EPS = 1e-6
    coord_index = istart = iend = 0

    coord_array = [0.0] * (3 * nu.resolution_u * macro_segmentsu(nu))
    sum_array = [0] * nu.point_count_u
    basisu = [0.0] * macro_knotsu(nu)
    knots = makeknots(nu)

    resolu = resolu * macro_segmentsu(nu)
    ustart = knots[nu.order_u - 1]
    uend   = knots[nu.point_count_u + nu.order_u - 1] if nu.use_cyclic_u else \
             knots[nu.point_count_u]
    ustep  = (uend - ustart) / (resolu - (0 if nu.use_cyclic_u else 1))
    cycl = nu.order_u - 1 if nu.use_cyclic_u else 0

    u = ustart
    while resolu:
        resolu -= 1
        istart, iend = basisNurb(u, nu.order_u, nu.point_count_u + cycl, knots, basisu, istart, iend)

        #/* calc sum */
        sumdiv = 0.0
        sum_index = 0
        pt_index = istart - 1
        for i in range(istart, iend + 1):
            if i >= nu.point_count_u:
                pt_index = i - nu.point_count_u
            else:
                pt_index += 1

            sum_array[sum_index] = basisu[i] * nu.points[pt_index].co[3]
            sumdiv += sum_array[sum_index]
            sum_index += 1

        if (sumdiv != 0.0) and (sumdiv < 1.0 - EPS or sumdiv > 1.0 + EPS):
            sum_index = 0
            for i in range(istart, iend + 1):
                sum_array[sum_index] /= sumdiv
                sum_index += 1

        coord_array[coord_index: coord_index + 3] = (0.0, 0.0, 0.0)

        sum_index = 0
        pt_index = istart - 1
        for i in range(istart, iend + 1):
            if i >= nu.point_count_u:
                pt_index = i - nu.point_count_u
            else:
                pt_index += 1

            if sum_array[sum_index] != 0.0:
                for j in range(3):
                    coord_array[coord_index + j] += sum_array[sum_index] * nu.points[pt_index].co[j]
            sum_index += 1

        coord_index += stride
        u += ustep

    return coord_array


def macro_knotsu(nu):
    return nu.order_u + nu.point_count_u + (nu.order_u - 1 if nu.use_cyclic_u else 0)

def macro_segmentsu(nu):
    return nu.point_count_u if nu.use_cyclic_u else nu.point_count_u - 1

def makeknots(nu):
    knots = [0.0] * (4 + macro_knotsu(nu))
    flag = nu.use_endpoint_u + (nu.use_bezier_u << 1)
    if nu.use_cyclic_u:
        calcknots(knots, nu.point_count_u, nu.order_u, 0)
        makecyclicknots(knots, nu.point_count_u, nu.order_u)
    else:
        calcknots(knots, nu.point_count_u, nu.order_u, flag)
    return knots

def calcknots(knots, pnts, order, flag):
    pnts_order = pnts + order
    if flag == 1:
        k = 0.0
        for a in range(1, pnts_order + 1):
            knots[a - 1] = k
            if a >= order and a <= pnts:
                k += 1.0
    elif flag == 2:
        if order == 4:
            k = 0.34
            for a in range(pnts_order):
                knots[a] = math.floor(k)
                k += (1.0 / 3.0)
        elif order == 3:
            k = 0.6
            for a in range(pnts_order):
                if a >= order and a <= pnts:
                    k += 0.5
                    knots[a] = math.floor(k)
    else:
        for a in range(pnts_order):
            knots[a] = a

def makecyclicknots(knots, pnts, order):
    order2 = order - 1

    if order > 2:
        b = pnts + order2
        for a in range(1, order2):
            if knots[b] != knots[b - a]:
                break

            if a == order2:
                knots[pnts + order - 2] += 1.0

    b = order
    c = pnts + order + order2
    for a in range(pnts + order2, c):
        knots[a] = knots[a - 1] + (knots[b] - knots[b - 1])
        b -= 1

def basisNurb(t, order, pnts, knots, basis, start, end):
    i1 = i2 = 0
    orderpluspnts = order + pnts
    opp2 = orderpluspnts - 1

    # this is for float inaccuracy
    if t < knots[0]:
        t = knots[0]
    elif t > knots[opp2]:
        t = knots[opp2]

    # this part is order '1'
    o2 = order + 1
    for i in range(opp2):
        if knots[i] != knots[i + 1] and t >= knots[i] and t <= knots[i + 1]:
            basis[i] = 1.0
            i1 = i - o2
            if i1 < 0:
                i1 = 0
            i2 = i
            i += 1
            while i < opp2:
                basis[i] = 0.0
                i += 1
            break

        else:
            basis[i] = 0.0

    basis[i] = 0.0

    # this is order 2, 3, ...
    for j in range(2, order + 1):

        if i2 + j >= orderpluspnts:
            i2 = opp2 - j

        for i in range(i1, i2 + 1):
            if basis[i] != 0.0:
                d = ((t - knots[i]) * basis[i]) / (knots[i + j - 1] - knots[i])
            else:
                d = 0.0

            if basis[i + 1] != 0.0:
                e = ((knots[i + j] - t) * basis[i + 1]) / (knots[i + j] - knots[i + 1])
            else:
                e = 0.0

            basis[i] = d + e

    start = 1000
    end = 0

    for i in range(i1, i2 + 1):
        if basis[i] > 0.0:
            end = i
            if start == 1000:
                start = i

    return start, end