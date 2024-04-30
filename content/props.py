from bpy.types        import PropertyGroup, Object, Collection, Context, UIList
from bpy.props        import *

from random import randint

from ..b3d_utils        import GenericList
from ..dataset.movement import State
from ..dataset.dataset  import Attribute, dataset_entries


# -----------------------------------------------------------------------------
class MET_PG_Module(PropertyGroup):

    def __get_name(self):
        return State(self.state).name


    def random_object(self) -> Object | None:
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


    def update_active_states(self, _obj:Object):
        for m in self.items:
            m.active = False

        for entry in dataset_entries(_obj):
            idx = entry[Attribute.STATE.value]
            self.items[idx].active = True


    items: CollectionProperty(type=MET_PG_Module)
    initialized: BoolProperty(name='PRIVATE', default=False)


# -----------------------------------------------------------------------------
class MET_UL_Module(UIList):
    def draw_item(self, context, layout, data, item:MET_PG_Module, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'

        ic = 'RADIOBUT_OFF'
        if item.active:
            ic = 'RADIOBUT_ON'
                
        layout.label(text=item.name, icon=ic)


# -----------------------------------------------------------------------------
class MET_COLLECTION_PG_Population(PropertyGroup):
    has_content: BoolProperty(name='PRIVATE', default=False)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_modules_prop(_context:Context) -> MET_SCENE_PG_Modules:
    return _context.scene.medge_modules


# -----------------------------------------------------------------------------
def get_population_prop(_collection:Collection) -> MET_COLLECTION_PG_Population:
    return _collection.medge_population


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# BUG: We call these manually in '__init__.py' because 'auto_load' throws an AttributeError every other reload
# def register():
#    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)
#    Collection.medge_population = PointerProperty(type=MET_COLLECTION_PG_Population)


# -----------------------------------------------------------------------------
# def unregister():
#     del Collection.medge_population
#     del Scene.medge_modules
