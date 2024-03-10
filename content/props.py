from bpy.types import PropertyGroup, Object, Scene, Context, UIList
from bpy.props import *

from ..b3d_utils        import GenericList
from ..dataset.movement import State


classes = []

# -----------------------------------------------------------------------------
class MET_PG_Module(PropertyGroup):

    def __get_name(self):
        return State(self.state).name

    name: StringProperty(name='Name', get=__get_name)
    active: BoolProperty(name='Active', default=False)
    state: IntProperty()
    object: PointerProperty(type=Object, name='Object')
    ignore_z_axis: BoolProperty(name='Ignore Z-Axis')

classes.append(MET_PG_Module)


# -----------------------------------------------------------------------------
class MET_SCENE_PG_Modules(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_Module:
        if self.items:
            return self.items[self.selected_item_idx]
        return None
    
    def init(self):
        self.items.clear()
        
        for state in State:
            module = self.add()
            module.state = state

        self.initialized = True

    def to_list(self):
        return [item.object for item in self.items]

    items: CollectionProperty(type=MET_PG_Module)
    initialized: BoolProperty(default=False)

classes.append(MET_SCENE_PG_Modules)


# -----------------------------------------------------------------------------
class MET_UL_Module(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
        layout.label(text=item.name)

classes.append(MET_UL_Module)


# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_modules(context: Context) -> MET_SCENE_PG_Modules:
    return context.scene.medge_modules


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)

# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_modules
