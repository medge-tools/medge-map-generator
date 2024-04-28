"""
Place this file in the root folder
"""

import  bpy
import  bmesh
import  gpu
from    gpu_extras.batch import batch_for_shader
from    bpy.types   import Object, Mesh, Operator, Context, UIList, UILayout, PropertyGroup
from    bpy.props   import *
from    bmesh.types import BMesh
from    mathutils   import Vector, Matrix, Euler

import math
import numpy as np
from copy import deepcopy


# -----------------------------------------------------------------------------
# Object
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def new_object(_name:str, _data:bpy.types.ID, _collection:str=None, _parent:Object=None):
    obj = bpy.data.objects.new(_name, _data)
    link_to_scene(obj, _collection)
    if(_parent): obj.parent = _parent
    set_active(obj)
    return obj


# -----------------------------------------------------------------------------
def link_to_scene(_obj:Object, _collection:str=None):
    if _obj == None: return
    """If the collection == None, then the object will be linked to the root collection"""
    for uc in _obj.users_collection:
        uc.objects.unlink(_obj)

    if _collection is not None:
        c = bpy.context.blend_data.collections.get(_collection)
        if c == None:
            c = bpy.data.collections.new(_collection)
            bpy.context.collection.children.link(c)
        c.objects.link(_obj)
    else:
        bpy.context.collection.objects.link(_obj)


# -----------------------------------------------------------------------------
def remove_object(_obj:Object):
    bpy.data.objects.remove(_obj)


# -----------------------------------------------------------------------------
def duplicate_object(_obj:Object, _instance=False, _collection=None) -> Object:
    if _instance:
        instance = new_object(_obj.name + '_INST', _obj.data, _collection)
        set_active(instance)
        return instance
    else:
        copy = _obj.copy()
        copy.data = _obj.data.copy()
        copy.name = _obj.name + '_COPY'
        link_to_scene(copy, _collection)
        set_active(copy)
        return copy


# -----------------------------------------------------------------------------
def join_objects(_objects:list[Object]) -> Object:
    deselect_all_objects()

    for obj in _objects:
        select_object(obj)

    bpy.ops.object.join()
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    return bpy.context.object


# -----------------------------------------------------------------------------
def set_active(_obj:Object):
    active = bpy.context.active_object
    if active: active.select_set(False)
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)


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
def apply_all_transforms(_obj: Object):
    mb = _obj.matrix_basis
    if hasattr(_obj.data, 'transform'):
        _obj.data.transform(mb)
    for c in _obj.children:
        c.matrix_local = mb @ c.matrix_local
        
    _obj.matrix_basis.identity()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def set_parent(_child:Object, _parent:Object, _keep_world_location=True):
    _child.parent = _parent
    if _keep_world_location:
        _child.matrix_parent_inverse = _parent.matrix_world.inverted()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def unparent(_obj:Object, _keep_world_location=True):
    parented_wm = _obj.matrix_world.copy()
    _obj.parent = None
    if _keep_world_location:
        _obj.matrix_world = parented_wm


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
def remove_mesh(_mesh:Mesh):
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
# https://blenderartists.org/t/how-to-replace-a-mesh/596225/4
def set_mesh(_obj:Object, _mesh:Mesh):
    old_mesh = _obj.data
    _obj.data = _mesh
    remove_mesh(old_mesh)


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
    set_active(_obj)
    bpy.ops.object.convert(target='MESH') 


# -----------------------------------------------------------------------------
def convert_to_new_mesh(_obj:Object) -> Object:
    mesh = bpy.data.meshes.new_from_object(_obj)
    new_obj = new_object(_obj.name, mesh)
    new_obj.matrix_world = _obj.matrix_world 
    return new_obj


# -----------------------------------------------------------------------------
def get_bmesh(_obj:Object):
    if _obj.mode == 'OBJECT':
        bm = bmesh.new()
        bm.from_mesh(_obj.data)
        return bm
    
    if _obj.mode == 'EDIT':
        return bmesh.from_edit_mesh(_obj.data)


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
    mode = bpy.context.mode
    bm = bmesh.new()

    if mode == 'OBJECT':
        bm.from_mesh(_mesh)
    elif mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(_mesh)

    for m in _transforms:
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    if mode == 'OBJECT':
        bm.to_mesh(_mesh)
    elif mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(_mesh)  



# -----------------------------------------------------------------------------
def snap_to_grid(_mesh:Mesh, _spacing:float):
    mode = bpy.context.mode
    bm = bmesh.new()

    if mode == 'OBJECT':
        bm.from_mesh(_mesh)
    elif mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(_mesh) 

    for v in bm.verts:
        v.co.x = round(v.co.x / _spacing) * _spacing
        v.co.y = round(v.co.y / _spacing) * _spacing
        v.co.z = round(v.co.z / _spacing) * _spacing

    if mode == 'OBJECT':
        bm.to_mesh(_mesh)
    elif mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(_mesh)  


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
def circle(_radius:float, 
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
        c = circle(_radius, (0, 0, z), _angle_step)
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
def create_curve(_num_points=3, 
                 _step=1, 
                 _dir:tuple[float, float, float]=(1, 0, 0)) -> bpy.types.Curve:
    curve = bpy.data.curves.new('CURVE', 'CURVE')
    path = curve.splines.new('NURBS')
    curve.dimensions = '3D'
    path.points.add(_num_points - 1)

    for k in range(_num_points):
        p = Vector(_dir) * _step * k
        path.points[k].co = (*p, 1)

    path.use_endpoint_u = True
    return curve

# -----------------------------------------------------------------------------
# Handler Callback
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def add_callback(_handler, _callback):
    for fn in _handler:
        if fn.__name__ == _callback.__name__: return
    _handler.append(_callback)


# -----------------------------------------------------------------------------
def remove_callback(_handler, _callback):
    for fn in _handler:
        if fn.__name__ == _callback.__name__:
            _handler.remove(fn)


# -----------------------------------------------------------------------------
# Math
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def map_range(_value, _in_min, _in_max, _out_min, _out_max):
    return _out_min + (_value - _in_min) / (_in_max - _in_min) * (_out_max - _out_min)


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/45142959/calculate-rotation-matrix-to-align-two-vectors-in-3d-space 
def rotation_matrix(_v1, _v2):
    """ 
    Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d 'source' vector
    :param vec2: A 3d 'destination' vector
    :return A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    _v1 = [_v1.x, _v1.y, _v1.z]
    _v2 = [_v2.x, _v2.y, _v2.z]

    a, b = (_v1 / np.linalg.norm(_v1)).reshape(3), (_v2 / np.linalg.norm(_v2)).reshape(3)
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
# Classes
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class B3D_UL_GenericList(UIList):
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


    def remove_selected(self):
        self.items.remove(self.selected_item_idx)
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
active_generic_list: GenericList

def begin_generic_list_ops(_list:GenericList):
    global active_generic_list
    active_generic_list = _list


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Add(Operator):
    bl_idname = 'b3d_utils.generic_list_add'
    bl_label = 'Add'
    
    list: GenericList

    def execute(self, _context:Context):
        global active_generic_list
        active_generic_list.add()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Remove(Operator):
    bl_idname = 'b3d_utils.generic_list_remove'
    bl_label = 'Remove'
    bl_options = {'UNDO'}
    

    def execute(self, _context:Context):
        global active_generic_list
        active_generic_list.remove_selected()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Clear(Operator):
    bl_idname = 'b3d_utils.generic_list_clear'
    bl_label = 'Clear'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        global active_generic_list
        active_generic_list.clear()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Move(Operator):
    bl_idname = 'b3d_utils.generic_list_move'
    bl_label = 'Move'
    
    direction : EnumProperty(items=(
        ('UP', 'Up', ''),
        ('DOWN', 'Down', ''),
    ))


    def execute(self, _context:Context):
        dir = (-1 if self.direction == 'UP' else 1)
        global active_generic_list
        active_generic_list.move(dir)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
def draw_generic_list_ops(_layout:UILayout, _list:GenericList):
    begin_generic_list_ops(_list)

    _layout.operator(B3D_OT_GenericList_Add.bl_idname   , icon='ADD'      , text='')
    _layout.operator(B3D_OT_GenericList_Remove.bl_idname, icon='REMOVE'   , text='')
    _layout.operator(B3D_OT_GenericList_Move.bl_idname  , icon='TRIA_UP'  , text='').direction = 'UP'
    _layout.operator(B3D_OT_GenericList_Move.bl_idname  , icon='TRIA_DOWN', text='').direction = 'DOWN'
    _layout.operator(B3D_OT_GenericList_Clear.bl_idname , icon='TRASH'    , text='')


# -----------------------------------------------------------------------------
def draw_generic_list(_layout:UILayout, _list:GenericList, _name:str, _rows=4, _with_generic_ops=True):
    row = _layout.row(align=True)
    row.template_list('B3D_UL_GenericList', _name, _list, 'items', _list, 'selected_item_idx', rows=_rows)
    if not _with_generic_ops: return
    col = row.column(align=True)
    draw_generic_list_ops(col, _list)


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
""" 
Registration depends on auto_load.py:
https://gist.github.com/JacquesLucke/11fecc6ea86ef36ea72f76ca547e795b 

Use these functions when the order of registration is important
"""
import importlib
from . import auto_load


# -----------------------------------------------------------------------------
registered_modules = []
registered_classes = []

# -----------------------------------------------------------------------------
def register_subpackage(_subpackage=''):
    """
    Use empty string ('') to register root 
    """
    def get_all_submodules(directory, package_name):
        return list(iter_submodules(directory, package_name))

    def iter_submodules(path, package_name):
        for name in sorted(iter_submodule_names(path)):
            name = '.' + name
            if _subpackage:
                name = '.' + _subpackage + name
            yield importlib.import_module(name, package_name)

    def iter_submodule_names(path):
        import pkgutil
        for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
            if not is_package:
                yield module_name


    from pathlib import Path
    
    package = Path(__file__).parent
    path = package 
    if _subpackage:
        path /= _subpackage

    modules = get_all_submodules(path, package.name)
    classes = auto_load.get_ordered_classes_to_register(modules)

    auto_load.modules = modules
    auto_load.ordered_classes = classes

    auto_load.register()

    global registered_modules
    global registered_classes

    registered_modules.extend(modules)
    registered_classes.extend(classes)


# -----------------------------------------------------------------------------
def unregister_subpackages():
    global registered_modules
    global registered_classes

    auto_load.modules = registered_modules
    auto_load.ordered_classes = registered_classes

    auto_load.unregister()
