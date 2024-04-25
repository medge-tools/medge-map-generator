from bpy.types  import Event, Operator, Context

from ..dataset.dataset import is_dataset, get_dataset
from .props            import get_modules_prop
from .content          import populate


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
        modules = get_modules_prop(_context)
        modules.update_active_states(get_dataset(_context.object))
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
from ..dataset.dataset import Dataset, Attribute
from copy import deepcopy


class MET_OT_Populate(Operator):
    bl_idname = 'medge_content.populate'
    bl_label = 'Populate'
    bl_options = {'UNDO'}


    dataset: Dataset


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        if not obj: return False
        return is_dataset(obj)


    def execute(self, _context:Context):
        modules = get_modules_prop(_context).items
        populate(_context.object, modules)
        return {'FINISHED'}

