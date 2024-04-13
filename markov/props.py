from bpy.types  import PropertyGroup, Collection, Context
from bpy.props  import *

from ..b3d_utils        import GenericList
from ..dataset.props    import get_dataset
from ..dataset.movement import PlayerState, PlayerStateProperty

from .markov import MarkovChain
from .chains import GenChainSettings

# -----------------------------------------------------------------------------
markov_chain_models = {}


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
            if not get_dataset(obj): continue
            objects.append(obj)

        if len(objects) == 0: return

        global markov_chain_models

        if self.name in markov_chain_models:
            del markov_chain_models[self.name]

        mc = MarkovChain()
        success = mc.create_transition_matrix(objects, 1, self.name)

        if success: 
            markov_chain_models[self.name] = mc
            self.update_statistics()


    def generate_chain(self):
        global markov_chain_models

        if not self.name in markov_chain_models:
            return

        settings = GenChainSettings()
        settings.length                 = self.length 
        settings.seed                   = self.seed 
        settings.aabb_margin            = self.aabb_margin
        settings.collision_radius       = self.collision_radius
        settings.angle_step             = self.angle_step
        settings.max_resolve_iterations = self.max_resolve_iterations
        settings.align_orientation      = self.align_orientation

        mc = markov_chain_models[self.name]
        mc.generate_chain(settings)


    def __get_name(self):
        if self.collection:
            return self.collection.name
        return '[SELECT COLLECTION]'

    
    def has_transition_matrix(self) -> bool:
        global markov_chain_models
        return self.name in markov_chain_models
    

    def update_statistics(self, _context=None):
        global markov_chain_models
        if self.name not in markov_chain_models: return

        mc = markov_chain_models[self.name]
        f = PlayerState[self.from_state].value
        t = PlayerState[self.to_state].value
        mc.update_statistics(f, t)


    name: StringProperty(name='Name', get=__get_name)
    collection: PointerProperty(type=Collection, name='Collection')

    display_statistics: BoolProperty(name='Display Statistics')
    from_state: PlayerStateProperty('From', update_statistics)
    to_state: PlayerStateProperty('To', update_statistics)
    
    min_chain_length: IntProperty(name='Min Chain Length', default=5, min=1)

    length: IntProperty(name='Length', default=100, min=0)
    seed: IntProperty(name='Seed', default=2024, min=0)
    aabb_margin: FloatProperty(name='AABB margin', default=0, min=0)
    collision_radius: FloatProperty(name='Collision Radius', default=.5, min=0)
    angle_step: IntProperty(name='Angle Step', default=5, min=1)
    align_orientation: BoolProperty(name='Align Orientation')
    max_resolve_iterations: IntProperty(name='Max Resolve Iterations', default=-1, min=-1)

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
# BUG: We call these manually in init because the auto_load throws an AttributeError every other reload
# def register():
#     bpy.types.Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)

# -----------------------------------------------------------------------------
# def unregister():
#     del bpy.types.Scene.
    