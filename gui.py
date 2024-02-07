import  bpy
from    .ops    import *
from    .       import dataset_utils as dsu

# -----------------------------------------------------------------------------
class MET_PT_Dataset(bpy.types.Panel):
    bl_idname = 'MET_PT_dataset'
    bl_label = 'Dataset'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'

    def draw(self, context : bpy.types.Context):
        obj = context.active_object
        if not obj: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        layout.operator(MET_OT_InitDatavis.bl_idname, text='Init Datavis')

        dataset = dsu.get_medge_dataset(obj)
        layout.prop(dataset, 'overlay_data')