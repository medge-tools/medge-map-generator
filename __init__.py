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
from .generate.gui import MET_PT_markov_chains_data, MET_PT_markov_chains_generate, MET_PT_generate_map

# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')

    register_class(MET_PT_markov_chains_data)
    register_class(MET_PT_markov_chains_generate)
    register_class(MET_PT_generate_map)

    register_subpackage('generate')
    

# -----------------------------------------------------------------------------
def unregister():
    unregister_subpackages()

    unregister_class(MET_PT_markov_chains_data)
    unregister_class(MET_PT_generate_map)