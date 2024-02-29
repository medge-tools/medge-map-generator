from    bpy.types   import Context, Panel
from    .ops        import *

from .props import get_dataset, is_datavis_enabled

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
        
        if is_datavis_enabled(context):
            
            layout.separator(factor=2)
            
            vis_settings = get_dataset(obj).get_vis_settings()
            
            col = layout.column(align=True)
            col.prop(vis_settings, 'to_name')
            col.prop(vis_settings, 'only_selection')
            col.prop(vis_settings, 'show_timestamps')
            col.separator()
            col.prop(vis_settings, 'color')
            col.separator()
            col.prop(vis_settings, 'font_size')
            col.separator()
            col.prop(vis_settings, 'min_draw_distance', text='Draw Distance Min')
            col.prop(vis_settings, 'max_draw_distance', text='Max')


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

        col = layout.column(align=True)
        
        col.prop(dataset, 'state')
        col.separator()
        col.operator(MET_OT_SetState.bl_idname)

        col.separator()
        col.prop(dataset, 'use_filter')
        if dataset.use_filter:
            col.prop(dataset, 'filter')
        
        col.separator()
        col.operator(MET_OT_SelectTransitions.bl_idname)
        
        col.separator()
        col.prop(dataset, 'filter')
        
        col.separator()
        col.operator(MET_OT_SelectStates.bl_idname)

        col.separator()
        col.prop(dataset, 'spacing')
        col.separator()
        col.operator(MET_OT_SnapToGrid.bl_idname)
        