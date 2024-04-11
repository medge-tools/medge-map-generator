from bpy.types import PropertyGroup, Object, Scene, Context, UIList
from bpy.props import *

from ..b3d_utils        import GenericList
from ..dataset.movement import PlayerState


# -----------------------------------------------------------------------------
class MET_PG_Module(PropertyGroup):

    def __get_name(self):
        return PlayerState(self.state).name

    name: StringProperty(name='Name', get=__get_name)
    active: BoolProperty(name='Active', default=False)
    state: IntProperty()
    object: PointerProperty(type=Object, name='Object')
    ignore_z_axis: BoolProperty(name='Ignore Z-Axis')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_Modules(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_Module:
        self.init()

        if self.items:
            return self.items[self.selected_item_idx]
        return None
    

    def init(self):
        if self.initialized: return
        
        self.items.clear()
        
        for state in PlayerState:
            module = self.add()
            module.state = state

        self.initialized = True


    def to_list(self):
        return [item.object for item in self.items]


    items: CollectionProperty(type=MET_PG_Module)
    initialized: BoolProperty(default=False)


# -----------------------------------------------------------------------------
class MET_UL_Module(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
        layout.label(text=item.name)


# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_modules(_context:Context) -> MET_SCENE_PG_Modules:
    return _context.scene.medge_modules


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)

# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_modules
