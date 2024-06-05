# from bpy.types import Context, Panel

# from ..         import b3d_utils
# from ..main_gui import MapGenPanel_DefaultProps, MET_PT_MapGenMainPanel
# from .props     import get_module_states_prop, get_module_prop
# from .ops       import MET_OT_InitModules, MET_OT_UpdateActiveStates, MET_OT_Populate, MET_OT_PrepareForExport, MET_OT_ExportT3D


# # -----------------------------------------------------------------------------
# class MET_PT_ModuleSettings(MapGenPanel_DefaultProps, Panel):
#     bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
#     bl_label = 'Module Settings'


#     def draw(self, _context:Context):
#         obj = _context.object

#         if not obj: return

#         layout = self.layout
#         layout.use_property_decorate = False
#         layout.use_property_split = True

#         col = layout.column(align=True)

#         module = get_module_prop(obj)

#         col.prop(module, 'can_overextend')
#         col.prop(module, 'curve_deform')

#         if module.curve_deform:
#             col.prop(module, 'curve_deform_z')


# # -----------------------------------------------------------------------------
# class MET_PT_Populate(MapGenPanel_DefaultProps, Panel):
#     bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
#     bl_label = 'Populate'


#     def draw(self, _context:Context):
#         layout = self.layout
#         layout.use_property_decorate = False
#         layout.use_property_split = True
        
#         module_prop = get_module_states_prop(_context)

#         col = layout.column(align=True)
#         col.separator()
        
#         row = col.row(align=True)
#         row.template_list('MET_UL_ModuleList', '#modules', module_prop, 'items', module_prop, 'selected_item_idx', rows=5)

#         col.separator()
#         col.operator(MET_OT_InitModules.bl_idname)
#         col.operator(MET_OT_UpdateActiveStates.bl_idname)
        
#         module = module_prop.get_selected()

#         if not module: return

#         col.separator(factor=2)
#         col = layout.column(align=True)
        
#         col.prop(module, 'only_at_chain_start')
#         col.prop(module, 'use_collection')
#         col.separator()

#         if module.use_collection:
#             col.prop(module, 'collection')
#         else:
#             col.prop(module, 'object')

#         col.separator(factor=2)
#         b3d_utils.draw_box('Select Dataset Object', col)

#         col.separator()
#         col.operator(MET_OT_Populate.bl_idname)
        
#         col.separator(factor=2)
#         b3d_utils.draw_box('Select Populated Collection', col)

#         col.separator()
#         col.operator(MET_OT_PrepareForExport.bl_idname)
#         col.operator(MET_OT_ExportT3D.bl_idname)