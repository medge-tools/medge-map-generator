from bpy.types  import Operator, Context

from .props import get_markov_chains_prop
from .      import stats

from ..b3d_utils       import get_active_collection
from .props            import MET_PG_GeneratedChain, get_module_groups_prop, get_population_prop
from .map              import MapGenSettings, generate, prepare_for_export, export


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
statistics_state = False

def is_stats_enabled():
    global statistics_state
    return statistics_state


def set_stats_state(state: bool):
    global statistics_state
    statistics_state = state


# -----------------------------------------------------------------------------
class MET_OT_EnableMarkovStats(Operator):
    bl_idname = 'medge_generate.enable_markov_statistics'
    bl_label  = 'Enable Statistics'


    @classmethod
    def poll(cls, _context:Context):
        return not is_stats_enabled()


    def execute(self, context: Context):
        stats.add_handle(context)
        context.area.tag_redraw()
        set_stats_state(True)

        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableMarkovStats(Operator):
    bl_idname = 'medge_generate.disable_markov_statistics'
    bl_label  = 'Disable Statistics'


    @classmethod
    def poll(cls, _context:Context):
        return is_stats_enabled()


    def execute(self, _context:Context):
        stats.remove_handle()
        _context.area.tag_redraw()
        set_stats_state(False)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
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
class MET_OT_GenerateChain(Operator):
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
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_InitModules(Operator):
    bl_idname = 'medge_generate.init_modules'
    bl_label = 'Init Modules'


    def execute(self, _context):
        modules = get_module_groups_prop(_context)
        modules.init()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_UpdateActiveStates(Operator):
    bl_idname = 'medge_generate.update_active_states'
    bl_label = 'Update Active States'


    def execute(self, _context:Context):
        markov = get_markov_chains_prop(_context)
        active_mc = markov.get_selected()

        active_chain = active_mc.generated_chains.get_selected()

        modules = get_module_groups_prop(_context)
        modules.update_active_states(active_chain)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_InitCapsuleData(Operator):
    bl_idname = 'medge_generate.init_capsule_data'
    bl_label = 'Init Capsule Data'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        module_groups = get_module_groups_prop(_context)
        module_groups.init_capsule_data()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_GenerateMap(Operator):
    bl_idname = 'medge_generate.generate_map'
    bl_label = 'Generate Map'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        active_mc = mc.get_selected()

        module_groups = get_module_groups_prop(_context)

        gen_chain:MET_PG_GeneratedChain = active_mc.generated_chains.get_selected()

        settings = MapGenSettings()
        settings.seed               = module_groups.seed 
        settings.collision_radius   = module_groups.capsule_radius
        settings.collision_height   = module_groups.capsule_height
        settings.max_depth          = module_groups.max_depth
        settings.max_angle          = module_groups.max_angle
        settings.angle_step         = module_groups.angle_step
        settings.align_orientation  = module_groups.align_orientation
        settings.resolve_collisions = module_groups.resolve_collisions
        settings.random_angles      = module_groups.random_angles
        settings.debug_capsules     = module_groups.debug_capsules

        generate(gen_chain.chain, gen_chain.seperator, module_groups.items, active_mc.name, settings)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_PrepareForExport(Operator):
    bl_idname = 'medge_generate.prepare_for_export'
    bl_label = 'Prepare For Export'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        collection = get_active_collection()
        if not collection: return False
        prop = get_population_prop(collection)
        return prop.has_content


    def execute(self, _context:Context):
        collection = get_active_collection()
        prepare_for_export(collection)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_ExportT3D(Operator):
    bl_idname = 'medge_generate.export_t3d'
    bl_label = 'Export T3D'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        collection = get_active_collection()
        
        if not collection: return False

        prop = get_population_prop(collection)

        return prop.has_content


    def execute(self, _context:Context):
        collection = get_active_collection()
        export(collection)

        return {'FINISHED'}