from bpy.types  import Operator, Context

from ..dataset import dataset
from .props    import get_modules
from .content  import populate


# -----------------------------------------------------------------------------
class MET_OT_InitModules(Operator):
    bl_idname = "medge_content.init_modules"
    bl_label = "Init Modules"


    def execute(self, _context:Context):
        modules = get_modules(_context)
        modules.init()
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_Populate(Operator):
    bl_idname = "medge_content.populate"
    bl_label = "Populate"


    @classmethod
    def poll(cls, _context:Context):
        if not _context.object: return False
        return dataset.is_dataset(_context.object)


    def execute(self, _context:Context):
        obj = _context.object
        modules = get_modules(_context)
        populate(obj, modules.to_list())
        return {'FINISHED'}
    