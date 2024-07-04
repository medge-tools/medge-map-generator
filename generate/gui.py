from bpy.types import Context, Panel

from ..     import b3d_utils
from ..gui  import MEdgeToolsPanel, MET_PT_map_gen_panel

from .ops   import (MET_OT_create_transition_matrix, MET_OT_generate_chain, MET_OT_add_handmade_chain,
                    MET_OT_init_module_collections, MET_OT_add_curve_module_to_group, MET_OT_add_collision_volume,
                    MET_OT_generate_map, MET_OT_generate_all_maps, MET_OT_prepare_for_export, MET_OT_export_t3d)
from .props import get_markov_chains_prop, get_curve_module_groups_prop, get_curve_module_prop, get_medge_map_gen_settings

# -----------------------------------------------------------------------------
class GenerateTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname

    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'GENERATE'


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_markov_chains_data(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Dataset Collections'
    

    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)

        b3d_utils.draw_generic_list(col, markov_chains, '#markov_chain_list')

        mc = markov_chains.get_selected()

        if not mc: return

        col = layout.column(align=True)
        col.prop(mc, 'collection')

        col.separator(factor=2)

        col.operator(MET_OT_create_transition_matrix.bl_idname, text=MET_OT_create_transition_matrix.bl_label)

        col.separator(factor=2)
        if mc.has_transition_matrix():
            col.prop(mc, 'length')
            col.prop(mc, 'seed')

            col.separator()
            col.operator(MET_OT_generate_chain.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_markov_chains_generate(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Generated Chains'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)
        mc = markov_chains.get_selected()
        gen_chains = mc.generated_chains

        b3d_utils.draw_generic_list(col, gen_chains, '#generated_chain_list', 3, {'REMOVE', 'MOVE', 'CLEAR'})

        col.separator()
        row = col.row(align=True)
        row.prop(mc, 'handmade_chain')
        row.operator(MET_OT_add_handmade_chain.bl_idname, text='', icon='ADD')

        active_chain = gen_chains.get_selected()

        if not active_chain: return

        col.separator()
        col.prop(mc, 'show_chain', expand=True)

        if mc.show_chain:
            col.separator(factor=2)
            b3d_utils.multiline_text(_context, col, active_chain.chain)


# -----------------------------------------------------------------------------
# Modules
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_modules(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Modules'


    def draw(self, _context:Context):
        markov_chains = get_markov_chains_prop(_context)
        active_mc = markov_chains.get_selected()

        if not active_mc: return

        gen_chains = active_mc.generated_chains
        active_chain = gen_chains.get_selected()

        if not active_chain: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        module_groups = get_curve_module_groups_prop(_context)
        
        row = col.row(align=True)
        row.template_list('MET_UL_curve_module_group_draw', '#modules', module_groups, 'items', module_groups, 'selected_item_idx', rows=3)
        
        col.separator()
        col.operator(MET_OT_init_module_collections.bl_idname)

        if len(module_groups.items) == 0: return

        col.separator(factor=2)

        mg = module_groups.get_selected()

        row = col.row(align=True)

        row.prop(mg, 'collection')
        row.operator(MET_OT_add_curve_module_to_group.bl_idname, text='', icon='ADD')


# -----------------------------------------------------------------------------
# Generate Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_generate_map(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Generate Map'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        settings = get_medge_map_gen_settings(_context)

        col.prop(settings, 'seed')
        col.prop(settings, 'align_orientation')
        col.prop(settings, 'resolve_intersection')

        if settings.resolve_intersection:
            col.prop(settings, 'max_depth')
            col.prop(settings, 'max_angle')
            col.prop(settings, 'angle_step')
            col.prop(settings, 'random_angles')

        col.separator(factor=2)
        b3d_utils.draw_box(col, 'Select Generated Chain')

        col.separator()
        col.operator(MET_OT_generate_map.bl_idname)
        col.operator(MET_OT_generate_all_maps.bl_idname)


# -----------------------------------------------------------------------------
# Generate Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_export_map(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Export'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Select Collection')

        settings = get_medge_map_gen_settings(_context)

        col.separator()
        col.prop(settings, 'only_top')
        col.prop(settings, 'skydome')
        col.separator()
        col.operator(MET_OT_prepare_for_export.bl_idname)
        col.operator(MET_OT_export_t3d.bl_idname)


# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_curve_module(MEdgeToolsPanel, Panel):
    bl_label = 'Curve Module'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj and obj.type == 'CURVE'


    def draw(self, _context:Context):
        obj = _context.object

        if not obj: return

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Use the curve as parent for any level component')
        col.separator()

        row = col.row(align=True)

        cm = get_curve_module_prop(obj)
        row.prop(cm, 'collision_volume')
        row.operator(MET_OT_add_collision_volume.bl_idname, text='', icon='ADD')
