import  bpy
from    bpy.types   import Context, Event, Operator
from    bpy.props   import *
from    .dataset    import DatasetVis
from    .           import dataset_utils as dsu

# -----------------------------------------------------------------------------
class MET_OT_AddDatavisDrawHandle(Operator):
    bl_idname   = 'medge_dataset_editor.overlay_data'
    bl_label    = 'Overlay Data'

    draw_handle = None

    def invoke(self, context: Context, event: Event):
        self.register_handler(context)
        return {'RUNNING_MODAL'}


    def modal(self, context: Context, event: Event):
        if context.area:
            context.area.tag_redraw()

        settings = dsu.get_medge_dataset_settings(context.scene)


        if settings.invoked_add_draw_handles > 0:
            self.unregister_handler(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}
    

    def register_handler(self, context: Context):
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            DatasetVis.draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        
        settings = dsu.get_medge_dataset_settings(context.scene)
        settings.invoked_add_draw_handles += 1


    def unregister_handler(self, context: Context):
        bpy.types.SpaceView3D.draw_handler_remove( self.draw_handle, 'WINDOW' )
        self.draw_handle = None

        settings = dsu.get_medge_dataset_settings(context.scene)
        settings.invoked_add_draw_handles -= 1
    

    def finish(self, context: Context):
        self.unregister_handler(context)
        return {'FINISHED'}