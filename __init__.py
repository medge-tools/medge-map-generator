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
import bpy
from bpy.props import PointerProperty
from .markov.props import MET_SCENE_PG_MarkovChains

from .b3d_utils import register_subpackage, unregister_subpackages


# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')
    register_subpackage('markov')
    register_subpackage('content')

    bpy.types.Scene.medge_markov_chains = PointerProperty(type=MET_SCENE_PG_MarkovChains)


# -----------------------------------------------------------------------------
def unregister():
    # Temp solution during development
    del bpy.types.Scene.medge_markov_chains

    unregister_subpackages()
