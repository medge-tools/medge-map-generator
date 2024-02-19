from bpy.types  import PropertyGroup, UIList, Collection, Context, Scene
from bpy.props  import *

from .markov    import *
from ..dataset  import props as dataset_props

# -----------------------------------------------------------------------------
markov_chain_models = {}

class MET_PG_MarkovChain(PropertyGroup):

    def create_transition_matrix(self, context: Context):
        objects = []
        for obj in self.collection.all_objects:
            if not dataset_props.is_dataset(obj): continue
            objects.append(obj)

        if len(objects) == 0: return

        global markov_chain_models
        mc: MarkovChain = markov_chain_models.setdefault(self.name, MarkovChain())
        mc.create_transition_matrix(objects)


    def generate_chain(self, context: Context):
        global markov_chain_models

        if not self.name in markov_chain_models:
            return

        mc: MarkovChain = markov_chain_models[self.name]
        mc.generate_chain(self.length, self.seed)


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return ''

    def __get_has_transition_matrix(self):
        return self.name in markov_chain_models

    name: StringProperty(name='Name', get=__get_name)
    collection: PointerProperty(type=Collection, name='Collection')
    has_transition_matrix: BoolProperty(default=False, get=__get_has_transition_matrix)
    length: IntProperty(name='Length', default=100)
    seed: IntProperty(name='Seed', default=2024)

# -----------------------------------------------------------------------------
class MET_UL_GenericList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        if self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
        layout.label(text=item.name)


# -----------------------------------------------------------------------------
class MET_SCENE_PG_MarkovChains(PropertyGroup):

    def add(self):
        self.items.add()
        self.selected_item_idx = len(self.items) - 1


    def remove_selected(self):
        self.items.remove(self.selected_item_idx)
        self.selected_item_idx = min(max(0, self.selected_item_idx - 1), len(self.items) - 1)

    
    def clear(self):
        self.items.clear()
        self.selected_item_idx = 0


    def move(self, direction):
        new_idx = self.selected_item_idx
        new_idx += direction
        self.items.move(new_idx, self.selected_item_idx)
        self.selected_item_idx = max(0, min(new_idx, len(self.items) - 1))


    def get_selected(self) -> MET_PG_MarkovChain:
        if self.items:
            return self.items[self.selected_item_idx]
        return None


    items: CollectionProperty(type=MET_PG_MarkovChain)
    selected_item_idx: IntProperty()



# -----------------------------------------------------------------------------
# SCENE UITLS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_markov_chains(context: Context) -> MET_SCENE_PG_MarkovChains:
    return context.scene.medge_markov_chains


# -----------------------------------------------------------------------------
# REGISTRATION
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)


# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_markov_chains
