import bpy
from bpy.types import Object
from mathutils import Vector, Matrix, Euler
import bmesh
import math
import numpy as np

# =============================================================================
# HELPERS
# -----------------------------------------------------------------------------
# =============================================================================
def set_active(obj: Object) -> None:
    active = bpy.context.active_object
    if active: active.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


# =============================================================================
def set_obj_mode(obj: Object, m = 'OBJECT') -> None:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode=m)


# =============================================================================
def set_obj_selectable(obj: Object, select: bool) -> None:
    obj.hide_select = not select


# =============================================================================
def select_obj(obj: Object):
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# =============================================================================
def select_all() -> None:
    for obj in bpy.context.scene.objects:
        select_obj(obj)


# =============================================================================
def deselect_all() -> None:
    for obj in bpy.context.selected_objects:
        obj.select_set(False)


# =============================================================================
def link_to_scene(obj: Object, collection: str = None) -> None:
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


# =============================================================================
def auto_gui_properties(data, layout: bpy.types.UILayout):
    for key in data.__annotations__.keys():
        layout.prop(data, key)


# =============================================================================
# HANDLER CALLBACK
# -----------------------------------------------------------------------------
# =============================================================================
def add_callback(handler, function) -> None:
    for fn in handler:
        if fn.__name__ == function.__name__: return
    handler.append(function)


# =============================================================================
def remove_callback(handler, function) -> None:
    for fn in handler:
        if fn.__name__ == function.__name__:
            handler.remove(fn)


# =============================================================================
# SCENE
# -----------------------------------------------------------------------------
# =============================================================================
def new_object(name: str, data: bpy.types.ID, collection: str = None, parent: bpy.types.Object = None) -> None:
    obj = bpy.data.objects.new(name, data)
    link_to_scene(obj, collection)
    if(parent): obj.parent = parent
    set_active(obj)
    return obj


# =============================================================================
def remove_object(obj: Object) -> None:
    bpy.data.objects.remove(obj)


# =============================================================================
def copy_object(obj: Object) -> bpy.types.Object:
    copy = obj.copy()
    copy.data = obj.data.copy()
    link_to_scene(copy)
    return copy


# =============================================================================
def create_mesh(
        verts: list[tuple[float, float, float]], 
        edges: list[tuple[int, int]], 
        faces: list[tuple[int, ...]], 
        name: str) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, faces)
    return mesh


# =============================================================================
def unpack(packed: list[Vector]):
    unpacked = [0] * len(packed) * 3

    for k in range(len(packed)): 
        unpacked[k * 3 + 0] = packed[k].x
        unpacked[k * 3 + 1] = packed[k].y
        unpacked[k * 3 + 2] = packed[k].z

    return unpacked