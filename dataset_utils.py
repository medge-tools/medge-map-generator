import bpy
from .props import *


def get_medge_dataset(obj: bpy.types.Object) -> MET_MESH_PG_Dataset:
    return obj.data.medge_dataset


def get_medge_dataset_settings(scene: bpy.types.Scene) -> MET_SCENE_PG_DatasetSettings:
    return scene.medge_dataset_settings