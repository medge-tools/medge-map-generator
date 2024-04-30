from bpy.types  import Context, Panel

from ..main_gui        import *
from ..b3d_utils       import draw_box 
from .props            import get_modules_prop
from .ops              import *

# -----------------------------------------------------------------------------
class MET_PT_Populate(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_label = 'Populate'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        modules = get_modules_prop(_context)

        col = layout.column(align=True)
        col.separator()
        
        row = col.row(align=True)
        row.template_list('MET_UL_Module', '#modules', modules, 'items', modules, 'selected_item_idx', rows=5)

        col.separator()
        col.operator(MET_OT_UpdateActiveStates.bl_idname)
        
        module = modules.get_selected()

        if not module: return

        col.separator(factor=2)
        col = layout.column(align=True)

        col.prop(module, 'use_collection')
        col.separator()

        if module.use_collection:
            col.prop(module, 'collection')
        else:
            col.prop(module, 'object')

        col.separator(factor=2)
        draw_box(col, 'Selected Dataset Object will be populated')

        col.separator()
        col.operator(MET_OT_Populate.bl_idname)
        
        col.separator(factor=2)
        draw_box(col, 'Select Collection')

        col.separator()
        col.operator(MET_OT_FinalizeContent.bl_idname)

