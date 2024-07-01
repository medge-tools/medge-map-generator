from bpy.types import Context, Panel

from ..gui      import MEdgeToolsPanel, MET_PT_map_gen_panel
from ..         import b3d_utils
from .props     import get_dataset_prop
from .ops       import (MET_OT_convert_to_dataset, MET_OT_set_state, MET_OT_select_states, MET_OT_select_transitions, 
                        MET_OT_enable_dataset_vis, MET_OT_disable_dataset_vis, is_vis_enabled, 
                        MET_OT_resolve_overlap, MET_OT_extract_curves)


# -----------------------------------------------------------------------------
class MET_PT_dataset(Panel, MEdgeToolsPanel):
    bl_idname = 'MET_PT_dataset_panel'
    bl_parent_id = MET_PT_map_gen_panel.bl_idname
    bl_label = 'Dataset'


    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'DATASET'
    
    
    def draw(self, _context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        obj = _context.active_object

        if not obj: 
            b3d_utils.draw_box(layout, 'Select Object')
            return

        col = layout.column(align=True)

        if not (dataset := get_dataset_prop(obj)): 
            col.operator(MET_OT_convert_to_dataset.bl_idname)
            b3d_utils.draw_box(layout, 'Make sure it is a polyline')
            return
        else:
            col.operator(MET_OT_convert_to_dataset.bl_idname, text='Update Attributes')

        settings = dataset.get_ops_settings()
        
        if not settings: return

        col.separator(factor=2)
        col.prop(settings, 'new_state')
        col.separator()
        col.operator(MET_OT_set_state.bl_idname)
        
        col.separator()
        col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_select_states.bl_idname)
        
        col.separator()
        col.prop(settings, 'use_filter')
        if settings.use_filter:
            col.prop(settings, 'restrict')
            col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_select_transitions.bl_idname)
        col.operator(MET_OT_resolve_overlap.bl_idname)
        col.operator(MET_OT_extract_curves.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_dataset_vis(Panel, MEdgeToolsPanel):
    bl_parent_id = MET_PT_dataset.bl_idname
    bl_label = 'Visualization'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, _context: Context):        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)
        row = col.row(align=True)

        row.operator(MET_OT_enable_dataset_vis.bl_idname, text='Enable')
        row.operator(MET_OT_disable_dataset_vis.bl_idname, text='Disable')
        
        if not is_vis_enabled(): 
            box = layout.box()
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text='Visualization renders in Edit Mode')
            return

        if not (obj := _context.active_object): return
        if not (dataset := get_dataset_prop(obj)): return

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
