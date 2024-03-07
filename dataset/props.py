from bpy.types      import PropertyGroup, Object, Mesh, Context
from bpy.props      import *

from .movement      import StateProperty
from .dataset       import DatasetOps

# -----------------------------------------------------------------------------
class MET_DS_PG_VisSettings(PropertyGroup):
    to_name:            BoolProperty(name='To Name', default=False)
    only_selection:     BoolProperty(name='Only Selection', default=False)
    show_timestamps:    BoolProperty(name='Show Timestamps', default=False)
    min_draw_distance:  FloatProperty(name='Min Draw Distance', subtype='DISTANCE', default=50)
    max_draw_distance:  FloatProperty(name='Max Draw Distance', subtype='DISTANCE', default=100)
    color:              FloatVectorProperty(name='Color', subtype='COLOR_GAMMA', default=(.9, .9, .9))
    font_size :         IntProperty(name='Font Size', default=13)


# -----------------------------------------------------------------------------
class MET_DS_PG_OpsSettings(PropertyGroup):
    use_filter:     BoolProperty(name='Use Filter')
    restrict:       BoolProperty(name='Restrict')
    filter:         StringProperty(name='Filter', description='List of [str | int] seperated by a comma')

    new_state:      StateProperty()
    spacing:        FloatProperty(name='Spacing', default=2)


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    def get_vis_settings(self) -> MET_DS_PG_VisSettings:
        return self.vis_settings

    def get_ops_settings(self) -> MET_DS_PG_OpsSettings:
        return self.ops_settings

    def __get_is_dataset(self):
        return DatasetOps.is_dataset(self.id_data)

    is_dataset:     BoolProperty(default=False, get=__get_is_dataset)
    vis_settings:   PointerProperty(type=MET_DS_PG_VisSettings)
    ops_settings:   PointerProperty(type=MET_DS_PG_OpsSettings)

    
# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_dataset(obj: Object) -> MET_MESH_PG_Dataset:
    dataset = obj.data.medge_dataset
    if dataset.is_dataset:
        return obj.data.medge_dataset
    return None


# -----------------------------------------------------------------------------
# REGISTRATION
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Mesh.medge_dataset = PointerProperty(type=MET_MESH_PG_Dataset)


# -----------------------------------------------------------------------------
def unregister():
    del Mesh.medge_dataset
