import bpy
from bpy.types import PropertyGroup, Object, Scene, Collection, Context, UIList, UILayout
from bpy.props import StringProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty, CollectionProperty
from mathutils import Vector

from random import randint

from ..                 import b3d_utils
from ..b3d_utils        import GenericList
from ..dataset.movement import State, StateProperty
from ..dataset.props    import get_dataset_prop

from .markov import MarkovChain


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
markov_chain_models:dict[str, MarkovChain] = {}


# -----------------------------------------------------------------------------
class MET_PG_GeneratedChain(PropertyGroup):
    def split(self):
        return self.chain.split(self.seperator)

    def __get_name(self):
        return self.chain


    name:      StringProperty(name='Name', get=__get_name)
    chain:     StringProperty(name='Sequence')
    seperator: StringProperty(name='Seperator', default='_')


# -----------------------------------------------------------------------------
class MET_PG_GeneratedChainList(PropertyGroup, GenericList):

    items: CollectionProperty(type=MET_PG_GeneratedChain)


# -----------------------------------------------------------------------------
class MET_PG_MarkovChain(PropertyGroup):

    def data(self) -> MarkovChain:
        if self.name in markov_chain_models:
            return markov_chain_models[self.name]
        return None


    def create_transition_matrix(self):
        if not self.collection: return

        objects = []

        for obj in self.collection.all_objects:
            if not get_dataset_prop(obj): continue
            objects.append(obj)

        if len(objects) == 0: return

        global markov_chain_models

        if self.name in markov_chain_models:
            del markov_chain_models[self.name]

        mc = MarkovChain()
        success = mc.create_transition_matrix(objects, self.name)

        if success: 
            markov_chain_models[self.name] = mc
            self.update_statistics()


    def generate_chain(self):
        global markov_chain_models

        if not self.name in markov_chain_models:
            return

        mc = markov_chain_models[self.name]
        chain = mc.generate_chain(self.length, self.seed)

        gs:MET_PG_GeneratedChain = self.generated_chains.add()
        gs.chain = gs.seperator.join(str(c) for c in chain)


    def get_selected_generated_chain(self) -> MET_PG_GeneratedChain:
        return self.generated_chains.get_selected()


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return '[SELECT COLLECTION]'

    
    def has_transition_matrix(self) -> bool:
        global markov_chain_models

        return self.name in markov_chain_models
    

    def update_statistics(self, _dummy=None):
        global markov_chain_models
        
        if self.name not in markov_chain_models: return

        mc = markov_chain_models[self.name]
        f  = State[self.from_state].value
        t  = State[self.to_state].value

        mc.update_statistics(f, t)


    def add_handmade_chain(self):
        gs:MET_PG_GeneratedChain = self.generated_chains.add()
        gs.chain = self.handmade_chain


    name:               StringProperty(name='Name', get=__get_name)
    collection:         PointerProperty(type=Collection, name='Collection')

    display_statistics: BoolProperty(name='Display Statistics')
    from_state:         StateProperty('From', update_statistics)
    to_state:           StateProperty('To', update_statistics)
    
    length:             IntProperty(name='Length', default=100, min=0)
    seed:               IntProperty(name='Seed', default=2024, min=0)

    generated_chains:   PointerProperty(type=MET_PG_GeneratedChainList)
    handmade_chain:     StringProperty(name='Handmade Chain')
    show_chain:         BoolProperty(name='Show Chain')



# -----------------------------------------------------------------------------
class MET_SCENE_PG_MarkovChainList(PropertyGroup, GenericList):

    # Override to define the return type
    def get_selected(self) -> MET_PG_MarkovChain | None:
        if self.items:
            return self.items[self.selected_item_idx]
        return None

    items: CollectionProperty(type=MET_PG_MarkovChain)
    

# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def add_volume(_obj:Object) -> Object:
    cube = b3d_utils.create_cube()
    volume = b3d_utils.new_object(cube, 'Volume', 'Modules', _obj, False)
    volume.display_type = 'WIRE'
    volume.location = _obj.location

    get_curve_module_prop(_obj).volume = volume


# -----------------------------------------------------------------------------
def create_module() -> Object:
    curve, _ = b3d_utils.create_curve()
    module = b3d_utils.new_object(curve, 'CurveModule', 'Modules')
    
    add_volume(module)

    return module


# -----------------------------------------------------------------------------
class MET_OBJECT_PG_CurveModule(PropertyGroup):

    def __on_volume_update(self, _context:Context):
        if self.volume:
            b3d_utils.set_parent(self.volume, self.id_data)


    volume: PointerProperty(type=Object, name='Volume', update=__on_volume_update)


# -----------------------------------------------------------------------------
class MET_PG_CurveModuleGroup(PropertyGroup):

    def random_module(self) -> Object | None:
        if self.use_collection:
            modules = self.collection.objects

            if not modules: return None

            k = randint(0, len(modules) - 1)
            return modules[k]
        
        else:
            return self.module
        
    
    def add_module(self):
        if self.use_collection and self.collection:
            module = create_module()
            b3d_utils.link_object_to_scene(module, self.collection)

        elif not self.module:
            self.module = create_module()


    def __get_name(self):
        name = State(self.state).name
        
        if self.use_collection:
            if self.collection:
                if not self.collection.all_objects:
                    name = '[EMPTY]_' + name
            else:
                name = '[EMPTY]_' + name
        else:
            if not self.module:
                name = '[EMPTY]_' + name

        return f'{self.state}_{name}'


    def __on_module_poll(self, _obj:Object):
        return _obj.type == 'CURVE'


    name:   StringProperty(name='Name', get=__get_name)
    state:  IntProperty(name='PRIVATE')

    module:         PointerProperty(type=Object, name='Curve Object', poll=__on_module_poll)
    use_collection: BoolProperty(name='Use Collection')
    collection:     PointerProperty(type=Collection, name='Collection')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_CurveModuleGroupList(PropertyGroup, GenericList):

    # Override to define return type
    def get_selected(self) -> MET_PG_CurveModuleGroup:
        if self.items:
            return self.items[self.selected_item_idx]
        
        return None


    def init_groups(self):        
        self.items.clear()
        
        for state in State:
            module = self.add()
            module.state = state

                    
    items:                  CollectionProperty(type=MET_PG_CurveModuleGroup)   

    seed:                   IntProperty(name='Seed', default=2024, min=0)

    align_orientation:      BoolProperty(name='Align Orientation')
    resolve_volume_overlap: BoolProperty(name='Resolve Overlap', default=True)

    max_depth:              IntProperty(name='Max Depth', default=3)
    max_angle:              IntProperty(name='Max Angle', default=180, max=180)
    angle_step:             IntProperty(name='Angle Step', default=45, max=180)
     
    random_angles:          BoolProperty(name='Random Angles')


# -----------------------------------------------------------------------------
class MET_UL_CurveModuleGroupList(UIList):

    def draw_item(self, _context, _layout, _data, _item:MET_PG_CurveModuleGroup, _icon, _active_data, _active_property, _index, _flt_flag):
        if self.layout_type == 'GRID':
            _layout.alignment = 'CENTER'

        mc = get_markov_chains_prop(_context).get_selected()
        gen_chain = mc.get_selected_generated_chain()
        states = set(gen_chain.split())
        
        ic = 'RADIOBUT_OFF'
        if str(_item.state) in states:
            ic = 'RADIOBUT_ON'

        _layout.label(text=_item.name, icon=ic)


    def draw_filter(self, _context:Context|None, _layout:UILayout):
        _layout.separator() 
        col = _layout.column(align=True) 
        col.prop(self, 'filter_gen_chain', text='', icon='RADIOBUT_ON') 


    def filter_items(self, _context:Context|None, _data, _property:str):
        items = getattr(_data, _property) 
        filtered = []

        if self.filter_gen_chain:
            filtered = [0] * len(items)
            
            mc = get_markov_chains_prop(_context).get_selected()
            gen_chain = mc.get_selected_generated_chain()

            states = set(gen_chain.split())

            for s in states:
                filtered[int(s)] = self.bitflag_filter_item
        
        return filtered, []


    filter_gen_chain: BoolProperty(name='Filter Generated Chain')


# -----------------------------------------------------------------------------
class MET_COLLECTION_PG_GeneratedMap(PropertyGroup):

    has_content: BoolProperty(name='PRIVATE', default=False)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_markov_chains_prop(_context: Context) -> MET_SCENE_PG_MarkovChainList:
    return _context.scene.medge_markov_chains


# -----------------------------------------------------------------------------
def get_curve_module_prop(_obj:Object) -> MET_OBJECT_PG_CurveModule:
    return _obj.medge_curve_module


# -----------------------------------------------------------------------------
def get_curve_module_groups_prop(_context:Context) -> MET_SCENE_PG_CurveModuleGroupList:
    return _context.scene.medge_curve_module_groups


# -----------------------------------------------------------------------------
def get_population_prop(_collection:Collection) -> MET_COLLECTION_PG_GeneratedMap:
    return _collection.medge_generated_map


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# BUG: We call these manually in '__init__.py' because 'auto_load' throws an AttributeError every other reload
def register():
   Object.medge_curve_module       = PointerProperty(type=MET_OBJECT_PG_CurveModule)
   Scene.medge_markov_chains       = PointerProperty(type=MET_SCENE_PG_MarkovChainList)
   Scene.medge_curve_module_groups = PointerProperty(type=MET_SCENE_PG_CurveModuleGroupList)
   Collection.medge_generated_map  = PointerProperty(type=MET_COLLECTION_PG_GeneratedMap)


# -----------------------------------------------------------------------------
def unregister():
    del Collection.medge_generated_map
    del Scene.medge_curve_module_groups
    del Scene.medge_markov_chains
    del Object.medge_curve_module

    