bl_info = {
    'name'        : 'Map Generator',
    'author'      : 'Tariq Bakhtali (didibib)',
    'description' : '',
    'blender'     : (3, 4, 0),
    'version'     : (1, 0, 0),
    'location'    : '',
    'warning'     : '',
    'category'    : 'MEdge Tools'
}


# -----------------------------------------------------------------------------
from bpy.utils     import register_class 

from .             import auto_load
from .prefs        import MET_map_gen_preferences

from .src.gui      import MET_PT_map_gen_panel
from .src.dataset  import MET_PT_dataset, MET_PT_dataset_vis
from .src.markov   import MET_PT_markov_chains_data, MET_PT_markov_chains_generate 
from .src.modules  import MET_PT_modules
from .src.map      import MET_PT_generate_map
from .src.export   import MET_PT_export_map
from .src.evaluate import MET_PT_evaluate


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    register_class(MET_map_gen_preferences)

    register_class(MET_PT_map_gen_panel)
    
    register_class(MET_PT_dataset)
    register_class(MET_PT_dataset_vis)

    register_class(MET_PT_markov_chains_data)
    register_class(MET_PT_markov_chains_generate)
    register_class(MET_PT_modules)
    register_class(MET_PT_generate_map)
    register_class(MET_PT_export_map)
    register_class(MET_PT_evaluate)

    auto_load.init()
    auto_load.register()


# -----------------------------------------------------------------------------
def unregister():
    auto_load.unregister()
