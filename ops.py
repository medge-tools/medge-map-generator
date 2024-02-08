from bpy.types   import Operator, Context, Event
from .dataset    import *


# -----------------------------------------------------------------------------
class MET_OT_InitDatavis(Operator):
    bl_idname   = 'medge_tools.init_datavis'
    bl_label    = 'Init Datavis'

    datavis = None

    @classmethod
    def poll(cls, context: Context):
        scene = context.scene
        return not scene.invoked_vis

    def invoke(self, context: Context, event: Event):
        context.window_manager.modal_handler_add(self)
        self.datavis = DatasetVis(context) 

        scene = context.scene
        scene.invoked_vis = True

        return {'RUNNING_MODAL'}


    def modal(self, context: Context, event: Event):
        scene = context.scene

        if not scene.invoked_vis:
            self.datavis.remove_handle()
            return {'CANCELLED'} 

        return {'PASS_THROUGH'}


# -----------------------------------------------------------------------------
class MET_OT_ResetDatavis(Operator):
    bl_idname   = 'medge_tools.reset_datavis'
    bl_label    = 'Reset Datavis'

    @classmethod
    def poll(cls, context: Context):
        scene = context.scene
        return scene.invoked_vis

    def execute(self, context: Context):
        scene = context.scene
        scene.invoked_vis = False

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_SelectTransitions(Operator):
    bl_idname   = 'medge_tools.select_transitions'
    bl_label    = 'Select Transitions'

    def execute(self, context: Context):
        DatasetOps().select_transitions(context)
        return {'FINISHED'}