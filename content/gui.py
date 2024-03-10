from bpy.types  import Context, Panel

from ..main_gui import *
from .ops       import MET_OT_InitModules, MET_OT_Populate
from .props     import get_modules


# -----------------------------------------------------------------------------
class MET_PT_Populate(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_label = 'Populate'


    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        modules = get_modules(context)

        col = layout.column(align=True)

        if not modules.initialized:
            col.operator(MET_OT_InitModules.bl_idname)
        
        col.separator()
        
        row = col.row(align=True)
        row.template_list('B3D_UL_GenericList', '#modules', modules, 'items', modules, 'selected_item_idx', rows=4)
        
        col = row.column(align=True)
        
        module = modules.get_selected()

        if not module: return

        col = layout.column(align=True)
        col.prop(module, 'object')

        col.separator()
        box = col.box()
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text='Selected Dataset will be populated')

        col.separator()
        col.operator(MET_OT_Populate.bl_idname)

