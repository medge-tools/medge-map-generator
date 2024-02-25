import bpy
from bpy.types              import Operator, Context
from bpy_extras.io_utils    import ImportHelper, ExportHelper
from bpy.props              import StringProperty

from .dataset   import *
from .          import props


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
class MET_OT_EnableDatavis(Operator):
    bl_idname   = 'medge_dataset.enable_datavis'
    bl_label    = 'Enable Datavis'


    @classmethod
    def poll(cls, context: Context):
        return not props.is_datavis_enabled(context)


    def execute(self, context: Context):
        DatasetVis().add_handle(context)
        context.area.tag_redraw()
        props.set_datavis_enabeld(context, True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableDatavis(Operator):
    bl_idname   = 'medge_dataset.disable_datavis'
    bl_label    = 'Disable Datavis'


    @classmethod
    def poll(cls, context: Context):
        return props.is_datavis_enabled(context)


    def execute(self, context: Context):
        DatasetVis().remove_handle()
        context.area.tag_redraw()
        props.set_datavis_enabeld(context, False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Dataset Operations
# -----------------------------------------------------------------------------
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
        dataset = props.get_dataset(obj)
        DatasetOps.set_state(obj, dataset.state)
        return {'FINISHED'} 


class MET_OT_SelectTransitions(Operator):
    bl_idname   = 'medge_dataset.select_transitions'
    bl_label    = 'Select Transitions'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return props.is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, context: Context):
        obj = context.object
        dataset = props.get_dataset(obj)
        filter = ''
        if dataset.use_filter:
            filter = dataset.filter
        DatasetOps.select_transitions(obj, filter)
        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_SelectStates(Operator):
    bl_idname   = 'medge_dataset.select_states'
    bl_label    = 'Select States'


    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        in_edit = obj.mode == 'EDIT'
        if not props.is_dataset(obj): return False
        dataset = props.get_dataset(obj)
        return in_edit and dataset.filter


    def execute(self, context: Context):
        obj = context.object
        dataset = props.get_dataset(obj)
        DatasetOps.select_states(obj, dataset.filter)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_SnapToGrid(Operator):
    bl_idname   = 'medge_dataset.snap_to_grid'
    bl_label    = 'Snap To Grid'
    bl_options  = {'UNDO'}

    
    @classmethod
    def poll(cls, context: Context):
        obj = context.object
        return props.is_dataset(obj)
    

    def execute(self, context: Context):
        obj = context.object
        spacing = props.get_dataset(obj).spacing

        b3d_utils.snap_to_grid(obj.data, spacing)
        DatasetOps.resolve_overlap(obj)
        return {'FINISHED'}
    


# -----------------------------------------------------------------------------
# Register
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, context):
    self.layout.operator(MET_OT_ImportDataset.bl_idname, text='MEdge Dataset (.json)')


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)
    
