from bpy.types  import PropertyGroup, UIList, Collection, Context, Scene
from bpy.props  import *

from .markov    import *
from ..dataset  import props as dataset_props

# -----------------------------------------------------------------------------
markov_chain_models = {}

class MET_PG_MarkovChain(PropertyGroup):

    def create_transition_matrix(self, context: Context):
        global markov_chain_models
        mc = markov_chain_models.setdefault(self.collection.name, MarkovChain())

        objects = []
        for obj in self.collection.all_objects:
            if not dataset_props.is_dataset(obj): continue
            objects.append(obj)

        mc.create_transition_matrix(objects)

    def __on_collection_update(self, context):
        global markov_chain_models
        name = self.collection.name
        markov_chain_models.setdefault(name, MarkovChain())


    def get_name(self):
        if self.collection:
            return self.collection.name
        return ''

    name: StringProperty(name='Name', get=get_name)
    collection: PointerProperty(type=Collection, name='Collection', update=__on_collection_update)

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
