import  bpy
from    bpy.types   import Context, Event, Operator
from    bpy.props   import *
from    .dataset    import DatasetVis
from    .           import dataset_utils as dsu

# -----------------------------------------------------------------------------
class MET_OT_DatavisHandler(Operator):
    bl_idname   = 'medge_dataset_editor.overlay_data'
    bl_label    = 'Overlay Data'

    draw_handle = None

    def invoke(self, context: Context, event: Event):
        settings = dsu.get_medge_dataset_settings(context.scene)

        if settings.has_draw_handle:
            return {'CANCELLED'}
        
        self.register_handler(context)
        return {"RUNNING_MODAL"}


    def modal(self, context: Context, event: Event):
        # if context.area:
        #     context.area.tag_redraw()
        return {'PASS_THROUGH'}
    

    def register_handler(self, context: Context):
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            DatasetVis.draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)

        settings = dsu.get_medge_dataset_settings(context.scene)
        settings.has_draw_handle = True


    def unregister_handler(self, context: Context):
        bpy.types.SpaceView3D.draw_handler_remove( self.draw_handle, 'WINDOW' )
        self.draw_handle = None
        
        settings = dsu.get_medge_dataset_settings(context.scene)
        settings.has_draw_handle = False
    

    def finish(self, context: Context):
        self.unregister_handler(context)
        return {'FINISHED'}