from    bpy.types   import Context, Panel
from    .ops        import *

from . import props

# -----------------------------------------------------------------------------
class DatasetMainPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'


class MET_PT_DatasetMainPanel(DatasetMainPanel, Panel):
    bl_idname = 'MET_PT_DatasetMainPanel'
    bl_label = 'Dataset'
    
    def draw(self, context: Context):
        pass


# -----------------------------------------------------------------------------
class MET_PT_DatasetVis(DatasetMainPanel, Panel):
    bl_parent_id = MET_PT_DatasetMainPanel.bl_idname
    bl_label = 'Visualization'

    def draw(self, context: Context):
        obj = context.active_object
        if not obj: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)
        row = col.row(align=True)

        row.operator(MET_OT_EnableDatavis.bl_idname, text='Enable')
        row.operator(MET_OT_DisableDatavis.bl_idname, text='Disable')
        
        if props.is_datavis_enabled(context):
            
            layout.separator(factor=2)
            
            vis_settings = props.get_dataset(obj).vis_settings
            
            col = layout.column(align=True)
            col.prop(vis_settings, 'overlay_data')

            if vis_settings.overlay_data:
                col.prop(vis_settings, 'to_name')
                col.prop(vis_settings, 'only_selection')
                col.prop(vis_settings, 'show_timestamps')
                col.prop(vis_settings, 'font_size')


# -----------------------------------------------------------------------------
class MET_PT_DatasetOps(DatasetMainPanel, Panel):
    bl_parent_id = MET_PT_DatasetMainPanel.bl_idname
    bl_label = 'Operations'

    def draw(self, context: Context):
        obj = context.active_object
        if not obj: return
        
        dataset = props.get_dataset(obj)

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.operator(MET_OT_SelectTransitions.bl_idname)
        layout.separator()
        layout.prop(dataset, 'spacing')
        layout.operator(MET_OT_SnapToGrid.bl_idname)
        