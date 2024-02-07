import  bpy
from    bpy.types   import Context, Event, Operator
from    bpy.props   import *
import  bmesh
from    .dataset    import *
from    .           import dataset_utils as dsu
from    .           import utils


# -----------------------------------------------------------------------------
draw_handle_added = False

class MET_OT_InitDatavis(Operator):
    bl_idname   = 'medge_dataset_editor.init_datavis'
    bl_label    = 'Datavis'

    def execute(self, context: Context):
        DatasetVis(context)
        return {'FINISHED'}
    