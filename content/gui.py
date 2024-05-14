from bpy.types import Context, Panel

from ..main_gui import MapGenPanel_DefaultProps, MET_PT_MapGenMainPanel
from ..         import b3d_utils
from .props     import get_modules_prop
from .ops       import MET_OT_InitModules, MET_OT_UpdateActiveStates, MET_OT_Populate, MET_OT_FinalizeContent


# -----------------------------------------------------------------------------
class MET_PT_Populate(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_label = 'Populate'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        module_prop = get_modules_prop(_context)

        col = layout.column(align=True)
        col.separator()
        
        row = col.row(align=True)
        row.template_list('MET_UL_ModuleList', '#modules', module_prop, 'items', module_prop, 'selected_item_idx', rows=5)

        col.separator()
        col.operator(MET_OT_InitModules.bl_idname)
        col.operator(MET_OT_UpdateActiveStates.bl_idname)
        col.prop(module_prop, 'filter_active')
        
        module = module_prop.get_selected()

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
        b3d_utils.draw_box('Selected Dataset Object will be populated', col)

        col.separator()
        col.operator(MET_OT_Populate.bl_idname)
        
        col.separator(factor=2)
        b3d_utils.draw_box('Select Collection', col)

        col.separator()
        col.operator(MET_OT_FinalizeContent.bl_idname)