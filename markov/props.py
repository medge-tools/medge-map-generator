import bpy
from bpy.types  import PropertyGroup, Collection, Context
from bpy.props  import *

from ..b3d_utils        import GenericList
from ..dataset.props    import get_dataset
from ..dataset.movement import PlayerState, StateProperty

from .markov            import MarkovChain

# -----------------------------------------------------------------------------
markov_chain_models = {}

class MET_PG_MarkovChain(PropertyGroup):

    def data(self) -> MarkovChain:
        if self.name in markov_chain_models:
            return markov_chain_models[self.name]
        return None

    def create_transition_matrix(self, context: Context):
        if not self.collection: return

        objects = []
        for obj in self.collection.all_objects:
            if not get_dataset(obj): continue
            objects.append(obj)

        if len(objects) == 0: return

        global markov_chain_models
        mc: MarkovChain = markov_chain_models.setdefault(self.name, MarkovChain())
        mc.create_transition_matrix(objects, self.collection.name)


    def generate_chain(self, context: Context):
        global markov_chain_models

        if not self.name in markov_chain_models:
            return

        mc: MarkovChain = markov_chain_models[self.name]
        mc.generate_chain(self.length, self.seed, self.capsule_radius)


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return '[SELECT COLLECTION]'

    
    def __get_has_transition_matrix(self):
        global markov_chain_models
        return self.name in markov_chain_models
    

    def __update_statistics(self, context):
        mc: MarkovChain = markov_chain_models[self.name]
        mc.update_statistics(PlayerState[self.from_state], PlayerState[self.to_state])


    name: StringProperty('Name', get=__get_name)
    prev_name: StringProperty()
    collection: PointerProperty(type=Collection, name='Collection')
    has_transition_matrix: BoolProperty(default=False, get=__get_has_transition_matrix)

    display_statistics: BoolProperty(name='Display Statistics')
    from_state: StateProperty('From', __update_statistics)
    to_state: StateProperty('To', __update_statistics)

    length: IntProperty(name='Length', default=100)
    seed: IntProperty(name='Seed', default=2024)
    capsule_radius: FloatProperty(name='Capsule Radius', default=.5)


# -----------------------------------------------------------------------------
class MET_SCENE_PG_MarkovChains(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_MarkovChain | None:
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
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


# BUG: We call these manually in init because the auto_load throws a AttributeError every other reload
# def register():
#     bpy.types.Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)
    

# # -----------------------------------------------------------------------------
# def unregister():
#     del bpy.types.Scene.medge_markov_chains