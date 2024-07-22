from bpy.types import Operator, Context, Object, PropertyGroup, Scene, Collection, Context, Panel
from bpy.props import StringProperty, PointerProperty, BoolProperty, IntProperty, CollectionProperty

import numpy as np

from ..b3d_utils import GenericList, draw_generic_list, multiline_text, draw_box
from .gui        import MEdgeToolsPanel, GenerateTab
from .dataset    import is_dataset, dataset_sequences, get_dataset_prop, update_attributes
from .movement   import State


# -----------------------------------------------------------------------------
class MarkovChain:
    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.nstates = 0


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, _objects:list[Object], _name='') -> bool:
        self.name = _name

        self.nstates = 0
        transitions:list[list] = []

        # Collect all states
        for obj in _objects:
            if not is_dataset(obj): continue

            update_attributes(obj)

            states = []

            for state, _ in dataset_sequences(obj):
                self.nstates = max(self.nstates, state)
                states.append(state)

            transitions.append(states.copy())
            
        if len(transitions) == 0: return False

        self.nstates += 1
        self.transition_matrix = np.zeros((self.nstates, self.nstates), dtype=float)

        # Populate transition matrix
        # Instead of going through each vertex, we group 
        for sequence in transitions:
            for s1, s2 in zip(sequence, sequence[1:]):
                self.transition_matrix[s1][s2] += 1.0

        # Normalize 
        for row in self.transition_matrix:
            if (s := sum(row)) > 0: 
                factor = 1.0 / s
                row[:] = [float(v) * factor for v in row]

        return True


    def generate_chain(self, _length:int, _seed:int) -> list[int]:
        # Prepare chain generation
        np.random.seed(_seed)

        start_state = State.Walking.value
        prev_state = start_state

        gen_chain = [prev_state]
        
        for _ in range(1, _length, 1):
            # Choose the next state
            probabilities = self.transition_matrix[prev_state]
            next_state = np.random.choice(self.nstates, p=probabilities)

            gen_chain.append(next_state)

            # Prepare for next iteration
            prev_state = next_state

        return gen_chain

# -----------------------------------------------------------------------------
# PropertyGroups
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
markov_chain_models:dict[str, MarkovChain] = {}


# -----------------------------------------------------------------------------
class MET_PG_generated_chain(PropertyGroup):
    def split(self):
        return self.chain.split(self.seperator)

    def __get_name(self):
        return self.chain


    name:      StringProperty(name='Name', get=__get_name)
    chain:     StringProperty(name='Sequence')
    seperator: StringProperty(name='Seperator', default='_')


# -----------------------------------------------------------------------------
class MET_PG_generated_chain_list(PropertyGroup, GenericList):

    items: CollectionProperty(type=MET_PG_generated_chain)


# -----------------------------------------------------------------------------
class MET_PG_markov_chain(PropertyGroup):

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


    def generate_chain(self):
        global markov_chain_models

        if not self.name in markov_chain_models:
            return

        mc = markov_chain_models[self.name]
        chain = mc.generate_chain(self.length, self.seed)

        gs:MET_PG_generated_chain = self.generated_chains.add()
        gs.chain = gs.seperator.join(str(c) for c in chain)


    def get_selected_generated_chain(self) -> MET_PG_generated_chain:
        return self.generated_chains.get_selected()


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return '[SELECT COLLECTION]'

    
    def has_transition_matrix(self) -> bool:
        global markov_chain_models

        return self.name in markov_chain_models
    

    def add_handmade_chain(self):
        gs:MET_PG_generated_chain = self.generated_chains.add()
        gs.chain = self.handmade_chain


    name:               StringProperty(name='Name', get=__get_name)
    collection:         PointerProperty(type=Collection, name='Collection')

    length:             IntProperty(name='Length', default=100, min=0)
    seed:               IntProperty(name='Seed', default=2024, min=0)

    generated_chains:   PointerProperty(type=MET_PG_generated_chain_list)
    handmade_chain:     StringProperty(name='Handmade Chain')
    show_chain:         BoolProperty(name='Show Chain')



# -----------------------------------------------------------------------------
class MET_SCENE_PG_markov_chain_list(PropertyGroup, GenericList):

    # Override to define the return type
    def get_selected(self) -> MET_PG_markov_chain | None:
        if self.items:
            return self.items[self.selected_item_idx]
        return None

    items: CollectionProperty(type=MET_PG_markov_chain)
    

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_create_transition_matrix(Operator):
    bl_idname = 'medge_generate.create_transition_matrix'
    bl_label  = 'Create Transition Matrix'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        cls.bl_label = 'Create Transition Matrix'

        if item.has_transition_matrix():
            cls.bl_label = 'Update Transition Matrix'

        return True


    def execute(self, _context:Context):
        markov_chains = get_markov_chains_prop(_context)
        item = markov_chains.get_selected()
        item.create_transition_matrix()

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_generate_chain(Operator):
    bl_idname = 'medge_generate.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        return item.has_transition_matrix()


    def execute(self, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        item.generate_chain()

        return {'FINISHED'}  


# -----------------------------------------------------------------------------
class MET_OT_add_handmade_chain(Operator):
    bl_idname = 'medge_generate.add_handmade_chain'
    bl_label  = 'Add Handmade Chain'


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        mc.get_selected().add_handmade_chain()
        
        return {'FINISHED'}    
    

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_markov_chains_data(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Markov Data'
    

    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)

        draw_generic_list(col, markov_chains, '#markov_chain_list')

        mc = markov_chains.get_selected()

        if not mc: return

        col = layout.column(align=True)
        col.prop(mc, 'collection')

        col.separator(factor=2)

        col.operator(MET_OT_create_transition_matrix.bl_idname, text=MET_OT_create_transition_matrix.bl_label)

        col.separator(factor=2)
        if mc.has_transition_matrix():
            col.prop(mc, 'length')
            col.prop(mc, 'seed')

            col.separator()
            col.operator(MET_OT_generate_chain.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_markov_chains_generate(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Generated Chains'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)
        mc = markov_chains.get_selected()

        if not mc: 
            draw_box(col, 'No Markov Data')
            return

        gen_chains = mc.generated_chains

        draw_generic_list(col, gen_chains, '#generated_chain_list', 3, {'REMOVE', 'MOVE', 'CLEAR'})

        col.separator()
        row = col.row(align=True)
        row.prop(mc, 'handmade_chain')
        row.operator(MET_OT_add_handmade_chain.bl_idname, text='', icon='ADD')

        active_chain = gen_chains.get_selected()

        if not active_chain: return

        col.separator()
        col.prop(mc, 'show_chain', expand=True)

        if mc.show_chain:
            col.separator(factor=2)
            multiline_text(_context, col, active_chain.chain)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_markov_chains_prop(_context: Context) -> MET_SCENE_PG_markov_chain_list:
    return _context.scene.medge_markov_chains


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_markov_chain_list)


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_markov_chains'): del Scene.medge_markov_chains