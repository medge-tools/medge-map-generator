from bpy_extras.io_utils    import ImportHelper, ExportHelper
from bpy.props              import StringProperty
from bpy.types              import Operator

from .dataset import DatasetIO


# -----------------------------------------------------------------------------
class MET_OT_ImportDataset(Operator, ImportHelper):
    bl_idname = "medge_tools.import_dataset"
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
    bl_idname = "medge_tools.export_dataset"
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