bl_info = {
    'name' : 'Map Generator',
    'author' : 'Tariq Bakhtali (didibib)',
    'description' : '',
    'blender' : (3, 4, 0),
    'version' : (1, 0, 0),
    'location' : '',
    'warning' : '',
    'category' : 'MEdge Tools'
}


# -----------------------------------------------------------------------------
from bpy.types import Scene, Mesh, Collection, Object
from bpy.props import PointerProperty

from .b3d_utils     import register_subpackage, unregister_subpackages

from .dataset.props import MET_MESH_PG_Dataset
from .markov.props  import MET_SCENE_PG_MarkovChains
from .content.props import MET_SCENE_PG_ModuleStates, MET_COLLECTION_PG_Population, MET_OBJECT_PG_ModuleSettings


# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')
    register_subpackage('markov')
    register_subpackage('content')

    Mesh.medge_dataset          = PointerProperty(type=MET_MESH_PG_Dataset)
    Scene.medge_markov_chains   = PointerProperty(type=MET_SCENE_PG_MarkovChains)
    Scene.medge_module_states   = PointerProperty(type=MET_SCENE_PG_ModuleStates)
    Collection.medge_population = PointerProperty(type=MET_COLLECTION_PG_Population)
    Object.medge_module         = PointerProperty(type=MET_OBJECT_PG_ModuleSettings)


# -----------------------------------------------------------------------------
def unregister():
    del Object.medge_module
    del Collection.medge_population
    del Scene.medge_module_states
    del Scene.medge_markov_chains
    del Mesh.medge_dataset

    unregister_subpackages()
