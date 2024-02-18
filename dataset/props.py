from bpy.types      import PropertyGroup, Object, Mesh, Scene
from bpy.props      import *

from .logdata       import *


# -----------------------------------------------------------------------------
class MET_DS_PG_VisSettings(PropertyGroup):

    overlay_data: BoolProperty(name='Overlay Data', default=True)
    to_name: BoolProperty(name='To Name', default=True)
    only_selection: BoolProperty(name='Only Selection', default=False)
    show_timestamps: BoolProperty(name='Show Timestamps', default=False)

    font_size : IntProperty(name='Font Size', default=13)


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    is_dataset: BoolProperty(default=False)
    vis_settings : PointerProperty(type=MET_DS_PG_VisSettings)



# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_dataset(obj: Object) -> MET_MESH_PG_Dataset:
    return obj.data.medge_dataset


# -----------------------------------------------------------------------------
def is_dataset(obj: Object):
    if obj.type != 'MESH': return False
    return get_dataset(obj).is_dataset


# -----------------------------------------------------------------------------
def is_datavis_enabled(context: Context):
    return context.scene.medge_datavis_enabled


# -----------------------------------------------------------------------------
def set_datavis_enabeld(context: Context, state: bool):
    context.scene.medge_datavis_enabled = state

# -----------------------------------------------------------------------------
# REGISTRATION
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Mesh.medge_dataset = PointerProperty(type=MET_MESH_PG_Dataset)
    Scene.medge_datavis_enabled = BoolProperty(default=False)


# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_datavis_enabled
    del Mesh.medge_dataset
