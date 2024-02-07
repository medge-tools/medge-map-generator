from bpy.types import PropertyGroup
from bpy.props import *


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    overlay_data : BoolProperty(name='Overlay Data', default=True)


# -----------------------------------------------------------------------------
class MET_SCENE_PG_DatasetSettings(PropertyGroup):
    invoked_add_draw_handles : IntProperty(name='Invoked Add Draw Handle', default=-1)
