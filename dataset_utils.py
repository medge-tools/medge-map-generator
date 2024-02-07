import bmesh
from bpy.types import Object, Context
from .props import *


# -----------------------------------------------------------------------------
def get_medge_dataset(obj: Object) -> MET_MESH_PG_Dataset:
    return obj.data.medge_dataset


# -----------------------------------------------------------------------------
def get_medge_dataset_settings(context: Context) -> MET_SCENE_PG_DatasetSettings:
    return context.scene.medge_dataset_settings


# -----------------------------------------------------------------------------
def get_attributes(obj: Object, attr_name: str, attr_type: str):
    mesh = obj.data
    if obj.mode == 'OBJECT':
        bm = bmesh.new()
        bm.from_mesh(mesh)
    elif obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(mesh)

    layer = bm.verts.layers.__getattribute__(attr_type).get(attr_name)
    attributes = [vert[layer] for vert in bm.verts]
    
    bm.free()

    return attributes


    #bm.attributes[attr_name].data.foreach_get(attr_type, container)
