from bpy.types      import PropertyGroup, Object, Mesh, Context
from bpy.props      import *

from .movement      import StateProperty


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
class MET_MESH_PG_Dataset(PropertyGroup):
    def get_vis_settings(self) -> MET_DS_PG_VisSettings:
        return self.vis_settings


    is_dataset:     BoolProperty(default=False)
    vis_settings:   PointerProperty(type=MET_DS_PG_VisSettings)
    
    use_filter:     BoolProperty(name='Use Filter')
    filter:         StringProperty(name='Filter', description='List of [str | int] seperated by a comma')
    
    new_state:      StateProperty()
    
    spacing:        FloatProperty(name='Spacing', default=2)


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
datavis_is_enabled = False

def is_datavis_enabled(context: Context):
    global datavis_is_enabled
    return datavis_is_enabled


# -----------------------------------------------------------------------------
def set_datavis_enabeld(context: Context, state: bool):
    global datavis_is_enabled
    datavis_is_enabled = state


# -----------------------------------------------------------------------------
# REGISTRATION
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Mesh.medge_dataset = PointerProperty(type=MET_MESH_PG_Dataset)


# -----------------------------------------------------------------------------
def unregister():
    del Mesh.medge_dataset
