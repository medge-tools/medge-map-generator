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
from bpy.utils     import register_class, unregister_class 
from .b3d_utils    import register_subpackage, unregister_subpackages
from .generate.gui import MET_PT_GenerateMain, MET_PT_MarkovChains, MET_PT_MapGeneration

# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')

    register_class(MET_PT_GenerateMain)
    register_class(MET_PT_MarkovChains)
    register_class(MET_PT_MapGeneration)

    register_subpackage('generate')
    

# -----------------------------------------------------------------------------
def unregister():
    unregister_subpackages()

    unregister_class(MET_PT_GenerateMain)
    unregister_class(MET_PT_MarkovChains)
    unregister_class(MET_PT_MapGeneration)