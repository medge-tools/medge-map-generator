from bpy.types  import Operator, Context

from .props import get_markov_chains_prop

from ..b3d_utils       import get_active_collection
from .props            import MET_PG_GeneratedChain, get_curve_module_groups_prop, get_curve_module_prop, add_collision_volume, remove_collision_volume
from .map              import MapGenSettings, generate, prepare_for_export, export


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
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
class MET_OT_AddHandmadeChain(Operator):
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
class MET_OT_InitModules(Operator):
    bl_idname = 'medge_generate.init_modules'
    bl_label = 'Init Modules'


    def execute(self, _context):
        modules = get_curve_module_groups_prop(_context)
        modules.init_groups()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_AddCurveModuleToGroup(Operator):
    bl_idname = 'medge_generate.add_curve_module_to_group'
    bl_label = 'Add Curve Module To Group'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()

        if mg.use_collection:
            return mg.collection != None
        else:
            return mg.module == None


    def execute(self, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()
        mg.add_module()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_AddCollisionVolume(Operator):
    bl_idname  = 'medge_generate.add_collision_volume'
    bl_label   = 'Add Collision Volume'
    bl_options = {'UNDO'}


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
class MET_OT_RemoveCollisionVolume(Operator):
    bl_idname  = 'medge_generate.remove_collision_volume'
    bl_label   = 'Remove Collision Volume'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        objs = _context.selected_objects

        for obj in objs:
            remove_collision_volume(obj)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# class MET_OT_TestVolumeOverlap(Operator):
#     bl_idname = 'medge_generate.test_volume_overlap'
#     bl_label = 'Test Volume Overlap'
#     bl_options = {'UNDO'}

#     @classmethod
#     def poll(cls, _context:Context):
#         objs = _context.selected_objects
#         return len(objs) == 2


#     def execute(self, _context:Context):
#         from .. import b3d_utils
#         objs = _context.selected_objects
#         pairs = b3d_utils.check_objects_overlap(objs[0], objs[1])
#         self.report({'INFO'}, str(len(pairs) > 0))
#         return {'FINISHED'}
    

# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_GenerateMap(Operator):
    bl_idname = 'medge_generate.generate_map'
    bl_label = 'Generate Map'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        active_mc = mc.get_selected()

        module_groups = get_curve_module_groups_prop(_context)

        gen_chain:MET_PG_GeneratedChain = active_mc.generated_chains.get_selected()

        settings = MapGenSettings()
        settings.seed              = module_groups.seed 
        settings.align_orientation = module_groups.align_orientation
        settings.resolve_overlap   = module_groups.resolve_volume_overlap
        settings.max_depth         = module_groups.max_depth
        settings.max_angle         = module_groups.max_angle
        settings.angle_step        = module_groups.angle_step
        settings.random_angles     = module_groups.random_angles

        generate(gen_chain, module_groups.items, active_mc.name, settings)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_PrepareForExport(Operator):
    bl_idname = 'medge_generate.prepare_for_export'
    bl_label = 'Prepare For Export'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        prepare_for_export(collection)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_ExportT3D(Operator):
    bl_idname = 'medge_generate.export_t3d'
    bl_label = 'Export T3D'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        export(collection)

        return {'FINISHED'}