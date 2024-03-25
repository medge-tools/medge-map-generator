from    bpy.types   import Context, Panel
from    .ops        import *

from ..main_gui import MapGenPanel_DefaultProps, MET_PT_MapGenMainPanel
from .props     import get_dataset
from .ops       import is_vis_enabled

classes = []


# -----------------------------------------------------------------------------
class MET_PT_DatasetMainPanel(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_idname = 'MET_PT_DatasetMainPanel'
    bl_label = 'Dataset'
    
    def draw(self, context: Context):
        pass

classes.append(MET_PT_DatasetMainPanel)


# -----------------------------------------------------------------------------
class MET_PT_DatasetVis(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_DatasetMainPanel.bl_idname
    bl_label = 'Visualization'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context: Context):        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)
        row = col.row(align=True)

        row.operator(MET_OT_EnableDatasetVis.bl_idname, text='Enable')
        row.operator(MET_OT_DisableDatasetVis.bl_idname, text='Disable')
        
        if not is_vis_enabled(): 
            box = layout.box()
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text='Visualization renders in Edit Mode')
            return

        if not (obj := context.active_object): return
        if not (dataset := get_dataset(obj)): return

        vis_settings = dataset.get_vis_settings()
        
        col = layout.column(align=True)
        col.separator()
        
        col.prop(vis_settings, 'to_name')
        col.prop(vis_settings, 'only_selection')
        col.prop(vis_settings, 'show_timestamps')
        col.prop(vis_settings, 'draw_aabb')
        col.separator()
        col.prop(vis_settings, 'default_color')
        col.prop(vis_settings, 'start_chain_color')
        col.separator()
        col.prop(vis_settings, 'font_size')
        col.separator()
        col.prop(vis_settings, 'min_draw_distance', text='Draw Distance Min')
        col.prop(vis_settings, 'max_draw_distance', text='Max')

classes.append(MET_PT_DatasetVis)


# -----------------------------------------------------------------------------
class MET_PT_DatasetOps(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_DatasetMainPanel.bl_idname
    bl_label = 'Operations'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context):
        obj = context.active_object
        if not obj: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        if not (dataset := get_dataset(obj)): 
            col.operator(MET_OT_ConvertToDataset.bl_idname)
        else:
            col.operator(MET_OT_ConvertToDataset.bl_idname, text='Update Attributes')

        settings = dataset.get_ops_settings()
        
        col.prop(settings, 'new_state')
        col.separator()
        col.operator(MET_OT_SetState.bl_idname)

        col.separator()
        col.prop(settings, 'use_filter')
        if settings.use_filter:
            col.prop(settings, 'restrict')
            col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_SelectTransitions.bl_idname)
        
        col.separator()
        col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_SelectStates.bl_idname)

        col.separator()
        col.prop(settings, 'spacing')
        col.separator()
        col.operator(MET_OT_SnapToGrid.bl_idname)
        col.operator(MET_OT_ResolveOverlap.bl_idname)


classes.append(MET_PT_DatasetOps)
