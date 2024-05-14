import bpy
from bpy.types           import Operator, Context
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props           import StringProperty

from .dataset import DatasetIO, to_dataset, set_player_state, is_dataset, select_transitions, select_player_states
from .props   import get_dataset_prop
from .        import vis


# -----------------------------------------------------------------------------
# IO
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_ImportDataset(Operator, ImportHelper):
    bl_idname = 'medge_dataset.import_dataset'
    bl_label = 'Import Dataset'
    filename_ext = '.json'

    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'},
        maxlen=255,
    )


    def execute(self, context):
        DatasetIO().import_from_file(self.filepath)

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_ExportDataset(Operator, ExportHelper):
    bl_idname = 'medge_dataset.export_dataset'
    bl_label = 'Export Dataset'
    filename_ext = ".json"

    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'},
        maxlen=255,
    )


    def execute(self, context):
        io = DatasetIO()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# DATASET
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
vis_state = False

def is_vis_enabled():
    global vis_state
    return vis_state


def set_vis_state(state: bool):
    global vis_state
    vis_state = state


# -----------------------------------------------------------------------------
class MET_OT_EnableDatasetVis(Operator):
    bl_idname = 'medge_dataset.enable_dataset_vis'
    bl_label  = 'Enable Dataset Vis'


    @classmethod
    def poll(cls, _context:Context):
        return not is_vis_enabled()


    def execute(self, _context:Context):
        vis.add_handle(_context)
        _context.area.tag_redraw()
        set_vis_state(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableDatasetVis(Operator):
    bl_idname   = 'medge_dataset.disable_dataset_vis'
    bl_label    = 'Disable Dataset Vis'


    @classmethod
    def poll(cls, _context:Context):
        return is_vis_enabled()


    def execute(self, _context:Context):
        vis.remove_handle()
        _context.area.tag_redraw()
        set_vis_state(False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Dataset Operations
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_ConvertToDataset(Operator):
    bl_idname = 'medge_dataset.convert_to_dataset'
    bl_label  = 'Convert To Dataset'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj.type == 'MESH'


    def execute(self, _context:Context):
        obj = _context.object
        to_dataset(obj)
        return {'FINISHED'}  


# -----------------------------------------------------------------------------
class MET_OT_SetState(Operator):
    bl_idname = 'medge_dataset.set_state'
    bl_label  = 'Set State'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        settings = get_dataset_prop(obj).get_ops_settings()
        s = settings.new_state
        set_player_state(obj, State[s])
        return {'FINISHED'} 


# -----------------------------------------------------------------------------
class MET_OT_SelectTransitions(Operator):
    bl_idname = 'medge_dataset.select_transitions'
    bl_label  = 'Select Transitions'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        settings = get_dataset_prop(obj).get_ops_settings()
        select_transitions(obj, settings.filter, settings.restrict)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_SelectStates(Operator):
    bl_idname = 'medge_dataset.select_states'
    bl_label  = 'Select States'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        settings = get_dataset_prop(obj).get_ops_settings()
        select_player_states(obj, settings.filter)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, context):
    self.layout.operator(MET_OT_ImportDataset.bl_idname, text='MEdge Dataset (.json)')


# -----------------------------------------------------------------------------
def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)


# -----------------------------------------------------------------------------
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)
