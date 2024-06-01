from bpy.types  import Operator, Context

from ..b3d_utils       import get_active_collection
from ..dataset.dataset import is_dataset
from .props            import get_module_states_prop, get_population_prop
from .content          import populate, prepare_for_export, export


# -----------------------------------------------------------------------------
class MET_OT_InitModules(Operator):
    bl_idname = 'medge_content.init_modules'
    bl_label = 'Init Modules'


    def execute(self, _context):
        modules = get_module_states_prop(_context)
        modules.init()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_UpdateActiveStates(Operator):
    bl_idname = 'medge_content.update_active_states'
    bl_label = 'Update Active States'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        if not obj: return False
        return is_dataset(obj)


    def execute(self, _context:Context):
        modules = get_module_states_prop(_context)
        modules.update_active_states(_context.object)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_Populate(Operator):
    bl_idname = 'medge_content.populate'
    bl_label = 'Populate'
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        if not obj: return False
        return is_dataset(obj)


    def execute(self, _context:Context):
        modules = get_module_states_prop(_context).items
        populate(_context.object, modules)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_PreppareForExport(Operator):
    bl_idname = 'medge_content.prepare_for_export'
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
    bl_idname = 'medge_content.export_t3d'
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