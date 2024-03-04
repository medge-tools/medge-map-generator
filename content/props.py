from bpy.types import PropertyGroup, Object, Scene, Context
from bpy.props import *

from ..b3d_utils    import GenericList


# -----------------------------------------------------------------------------
class MET_PG_Module(PropertyGroup):
    item: PointerProperty(type=Object, name='Module')
    ignore_z_axis: BoolProperty(name='Ignore Z-Axis')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_Modules(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_Module:
        if self.items:
            return self.items[self.selected_item_idx]
        return None

    items: CollectionProperty(type=MET_PG_Module)

# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_modules(context: Context) -> MET_SCENE_PG_Modules:
    return context.scene.medge_modules


# -----------------------------------------------------------------------------
# REGISTRATION
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)


# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_modules