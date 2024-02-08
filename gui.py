import  bpy
from    bpy.types   import Context
from    .ops        import *
from    .           import dataset as ds


# -----------------------------------------------------------------------------
class DatasetMainPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'

class MET_PT_DatasetMainPanel(DatasetMainPanel, bpy.types.Panel):
    bl_idname = 'MET_PT_DatasetMainPanel'
    bl_label = 'Dataset'
    
    def draw(self, context: Context):
        pass

# -----------------------------------------------------------------------------
class MET_PT_DatasetVis(DatasetMainPanel, bpy.types.Panel):
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

        row.operator(MET_OT_InitDatavis.bl_idname, text='Init')
        row.operator(MET_OT_ResetDatavis.bl_idname, text='Reset')
        
        col.separator(factor=2)
        
        dataset = ds.get_medge_dataset(obj)
        dataset.vis_settings.draw(col)


# -----------------------------------------------------------------------------
class MET_PT_DatasetOps(DatasetMainPanel, bpy.types.Panel):
    bl_parent_id = MET_PT_DatasetMainPanel.bl_idname
    bl_label = 'Operations'

    def draw(self, context: Context):
        obj = context.active_object
        if not obj: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.operator(MET_OT_SelectTransitions.bl_idname)
        