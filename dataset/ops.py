import bpy
from bpy.types              import Operator, Context
from bpy_extras.io_utils    import ImportHelper, ExportHelper
from bpy.props              import StringProperty

from .dataset   import *
from .          import props, vis


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
vis_state = False

def is_vis_enabled():
    global vis_state
    return vis_state


def set_vis_state(state: bool):
    global vis_state
    vis_state = state

# -----------------------------------------------------------------------------
class MET_OT_EnableDatasetVis(Operator):
    bl_idname   = 'medge_dataset.enable_dataset_vis'
    bl_label    = 'Enable Dataset Vis'


    @classmethod
    def poll(cls, context: Context):
        return not is_vis_enabled()


    def execute(self, context: Context):
        vis.add_handle(context)
        context.area.tag_redraw()
        set_vis_state(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableDatasetVis(Operator):
    bl_idname   = 'medge_dataset.disable_dataset_vis'
    bl_label    = 'Disable Dataset Vis'


    @classmethod
    def poll(cls, context: Context):
        return is_vis_enabled()


    def execute(self, context: Context):
        vis.remove_handle()
        context.area.tag_redraw()
        set_vis_state(False)
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
        props.convert_to_dataset(obj)
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
        set_player_state(obj, PlayerState[s])
        return {'FINISHED'} 


# -----------------------------------------------------------------------------
class MET_OT_SelectTransitions(Operator):
    bl_idname   = 'medge_dataset.select_transitions'
    bl_label    = 'Select Transitions'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, context: Context):
        obj = context.object
        settings = get_dataset(obj).get_ops_settings()
        select_transitions(obj, settings.filter, settings.restrict)
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
        select_player_states(obj, settings.filter)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_SnapToGrid(Operator):
    bl_idname   = 'medge_dataset.snap_to_grid'
    bl_label    = 'Snap To Grid'
    bl_options  = {'UNDO'}

    
    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return is_dataset(obj)
    

    def execute(self, context: Context):
        obj = context.object
        spacing = props.get_dataset(obj).get_ops_settings().spacing

        b3d_utils.snap_to_grid(obj.data, spacing)
        resolve_overlap(obj)
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
        resolve_overlap(obj)
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
