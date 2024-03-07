from bpy.types  import Operator

from ..dataset.props    import get_dataset
from .props             import get_modules
from .content               import populate

# -----------------------------------------------------------------------------
class MET_OT_InitModules(Operator):
    bl_idname = "medge_content.init_modules"
    bl_label = "Init Modules"


    def execute(self, context):
        modules = get_modules(context)
        modules.init()
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_Populate(Operator):
    bl_idname = "medge_content.populate"
    bl_label = "Populate"


    @classmethod
    def poll(cls, context):
        dataset = get_dataset(context.object)
        return dataset.is_dataset

    def execute(self, context):
        obj = context.object
        modules = get_modules(context)
        populate(obj, modules.to_list())
        return {'FINISHED'}