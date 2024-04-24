bl_info = {
    "name" : "Map Generator",
    "author" : "Tariq Bakhtali (didibib)",
    "description" : "",
    "blender" : (3, 4, 0),
    "version" : (1, 0, 0),
    "location" : "",
    "warning" : "",
    "category" : "MEdge Tools"
}


# -----------------------------------------------------------------------------
from bpy.types import Scene
from bpy.props import PointerProperty

from .b3d_utils     import register_subpackage, unregister_subpackages
from .markov.props  import MET_SCENE_PG_MarkovChains
from .content.props import MET_SCENE_PG_Modules


# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')
    register_subpackage('markov')
    register_subpackage('content')

    Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)
    Scene.medge_modules = PointerProperty(type=MET_SCENE_PG_Modules)


# -----------------------------------------------------------------------------
def unregister():
    del Scene.medge_modules
    del Scene.medge_markov_chains

    unregister_subpackages()
