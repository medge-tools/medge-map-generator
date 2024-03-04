from bpy.types  import Context, Panel

from .props     import get_modules

class MET_PT_PCG(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'
    bl_label = 'PCG'

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        modules = get_modules(context)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.template_list('B3D_UL_GenericList', '#modules', modules, 'items', modules, 'selected_item_idx', rows=4)
        
        col = row.column(align=True)
        
        item = modules.get_selected()

        if not item: return

        col = layout.column(align=True)
