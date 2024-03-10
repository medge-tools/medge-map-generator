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
def register():
    from .b3d_utils import register_subpackage

    register_subpackage('')
    register_subpackage('dataset')
    register_subpackage('markov')
    register_subpackage('content')


# -----------------------------------------------------------------------------
def unregister():
    from .b3d_utils import unregister_subpackages
    
    # Temp solution during development
    import bpy
    del bpy.types.Scene.medge_markov_chains

    unregister_subpackages()
