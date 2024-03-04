from bpy.types  import PropertyGroup, Collection, Context, Scene
from bpy.props  import *

from .markov            import *
from ..dataset.props    import is_dataset
from ..b3d_utils        import GenericList

# -----------------------------------------------------------------------------
markov_chain_models = {}

class MET_PG_MarkovChain(PropertyGroup):

    def create_transition_matrix(self, context: Context):
        objects = []
        for obj in self.collection.all_objects:
            if not is_dataset(obj): continue
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
        mc.generate_chain(self.length, self.seed, self.spacing)


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return '[SELECT COLLECTION]'

    def __get_has_transition_matrix(self):
        return self.name in markov_chain_models

    name: StringProperty(name='Name', get=__get_name)
    collection: PointerProperty(type=Collection, name='Collection')
    has_transition_matrix: BoolProperty(default=False, get=__get_has_transition_matrix)
    length: IntProperty(name='Length', default=100)
    seed: IntProperty(name='Seed', default=2024)
    spacing: FloatProperty(name='Spacing', default=2, min=1)


# -----------------------------------------------------------------------------
class MET_SCENE_PG_MarkovChains(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_MarkovChain:
        if self.items:
            return self.items[self.selected_item_idx]
        return None


    items: CollectionProperty(type=MET_PG_MarkovChain)
    

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
