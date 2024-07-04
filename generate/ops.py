from bpy.types  import Operator, Context

from datetime import datetime

from ..b3d_utils import get_active_collection, new_collection
from .props      import MET_PG_generated_chain, get_markov_chains_prop, get_curve_module_groups_prop, get_curve_module_prop, add_collision_volume, get_medge_map_gen_settings
from .map        import generate, prepare_for_export, export


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_create_transition_matrix(Operator):
    bl_idname = 'medge_generate.create_transition_matrix'
    bl_label  = 'Create Transition Matrix'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        cls.bl_label = 'Create Transition Matrix'

        if item.has_transition_matrix():
            cls.bl_label = 'Update Transition Matrix'

        return True


    def execute(self, _context:Context):
        markov_chains = get_markov_chains_prop(_context)
        item = markov_chains.get_selected()
        item.create_transition_matrix()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_generate_chain(Operator):
    bl_idname = 'medge_generate.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        return item.has_transition_matrix()


    def execute(self, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        item.generate_chain()

        return {'FINISHED'}        


# -----------------------------------------------------------------------------
class MET_OT_add_handmade_chain(Operator):
    bl_idname = 'medge_generate.add_handmade_chain'
    bl_label  = 'Add Handmade Chain'


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        mc.get_selected().add_handmade_chain()
        
        return {'FINISHED'}    
    

# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_init_module_collections(Operator):
    bl_idname      = 'medge_generate.init_modules'
    bl_label       = 'Init Module Collections'
    bl_description = 'Initialize list elements or reset if they already exists'


    def execute(self, _context):
        modules = get_curve_module_groups_prop(_context)
        modules.init_collections()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_add_curve_module_to_group(Operator):
    bl_idname      = 'medge_generate.add_curve_module_to_group'
    bl_label       = 'Add Curve Module To Group'
    bl_description = 'Add curve module to collection'
    bl_options     = {'UNDO'}

    @classmethod
    def poll(cls, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()

        return mg.collection != None


    def execute(self, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()
        mg.add_module()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_add_collision_volume(Operator):
    bl_idname      = 'medge_generate.add_collision_volume'
    bl_label       = 'Add Collision Volume'
    bl_description = 'Add collision volume to curve module'
    bl_options     = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj and not get_curve_module_prop(obj).collision_volume


    def execute(self, _context:Context):
        objs = _context.selected_objects

        for obj in objs:
            add_collision_volume(obj)

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_generate_map(Operator):
    bl_idname = 'medge_generate.generate_map'
    bl_label = 'Generate Map'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        active_mc = mc.get_selected()
        gen_chain:MET_PG_generated_chain = active_mc.generated_chains.get_selected()

        module_groups = get_curve_module_groups_prop(_context)

        settings = get_medge_map_gen_settings(_context)
        
        time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        collection = new_collection(f'POPULATED_{active_mc.name}_[{settings}]_{time}' )

        generate(gen_chain, module_groups.items, settings, collection)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_generate_all_maps(Operator):
    bl_idname = 'medge_generate.generate_all_maps'
    bl_label = 'Generate All Maps'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        active_mc = mc.get_selected()

        module_groups = get_curve_module_groups_prop(_context)

        settings = get_medge_map_gen_settings(_context)

        for  gen_chain in active_mc.generated_chains.items:
            time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
            collection = new_collection(f'POPULATED_{active_mc.name}_[{settings}]_{time}' )

            generate(gen_chain, module_groups.items, settings, collection)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_prepare_for_export(Operator):
    bl_idname = 'medge_generate.prepare_for_export'
    bl_label = 'Prepare For Export'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        settings = get_medge_map_gen_settings(_context)
        prepare_for_export(settings, collection)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_export_t3d(Operator):
    bl_idname = 'medge_generate.export_t3d'
    bl_label = 'Export T3D'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        export(collection)

        return {'FINISHED'}