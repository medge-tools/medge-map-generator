from bpy.types  import Operator

from ..dataset.props    import is_dataset
from .props             import get_modules
from .pcg               import generate

# -----------------------------------------------------------------------------
class MET_OT_InitModules(Operator):
    bl_idname = "medge_pcg.init_modules"
    bl_label = "Init Modules"


    def execute(self, context):
        modules = get_modules(context)
        modules.init()
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_Generate(Operator):
    bl_idname = "medge_pcg.generate"
    bl_label = "Generate"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return is_dataset(obj)

    def execute(self, context):
        obj = context.object
        modules = get_modules(context)
        generate(obj, modules.to_list())
        return {'FINISHED'}