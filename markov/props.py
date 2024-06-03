from bpy.types import PropertyGroup, Collection, Context
from bpy.props import StringProperty, PointerProperty, BoolProperty, IntProperty, FloatProperty, CollectionProperty

from ..b3d_utils        import GenericList
from ..dataset.props    import get_dataset_prop
from ..dataset.movement import State, StateProperty

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

        settings = GenChainSettings()
        settings.length             = self.length 
        settings.seed               = self.seed 
        settings.collision_radius   = self.collision_radius
        settings.collision_height   = self.collision_height
        settings.max_depth          = self.max_depth
        settings.max_angle          = self.max_angle
        settings.angle_step         = self.angle_step
        settings.align_orientation  = self.align_orientation
        settings.resolve_collisions = self.resolve_collisions
        settings.random_angles      = self.random_angles
        settings.random_mirror      = self.random_mirror
        settings.debug_capsules     = self.debug_capsules

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
        f = State[self.from_state].value
        t = State[self.to_state].value

        mc.update_statistics(f, t)


    name:       StringProperty(name='Name', get=__get_name)
    collection: PointerProperty(type=Collection, name='Collection')

    display_statistics: BoolProperty(name='Display Statistics')
    from_state:         StateProperty('From', update_statistics)
    to_state:           StateProperty('To', update_statistics)
    
    length:             IntProperty(name='Length', default=100, min=0)
    seed:               IntProperty(name='Seed', default=2024, min=0)
    collision_height:   FloatProperty(name='Collision Height', default=1.92, min=1)
    collision_radius:   FloatProperty(name='Collision Radius', default=.5, min=0)
    max_depth:          IntProperty(name='Max Depth', default=3)
    max_angle:          IntProperty(name='Max Angle', default=180, max=180)
    angle_step:         IntProperty(name='Angle Step', default=45, max=180)
    align_orientation:  BoolProperty(name='Align Orientation')
    resolve_collisions: BoolProperty(name='Resolve Collisions', default=True)
    random_angles:      BoolProperty(name='Random Angles')
    random_mirror:      BoolProperty(name='Random Mirror')
    debug_capsules:     BoolProperty(name='Debug Capsules')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_MarkovChains(PropertyGroup, GenericList):

    def get_selected(self) -> MET_PG_MarkovChain | None:
        if self.items:
            return self.items[self.selected_item_idx]
        return None

    items: CollectionProperty(type=MET_PG_MarkovChain)
    

# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_markov_chains_prop(context: Context) -> MET_SCENE_PG_MarkovChains:
    return context.scene.medge_markov_chains


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# BUG: We call these manually in '__init__.py' because 'auto_load' throws an AttributeError every other reload
# def register():
#     bpy.types.Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)

# -----------------------------------------------------------------------------
# def unregister():
#     del bpy.types.Scene.medge_markov_chains
    