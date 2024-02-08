from    bpy.types   import Operator, Context, Event
from    .dataset    import *


# -----------------------------------------------------------------------------
class MET_OT_InitDatavis(Operator):
    bl_idname   = 'medge_dataset_editor.init_datavis'
    bl_label    = 'Datavis'

    datavis = None

    def invoke(self, context: Context, event: Event):
        scene = context.scene
        # if scene.invoked_datavis: 
        #     return {'CANCELLED'}

        scene.invoked_datavis = True
        context.window_manager.modal_handler_add(self)
        self.datavis = DatasetVis(context) 
        return {'RUNNING_MODAL'}


    def modal(self, context: Context, event: Event):
        return {'PASS_THROUGH'}
    