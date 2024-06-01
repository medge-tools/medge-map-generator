from bpy.types import PropertyGroup, Object, Collection, Context, UIList, UILayout
from bpy.props import *

from random import randint

from ..b3d_utils        import GenericList
from ..dataset.movement import State
from ..dataset.dataset  import Attribute, dataset_entries


# -----------------------------------------------------------------------------
class MET_OBJECT_PG_Module(PropertyGroup):

    can_overextend: BoolProperty(name='Can Overextend', default=True)
    curve_deform:   BoolProperty(name='Curve Deform',   description='Mesh will be deform by curve modifier in the xy-plane')
    curve_deform_z: BoolProperty(name='Curve Deform Z', description='Mesh will also be deformed in the z-axis')

# -----------------------------------------------------------------------------
class MET_PG_ModuleState(PropertyGroup):

    def __get_name(self):
        return State(self.state).name


    def random_object(self) -> Object | None:
        if not self.use_collection:
            return self.object
        
        else:
            objects = self.collection.objects
            n = len(objects)
            k = randint(0, n - 1)
            return objects[k]


    name:   StringProperty(name='Name', get=__get_name)
    state:  IntProperty(name='PRIVATE')
    active: BoolProperty(name='PRIVATE')

    object:              PointerProperty(type=Object, name='Object')
    only_at_chain_start: BoolProperty(name='Only At Chain Start')
    use_collection:      BoolProperty(name='Use Collection')
    collection:          PointerProperty(type=Collection, name='Collection')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_ModuleStates(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_ModuleState:
        if self.items:
            return self.items[self.selected_item_idx]
        
        return None


    def init(self):        
        self.items.clear()
        
        for state in State:
            module = self.add()
            module.state = state


    def update_active_states(self, _obj:Object):
        for m in self.items:
            m.active = False

        for entry in dataset_entries(_obj):
            idx = entry[Attribute.STATE.value]
            item = self.items[idx]
            item.active = True
            

    items: CollectionProperty(type=MET_PG_ModuleState)    


# -----------------------------------------------------------------------------
class MET_UL_ModuleList(UIList):

    def draw_item(self, context, layout, data, item:MET_PG_ModuleState, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'

        ic = 'RADIOBUT_OFF'
        if item.active:
            ic = 'RADIOBUT_ON'
    
        layout.label(text=item.name, icon=ic)


    def draw_filter(self, _context:Context|None, _layout:UILayout):
        _layout.separator() 
        col = _layout.column(align=True) 
        col.prop(self, 'filter_active', text='', icon='RADIOBUT_ON') 


    def filter_items(self, _context:Context|None, _data, _property:str):
        items = getattr(_data, _property) 
        filtered = [self.bitflag_filter_item] * len(items)
        
        if self.filter_active:
            for k, item in enumerate(items):
                if item.active: continue
                filtered[k] &= ~self.bitflag_filter_item
        
        return filtered, []


    filter_active: BoolProperty(name='Filter Active')


# -----------------------------------------------------------------------------
class MET_COLLECTION_PG_Population(PropertyGroup):
    has_content: BoolProperty(name='PRIVATE', default=False)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_module_prop(_obj:Object) -> MET_OBJECT_PG_Module:
    return _obj.medge_module


# -----------------------------------------------------------------------------
def get_module_states_prop(_context:Context) -> MET_SCENE_PG_ModuleStates:
    return _context.scene.medge_module_states


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
#    Object.medge_module = PointerProperty(type=MET_OBJECT_PG_Module)


# -----------------------------------------------------------------------------
# def unregister():
#     del Object.medge_module
#     del Collection.medge_population
#     del Scene.medge_modules
