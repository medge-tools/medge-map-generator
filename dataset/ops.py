import bpy
from bpy.types              import Operator, Context, Event
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

    datavis = None


    @classmethod
    def poll(cls, context: Context):
        return not props.is_datavis_enabled(context)


    def invoke(self, context: Context, event: Event):
        context.window_manager.modal_handler_add(self)

        self.datavis = DatasetVis(context) 

        context.area.tag_redraw()

        props.set_datavis_enabeld(context, True)

        return {'RUNNING_MODAL'}


    def modal(self, context: Context, event: Event):
        context.area.tag_redraw()

        if not props.is_datavis_enabled(context):
            self.datavis.remove_handle()
            context.area.tag_redraw()
            return {'CANCELLED'} 

        return {'PASS_THROUGH'}


# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, context):
    self.layout.operator(MET_OT_ImportDataset.bl_idname, text='MEdge Dataset (.json)')


def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)
    

# -----------------------------------------------------------------------------
class MET_OT_ResetDatavis(Operator):
    bl_idname   = 'medge_dataset.disable_datavis'
    bl_label    = 'Disable Datavis'


    @classmethod
    def poll(cls, context: Context):
        return props.is_datavis_enabled(context)


    def execute(self, context: Context):
        scene = context.scene
        props.set_datavis_enabeld(context, False)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_SelectTransitions(Operator):
    bl_idname   = 'medge_dataset.select_transitions'
    bl_label    = 'Select Transitions'


    def execute(self, context: Context):
        DatasetOps.select_transitions(context)
        return {'FINISHED'}