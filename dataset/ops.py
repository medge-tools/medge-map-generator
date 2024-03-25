import bpy
from bpy.types              import Operator, Context
from bpy_extras.io_utils    import ImportHelper, ExportHelper
from bpy.props              import StringProperty

from .dataset   import *
from .props     import get_dataset
from .vis       import DatasetVis


# -----------------------------------------------------------------------------
# IO
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_ImportDataset(Operator, ImportHelper):
    bl_idname = "medge_dataset.import_dataset"
    bl_label = "Import Dataset"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,
    )


    def execute(self, context):
        DatasetIO().import_from_file(self.filepath)

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_ExportDataset(Operator, ExportHelper):
    bl_idname = "medge_dataset.export_dataset"
    bl_label = "Export Dataset"
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,
    )


    def execute(self, context):
        dataset = DatasetIO()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# DATASET
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
vis_is_enabled = False

def is_vis_enabled():
    global vis_is_enabled
    return vis_is_enabled


def set_vis_enabeld(state: bool):
    global vis_is_enabled
    vis_is_enabled = state

# -----------------------------------------------------------------------------
class MET_OT_EnableDatasetVis(Operator):
    bl_idname   = 'medge_dataset.enable_dataset_vis'
    bl_label    = 'Enable Dataset Vis'


    @classmethod
    def poll(cls, context: Context):
        return not is_vis_enabled()


    def execute(self, context: Context):
        DatasetVis().add_handle(context)
        context.area.tag_redraw()
        set_vis_enabeld(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableDatasetVis(Operator):
    bl_idname   = 'medge_dataset.disable_dataset_vis'
    bl_label    = 'Disable Dataset Vis'


    @classmethod
    def poll(cls, context: Context):
        return is_vis_enabled()


    def execute(self, context: Context):
        DatasetVis().remove_handle()
        context.area.tag_redraw()
        set_vis_enabeld(False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Dataset Operations
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_ConvertToDataset(Operator):
    bl_idname   = 'medge_dataset.convert_to_dataset'
    bl_label    = 'Convert To Dataset'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return obj.type == 'MESH'


    def execute(self, context: Context):
        obj = context.object
        DatasetOps.convert_to_dataset(obj)
        return {'FINISHED'}  


# -----------------------------------------------------------------------------
class MET_OT_SetState(Operator):
    bl_idname   = 'medge_dataset.set_state'
    bl_label    = 'Set State'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return obj.mode == 'EDIT'


    def execute(self, context: Context):
        obj = context.object
        settings = get_dataset(obj).get_ops_settings()
        s = settings.new_state
        DatasetOps.set_state(obj, PlayerState[s])
        return {'FINISHED'} 


# -----------------------------------------------------------------------------
class MET_OT_SelectTransitions(Operator):
    bl_idname   = 'medge_dataset.select_transitions'
    bl_label    = 'Select Transitions'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return get_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, context: Context):
        obj = context.object
        settings = get_dataset(obj).get_ops_settings()
        DatasetOps.select_transitions(obj, settings.filter, settings.restrict)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_SelectStates(Operator):
    bl_idname   = 'medge_dataset.select_states'
    bl_label    = 'Select States'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        in_edit = obj.mode == 'EDIT'
        if not (dataset := get_dataset(obj)): return False
        settings = dataset.get_ops_settings()
        return in_edit and settings.filter


    def execute(self, context: Context):
        obj = context.object
        settings = get_dataset(obj).get_ops_settings()
        DatasetOps.select_states(obj, settings.filter)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_SnapToGrid(Operator):
    bl_idname   = 'medge_dataset.snap_to_grid'
    bl_label    = 'Snap To Grid'
    bl_options  = {'UNDO'}

    
    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return get_dataset(obj)
    

    def execute(self, context: Context):
        obj = context.object
        spacing = get_dataset(obj).get_ops_settings().spacing

        b3d_utils.snap_to_grid(obj.data, spacing)
        DatasetOps.resolve_overlap(obj)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_ResolveOverlap(Operator):
    bl_idname   = 'medge_dataset.resolve_overlap'
    bl_label    = 'Resolve Overlap'
    bl_options  = {'UNDO'}

    
    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return get_dataset(obj)
    

    def execute(self, context: Context):
        obj = context.object
        DatasetOps.resolve_overlap(obj)
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
