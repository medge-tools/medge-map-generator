from bpy.types        import PropertyGroup, Object, Collection, Context, UIList
from bpy.props        import *

from random import randint

from ..b3d_utils        import GenericList
from ..dataset.movement import State
from ..dataset.dataset  import Dataset, Attribute


# -----------------------------------------------------------------------------
class MET_PG_Module(PropertyGroup):

    def __get_name(self):
        return State(self.state).name


    def random_object(self) -> Object:
        if not self.use_collection:
            return self.object
        else:        
            n = len(self.collection.objects)
            k = randint(0, n - 1)
            return self.collection.objects[k]


    name: StringProperty(name='Name', get=__get_name)
    state: IntProperty(name='PRIVATE')
    active: BoolProperty(name='PRIVATE')

    object: PointerProperty(type=Object, name='Object')
    collection: PointerProperty(type=Collection, name='Collection')
    use_collection: BoolProperty(name='Use Collection')


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
        
        for state in State:
            module = self.add()
            module.state = state

        self.initialized = True


    def update_active_states(self, _dataset:Dataset):
        states = _dataset[:, Attribute.STATE.value]
        for m in self.items:
            m.active = False
            if m.state in states:
                m.active = True


    items: CollectionProperty(type=MET_PG_Module)
    initialized: BoolProperty(name='PRIVATE', default=False)


# -----------------------------------------------------------------------------
class MET_UL_Module(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'

        ic = 'RADIOBUT_OFF'
        if item.active:
            ic = 'RADIOBUT_ON'
                
        layout.label(text=item.name, icon=ic)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_modules_prop(_context:Context) -> MET_SCENE_PG_Modules:
    return _context.scene.medge_modules


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# BUG: We call these manually in '__init__.py' because 'auto_load' throws an AttributeError every other reload
# def register():
#    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)


# -----------------------------------------------------------------------------
# def unregister():
#     del Scene.medge_modules
