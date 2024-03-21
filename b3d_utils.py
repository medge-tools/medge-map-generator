"""
Place this file in the root folder
"""

import  bpy
import  bmesh
from    bpy.types   import Object, Mesh, Operator, Context, UIList, UILayout
from    bpy.props   import *
from    bmesh.types import BMesh
from    mathutils   import Vector, Matrix, Euler

import math
import numpy as np


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def set_active(obj: Object):
    active = bpy.context.active_object
    if active: active.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


# -----------------------------------------------------------------------------
def set_object_mode(obj: Object, m):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode=m)


# -----------------------------------------------------------------------------
def set_object_selectable(obj: Object, select: bool):
    obj.hide_select = not select


# -----------------------------------------------------------------------------
def select_object(obj: Object):
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# -----------------------------------------------------------------------------
def select_all_objects():
    for obj in bpy.context.scene.objects:
        select_object(obj)


# -----------------------------------------------------------------------------
def deselect_all_objects():
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


# -----------------------------------------------------------------------------
def select_all_vertices(bm: BMesh):
    for v in bm.verts:
        v.select = True
    bm.select_flush_mode()   


# -----------------------------------------------------------------------------
def deselect_all_vertices(bm: BMesh):
    for v in bm.verts:
        v.select = False
    bm.select_flush_mode()   
    

# -----------------------------------------------------------------------------
def link_to_scene(obj: Object, collection: str = None):
    if obj == None: return
    """If the collection == None, then the object will be linked to the root collection"""
    for uc in obj.users_collection:
        uc.objects.unlink(obj)

    if collection is not None:
        c = bpy.context.blend_data.collections.get(collection)
        if c == None:
            c = bpy.data.collections.new(collection)
            bpy.context.scene.collection.children.link(c)
        c.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)


# -----------------------------------------------------------------------------
def auto_gui_properties(data, layout: bpy.types.UILayout):
    for key in data.__annotations__.keys():
        layout.prop(data, key)


# -----------------------------------------------------------------------------
# Handler Callback
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def add_callback(handler, function):
    for fn in handler:
        if fn.__name__ == function.__name__: return
    handler.append(function)


# -----------------------------------------------------------------------------
def remove_callback(handler, function):
    for fn in handler:
        if fn.__name__ == function.__name__:
            handler.remove(fn)


# -----------------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def new_object(name: str, data: bpy.types.ID, collection: str = None, parent: bpy.types.Object = None):
    obj = bpy.data.objects.new(name, data)
    link_to_scene(obj, collection)
    if(parent): obj.parent = parent
    set_active(obj)
    return obj


# -----------------------------------------------------------------------------
def remove_object(obj: Object):
    bpy.data.objects.remove(obj)


# -----------------------------------------------------------------------------
def duplicate_object(obj: Object, instance = False) -> Object:
    if instance:
        mesh = obj.data
        inst = new_object(obj.name + '_INSTANCE', mesh, obj.name + '_GENERATED')
        return inst
    else:
        copy = obj.copy()
        copy.data = obj.data.copy()
        link_to_scene(copy)
        return copy


# -----------------------------------------------------------------------------
def create_mesh(
        verts: list[tuple[float, float, float]], 
        edges: list[tuple[int, int]], 
        faces: list[tuple[int, ...]], 
        name: str) -> Mesh:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, faces)
    return mesh


# -----------------------------------------------------------------------------
def remove_mesh(mesh: Mesh):
    # Extra test because this can crash Blender if not done correctly.
    result = False
    if mesh and mesh.users == 0: 
        try:
            mesh.user_clear()
            can_continue = True
        except: can_continue = False
        if can_continue == True:
            try:
                bpy.data.meshes.remove(mesh)
                result = True
            except: result = False
    else: result = True
    return result


# -----------------------------------------------------------------------------
# https://blenderartists.org/t/how-to-replace-a-mesh/596225/4
def set_mesh(obj: Object, mesh: Mesh):
    old_mesh = obj.data
    obj.data = mesh
    remove_mesh(old_mesh)


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/50160/scripting-low-level-join-meshes-elements-hopefully-with-bmesh
def join_meshes(meshes: list[Mesh]):
    bm = bmesh.new()
    bm_verts = bm.verts.new
    bm_faces = bm.faces.new
    bm_edges = bm.edges.new

    for mesh in meshes:
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
    bm.to_mesh(meshes[0])
    bm.free()
    return meshes[0]


# -----------------------------------------------------------------------------
def convert_to_mesh_in_place(obj: Object):
    set_active(obj)
    bpy.ops.object.convert(target='MESH') 


# -----------------------------------------------------------------------------
def convert_to_new_mesh(obj: Object) -> bpy.types.Object:
    mesh = bpy.data.meshes.new_from_object(obj)
    new_obj = new_object(obj.name, mesh)
    new_obj.matrix_world = obj.matrix_world 
    return new_obj


# -----------------------------------------------------------------------------
def transform(mesh: Mesh, transforms: list[Matrix]):
    mode = bpy.context.mode
    bm = bmesh.new()

    if mode == 'OBJECT':
        bm.from_mesh(mesh)
    elif mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(mesh)

    for m in transforms:
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    if mode == 'OBJECT':
        bm.to_mesh(mesh)
    elif mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(mesh)  


# -----------------------------------------------------------------------------
def snap_to_grid(mesh: Mesh,  spacing: int):
    mode = bpy.context.mode
    bm = bmesh.new()

    if mode == 'OBJECT':
        bm.from_mesh(mesh)
    elif mode == 'EDIT_MESH':
        bm = bmesh.from_edit_mesh(mesh) 

    for v in bm.verts:
        v.co.x = round(v.co.x / spacing) * spacing
        v.co.y = round(v.co.y / spacing) * spacing
        v.co.z = round(v.co.z / spacing) * spacing

    if mode == 'OBJECT':
        bm.to_mesh(mesh)
    elif mode == 'EDIT_MESH':
        bmesh.update_edit_mesh(mesh)  


# -----------------------------------------------------------------------------
# Rotation mode: 
#   https://gist.github.com/behreajj/2dbb6fb7cee78c167cd85085e67bcdf6
# Mirror rotation: 
#   https://www.gamedev.net/forums/topic/# 599824-mirroring-a-quaternion-against-the-yz-plane/
def get_rotation_mirrored_x_axis(obj: Object) -> Euler:
    prev_rot_mode = obj.rotation_mode
    obj.rotation_mode = 'QUATERNION'
    q = obj.rotation_quaternion.copy()
    q.x *= -1
    q.w *= -1
    obj.rotation_mode = prev_rot_mode
    return q.to_euler()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/159538/how-to-apply-all-transformations-to-an-object-at-low-level
def apply_all_transforms(obj: Object):
    mb = obj.matrix_basis
    if hasattr(obj.data, 'transform'):
        obj.data.transform(mb)
    for c in obj.children:
        c.matrix_local = mb @ c.matrix_local
        
    obj.matrix_basis.identity()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def set_parent(child: Object, parent: Object, keep_world_location = True):
    child.parent = parent
    if keep_world_location:
        child.matrix_parent_inverse = parent.matrix_world.inverted()


# -----------------------------------------------------------------------------
# https://blender.stackexchange.com/questions/9200/how-to-make-object-a-a-parent-of-object-b-via-blenders-python-api
def unparent(obj: Object, keep_world_location = True):
    parented_wm = obj.matrix_world.copy()
    obj.parent = None
    if keep_world_location:
        obj.matrix_world = parented_wm


# -----------------------------------------------------------------------------
# Create
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def create_cube(scale: tuple[float, float, float] = (1, 1, 1)) -> Mesh:
    verts = [
        Vector((-1 * scale[0], -1 * scale[1], -1 * scale[2])),
        Vector((-1 * scale[0],  1 * scale[1], -1 * scale[2])),
        Vector(( 1 * scale[0],  1 * scale[1], -1 * scale[2])),
        Vector(( 1 * scale[0], -1 * scale[1], -1 * scale[2])),
        Vector((-1 * scale[0], -1 * scale[1],  1 * scale[2])),
        Vector((-1 * scale[0],  1 * scale[1],  1 * scale[2])),
        Vector(( 1 * scale[0],  1 * scale[1],  1 * scale[2])),
        Vector(( 1 * scale[0], -1 * scale[1],  1 * scale[2])),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (4, 5, 1, 0),
        (7, 4, 0, 3),
        (6, 7, 3, 2),
        (5, 6, 2, 1),
    ]
    return create_mesh(verts, [], faces, 'CUBE')


# -----------------------------------------------------------------------------
def create_arrow(scale: tuple[float, float] = (1, 1)) -> Mesh:
    verts = [
        Vector((-1 * scale[0],  0.4 * scale[1], 0)),
        Vector(( 0 * scale[0],  0.4 * scale[1], 0)),
        Vector(( 0 * scale[0],  1   * scale[1], 0)), 
        Vector(( 1 * scale[0],  0   * scale[1], 0)), 
        Vector(( 0 * scale[0], -1   * scale[1], 0)), 
        Vector(( 0 * scale[0], -0.4 * scale[1], 0)),
        Vector((-1 * scale[0], -0.4 * scale[1], 0)),
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
    return create_mesh(verts, edges, [], 'ARROW')


# -----------------------------------------------------------------------------
def circle(radius, 
           location, 
           angle_step = 10) -> list[tuple[float, float, float]]:
    (a, b, c) = location

    verts = []
    for angle in range(0, 360, angle_step):
        angle_radius = math.radians(angle)
        x = a + radius * math.cos(angle_radius)
        y = b + radius * math.sin(angle_radius)
        verts.append((x, y, c))
    # Adding the first vertex as last vertex to close the loop
    verts.append(verts[0])
    return verts


# -----------------------------------------------------------------------------
def create_cylinder(radius = 2, 
                    height = 2, 
                    row_height = 1, 
                    angle_step = 10, 
                    make_faces = True) -> Mesh:
    height += 1
    verts = []
    per_circle_verts = 0

    for z in np.arange(0, height, row_height):
        c = circle(radius, (0, 0, z), angle_step)
        per_circle_verts = len(c)
        verts += c

    rows = int(height / row_height)
    faces = []

    if make_faces:
        for row in range(0, rows - 1):
            for index in range(0, per_circle_verts - 1):
                v1 = index + (row * per_circle_verts)
                v2 = v1 + 1
                v3 = v1 + per_circle_verts
                v4 = v2 + per_circle_verts
                faces.append((v1, v3, v4, v2))

    return create_mesh(verts, [], faces, 'CYLINDER')


# -----------------------------------------------------------------------------
#https://blender.stackexchange.com/questions/127603/how-to-specify-nurbs-path-vertices-in-python
def create_curve(num_points = 3, 
                 step = 1, 
                 dir: tuple[float, float, float] = (1, 0, 0)) -> bpy.types.Curve:
    curve = bpy.data.curves.new('CURVE', 'CURVE')
    path = curve.splines.new('NURBS')
    curve.dimensions = '3D'
    path.points.add(num_points - 1)

    for k in range(num_points):
        p = Vector(dir) * step * k
        path.points[k].co = (*p, 1)

    path.use_endpoint_u = True
    return curve


# -----------------------------------------------------------------------------
# Math
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def map_range(value, in_min, in_max, out_min, out_max):
    return out_min + (value - in_min) / (in_max - in_min) * (out_max - out_min)


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/45142959/calculate-rotation-matrix-to-align-two-vectors-in-3d-space 
def rotation_matrix(v1, v2):
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    v1 = [v1.x, v1.y, v1.z]
    v2 = [v2.x, v2.y, v2.z]

    a, b = (v1 / np.linalg.norm(v1)).reshape(3), (v2 / np.linalg.norm(v2)).reshape(3)
    v = np.cross(a, b)
    
    if not any(v):
        return Matrix.Identity(3)

    d = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    r = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - d) / (s ** 2))
    R = Matrix(((r[0][0], r[0][1], r[0][2], 0),
                (r[1][0], r[1][1], r[1][2], 0), 
                (r[2][0], r[2][1], r[2][2], 0), 
                (0,       0,       0,       1)))

    return R


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


    def move(self, direction):
        new_idx = self.selected_item_idx
        new_idx += direction
        self.items.move(new_idx, self.selected_item_idx)
        self.selected_item_idx = max(0, min(new_idx, len(self.items) - 1))


    def get_selected(self):
        if self.items:
            return self.items[self.selected_item_idx]
        return None


    selected_item_idx: IntProperty()


# -----------------------------------------------------------------------------
active_generic_list: GenericList

def begin_generic_list_ops(list: GenericList):
    global active_generic_list
    active_generic_list = list


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Add(Operator):
    bl_idname = 'b3d_utils.generic_list_add'
    bl_label = 'Add'
    
    list: GenericList

    def execute(self, context: Context):
        global active_generic_list
        active_generic_list.add()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Remove(Operator):
    bl_idname = 'b3d_utils.generic_list_remove'
    bl_label = 'Remove'
    bl_options = {'UNDO'}
    

    def execute(self, context: Context):
        global active_generic_list
        active_generic_list.remove_selected()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Clear(Operator):
    bl_idname = 'b3d_utils.generic_list_clear'
    bl_label = 'Clear'
    bl_options = {'UNDO'}


    def execute(self, context: Context):
        global active_generic_list
        active_generic_list.clear()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class B3D_OT_GenericList_Move(Operator):
    bl_idname = 'b3d_utils.generic_list_move'
    bl_label = 'Move Shape'
    
    direction : EnumProperty(items=(
        ('UP', 'Up', ''),
        ('DOWN', 'Down', ''),
    ))


    def execute(self, context: Context):
        dir = (-1 if self.direction == 'UP' else 1)
        global active_generic_list
        active_generic_list.move(dir)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
def draw_generic_list_ops(layout: UILayout, list: GenericList):
    begin_generic_list_ops(list)

    layout.operator(B3D_OT_GenericList_Add.bl_idname   , icon='ADD'        , text='')
    layout.operator(B3D_OT_GenericList_Remove.bl_idname, icon='REMOVE'     , text='')
    layout.operator(B3D_OT_GenericList_Move.bl_idname  , icon='TRIA_UP'    , text='').direction = 'UP'
    layout.operator(B3D_OT_GenericList_Move.bl_idname  , icon='TRIA_DOWN'  , text='').direction = 'DOWN'
    layout.operator(B3D_OT_GenericList_Clear.bl_idname , icon='TRASH'      , text='')


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
def register_subpackage(subpackage = ''):
    """
    Use empty string ('') to register root 
    """
    def get_all_submodules(directory, package_name):
        return list(iter_submodules(directory, package_name))

    def iter_submodules(path, package_name):
        for name in sorted(iter_submodule_names(path)):
            name = '.' + name
            if subpackage:
                name = '.' + subpackage + name
            yield importlib.import_module(name, package_name)

    def iter_submodule_names(path):
        import pkgutil
        for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
            if not is_package:
                yield module_name


    from pathlib import Path
    
    package = Path(__file__).parent
    path = package 
    if subpackage:
        path /= subpackage

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
