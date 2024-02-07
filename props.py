from bpy.types      import PropertyGroup
from bpy.props      import *
from .dataset       import *


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    overlay_data : BoolProperty(name='Overlay Data', default=True)


class MET_SCENE_PG_DatasetSettings(PropertyGroup):
    invoked_draw_handlers: IntProperty(name='Invoked Draw Handlers')