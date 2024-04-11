from bpy.types  import Context, Panel

from ..main_gui  import *
from .ops        import MET_OT_Populate
from .props      import get_modules
from ..b3d_utils import draw_generic_list 

# -----------------------------------------------------------------------------
class MET_PT_Populate(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_label = 'Populate'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        modules = get_modules(_context)

        col = layout.column(align=True)

        col.separator()
        
        draw_generic_list(col, modules, '#modules')

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

