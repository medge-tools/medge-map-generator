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


    name:               StringProperty(name='Name', get=__get_name)
    collection:         PointerProperty(type=Collection, name='Collection')

    display_statistics: BoolProperty(name='Display Statistics')
    from_state:         StateProperty('From', update_statistics)
    to_state:           StateProperty('To', update_statistics)
    
    length:             IntProperty(name='Length', default=100, min=0)
    seed:               IntProperty(name='Seed', default=2024, min=0)

    generated_chains:   PointerProperty(type=MET_PG_GeneratedChainList)
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
class MET_OBJECT_PG_Module(PropertyGroup):
    
    capsule: PointerProperty(type=Object, name='PRIVATE')


# -----------------------------------------------------------------------------
class MET_PG_ModuleGroup(PropertyGroup):

    def random_object(self) -> Object | None:
        if not self.use_collection:
            return self.object
        
        else:
            objects = self.collection.objects
            n = len(objects)
            k = randint(0, n - 1)
            return objects[k]
        

    def __get_name(self):
        name = State(self.state).name
        
        if self.use_collection:
            if self.collection:
                if not self.collection.all_objects:
                    name = '[EMPTY]_' + name
            else:
                name = '[EMPTY]_' + name
        else:
            if not self.object:
                name = '[EMPTY]_' + name

        return name


    def __on_object_poll(self, _obj:Object):
        return _obj.type == 'CURVE'


    name:   StringProperty(name='Name', get=__get_name)
    state:  IntProperty(name='PRIVATE')
    active: BoolProperty(name='PRIVATE')

    object:         PointerProperty(type=Object, name='Curve Object', poll=__on_object_poll)
    use_collection: BoolProperty(name='Use Collection')
    collection:     PointerProperty(type=Collection, name='Collection')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_ModuleGroupList(PropertyGroup, GenericList):

    # Override to define return type
    def get_selected(self) -> MET_PG_ModuleGroup:
        if self.items:
            return self.items[self.selected_item_idx]
        
        return None


    def init(self):        
        self.items.clear()
        
        for state in State:
            module = self.add()
            module.state = state


    def update_active_states(self, _gen:MET_PG_GeneratedChain):
        for m in self.items:
            m.active = False

        states = _gen.chain.split(_gen.seperator)

        for s in states:
            item = self.items[int(s)]
            item.active = True
            

    def init_capsule_data(self):
        coll_name = 'MapGeneration_CapsuleData'

        b3d_utils.remove_object(self.capsule_data)

        self.update_capsule_data()

        # Init capsule data per object
        def init(_curve:Object):
            nonlocal coll_name

            assert(_curve.type == 'CURVE')

            copy = b3d_utils.duplicate_object(self.capsule_data, True, coll_name)
            
            module = get_module_prop(_curve)

            b3d_utils.remove_object(module.capsule)

            module.capsule = copy

            copy.location = _curve.location

            b3d_utils.set_parent(copy, _curve)

            # Add modifiers
            array_mod = copy.modifiers.get('Array')

            if not array_mod:
                array_mod = copy.modifiers.new('Array', 'ARRAY')
            
            array_mod.fit_type = 'FIT_CURVE'
            array_mod.curve = _curve
            array_mod.use_relative_offset = False
            array_mod.use_constant_offset = True

            b3d_utils.add_driver(array_mod, 'constant_offset_displace', 0, bpy.context.scene, 'SCENE', 'SINGLE_PROP', 'medge_module_groups.capsule_radius')

            curve_mod = copy.modifiers.get('Curve')

            if not curve_mod:
                curve_mod = copy.modifiers.new('Curve', 'CURVE')

            curve_mod.object = _curve
            curve_mod.deform_axis = 'POS_X'


        for m in self.items:
            if m.use_collection:
                if m.collection:
                    for obj in m.collection.objects:
                        init(obj)

            elif m.object:
                init(m.object)

    def update_capsule_data(self, _dummy=None):        
        if self.capsule_radius >= (r := self.capsule_height * .5):
           self.capsule_radius = r

        h = self.capsule_height
        r = self.capsule_radius
        tip_base = h - r

        verts = [
            # Height
            Vector((0, 0, 0)),
            Vector((0, 0, h)),
            # Two horizontal edges at the base of each half sphere
            Vector((-r,  0, r)),
            Vector(( r,  0, r)),
            Vector(( 0, -r, r)),
            Vector(( 0,  r, r)),

            Vector((-r,  0, tip_base)),
            Vector(( r,  0, tip_base)),
            Vector(( 0, -r, tip_base)),
            Vector(( 0,  r, tip_base)),
        ]
        
        edges = [
            (0, 1), 
            (2, 3), (4, 5),
            (6, 7), (8, 9),
        ]
        
        cap_name = 'CapsuleColliderData'
        coll_name = 'MapGeneration_CapsuleData'

        if not self.capsule_data:
            mesh = b3d_utils.new_mesh(verts, edges, [], cap_name)
            self.capsule_data = b3d_utils.new_object(mesh, cap_name, coll_name)

        vertices = self.capsule_data.data.vertices

        for k in range(len(verts)):
            vertices[k].co = verts[k]
        

    items:              CollectionProperty(type=MET_PG_ModuleGroup)   
    capsule_data:       PointerProperty(type=Object, name='PRIVATE')
    
    seed:               IntProperty(name='Seed', default=2024, min=0)
    align_orientation:  BoolProperty(name='Align Orientation')
    resolve_collisions: BoolProperty(name='Resolve Collisions', default=True)

    capsule_height:     FloatProperty(name='Capsule Height', default=1.92, min=1, update=update_capsule_data)
    capsule_radius:     FloatProperty(name='Capsule Radius', default=.5, min=0.1, update=update_capsule_data)

    max_depth:          IntProperty(name='Max Depth', default=3)
    max_angle:          IntProperty(name='Max Angle', default=180, max=180)
    angle_step:         IntProperty(name='Angle Step', default=45, max=180)

    random_angles:      BoolProperty(name='Random Angles')
    debug_capsules:     BoolProperty(name='Debug Capsules') 


# -----------------------------------------------------------------------------
class MET_UL_ModuleList(UIList):

    def draw_item(self, context, layout, data, item:MET_PG_ModuleGroup, icon, active_data, active_property, index, flt_flag):
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
def get_markov_chains_prop(_context: Context) -> MET_SCENE_PG_MarkovChainList:
    return _context.scene.medge_markov_chains


# -----------------------------------------------------------------------------
def get_module_groups_prop(_context:Context) -> MET_SCENE_PG_ModuleGroupList:
    return _context.scene.medge_module_groups


# -----------------------------------------------------------------------------
def get_population_prop(_collection:Collection) -> MET_COLLECTION_PG_Population:
    return _collection.medge_population


# -----------------------------------------------------------------------------
def get_module_prop(_obj:Object) -> MET_OBJECT_PG_Module:
    return _obj.medge_module


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# BUG: We call these manually in '__init__.py' because 'auto_load' throws an AttributeError every other reload
def register():
   Object.medge_module         = PointerProperty(type=MET_OBJECT_PG_Module)
   Scene.medge_markov_chains   = PointerProperty(type=MET_SCENE_PG_MarkovChainList)
   Scene.medge_module_groups   = PointerProperty(type=MET_SCENE_PG_ModuleGroupList)
   Collection.medge_population = PointerProperty(type=MET_COLLECTION_PG_Population)


# -----------------------------------------------------------------------------
def unregister():
    del Collection.medge_population
    del Scene.medge_module_groups
    del Scene.medge_markov_chains
    del Object.medge_module

    