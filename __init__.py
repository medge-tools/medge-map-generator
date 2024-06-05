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
from .b3d_utils     import register_subpackage, unregister_subpackages


# -----------------------------------------------------------------------------
def register():
    register_subpackage('')
    register_subpackage('dataset')
    register_subpackage('generate')


# -----------------------------------------------------------------------------
def unregister():
    unregister_subpackages()
