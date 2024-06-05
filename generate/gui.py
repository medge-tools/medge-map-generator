from bpy.types  import Context, Panel

from ..             import b3d_utils
from ..gui_defaults import MapGenPanel_DefaultProps

from .ops   import (MET_OT_CreateTransitionMatrix, MET_OT_GenerateChain, MET_OT_EnableMarkovStats, MET_OT_DisableMarkovStats,
                    MET_OT_InitModules, MET_OT_UpdateActiveStates, MET_OT_InitCapsuleData, MET_OT_GenerateMap, MET_OT_PrepareForExport, MET_OT_ExportT3D)
from .props import get_markov_chains_prop, get_module_groups_prop


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(MapGenPanel_DefaultProps, Panel):
    bl_idname = 'MET_PT_MarkovChains'
    bl_label = 'Map Gen: Markov Chains'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov = get_markov_chains_prop(_context)

        # ---------------------------------------------------------------------
        col.label(text='Dataset Collections')
        col.separator()
        b3d_utils.draw_generic_list(col, markov, '#markov_chain_list')

        active_mc = markov.get_selected()

        if not active_mc: return

        col = layout.column(align=True)
        col.prop(active_mc, 'collection')

        col.separator(factor=2)

        col.operator(MET_OT_CreateTransitionMatrix.bl_idname, text=MET_OT_CreateTransitionMatrix.bl_label)

        col.separator(factor=2)
        if active_mc.has_transition_matrix():
            col.prop(active_mc, 'length')
            col.prop(active_mc, 'seed')

            col.separator()
            col.operator(MET_OT_GenerateChain.bl_idname)

        gen_chains = active_mc.generated_chains

        
        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Generated Chains')
        col.separator()
        b3d_utils.draw_generic_list(col, gen_chains, '#generated_chain_list', 3, {'REMOVE', 'MOVE', 'CLEAR'})

        active_chain = gen_chains.get_selected()

        if not active_chain: return

        col.separator()
        col.prop(active_mc, 'show_chain')

        if active_mc.show_chain:
            col.separator(factor=2)
            b3d_utils.multiline_text(_context, col, active_chain.chain)
            col.separator(factor=2)


# -----------------------------------------------------------------------------
class MET_PT_MarkovChainsStats(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MarkovChains.bl_idname
    bl_label = 'Statistics'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)
        row = col.row(align=True)

        row.operator(MET_OT_EnableMarkovStats.bl_idname, text='Enable')
        row.operator(MET_OT_DisableMarkovStats.bl_idname, text='Disable')

        markov = get_markov_chains_prop(_context)
        item = markov.get_selected()

        if not item: return
        if not item.has_transition_matrix(): 
            b3d_utils.draw_box('Selected Dataset Collection has no transition matrix', layout)
            return

        col.separator()
        col.prop(item, 'from_state')
        col.prop(item, 'to_state')


# -----------------------------------------------------------------------------
# Generate Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_GenerateMap(MapGenPanel_DefaultProps, Panel):
    bl_idname = 'MET_PT_GenerateMap'
    bl_label = 'Map Gen: Generate Map'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)
        
        
        # ---------------------------------------------------------------------
        col.label(text='Module Groups')
        col.separator()

        module_groups = get_module_groups_prop(_context)
        
        row = col.row(align=True)
        row.template_list('MET_UL_ModuleList', '#modules', module_groups, 'items', module_groups, 'selected_item_idx', rows=3)
        
        col.separator()
        col.operator(MET_OT_InitModules.bl_idname)
        col.operator(MET_OT_UpdateActiveStates.bl_idname)

        if len(module_groups.items) == 0: return

        col.separator(factor=2)

        module = module_groups.get_selected()

        col.prop(module, 'use_collection')
        col.separator()

        if module.use_collection:
            col.prop(module, 'collection')
        else:
            col.prop(module, 'object')

        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Settings')
        col.separator()
        
        col.operator(MET_OT_InitCapsuleData.bl_idname)
        col.separator()
        
        col.prop(module_groups, 'seed')
        col.prop(module_groups, 'align_orientation')
        col.prop(module_groups, 'resolve_collisions')

        if module_groups.resolve_collisions:
            col.separator()
            col.prop(module_groups, 'capsule_height')
            col.prop(module_groups, 'capsule_radius', text='Radius')
            col.prop(module_groups, 'capsule_spacing', text='Spacings')
            col.separator()
            col.prop(module_groups, 'max_depth')
            col.prop(module_groups, 'max_angle')
            col.prop(module_groups, 'angle_step')
            col.prop(module_groups, 'random_angles')
            col.prop(module_groups, 'debug_capsules')

        
        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Dataset Collections')
        col.separator()

        markov_chains = get_markov_chains_prop(_context)

        b3d_utils.draw_generic_list(col, markov_chains, '#markov_chain_list')

        active_mc = markov_chains.get_selected()

        if not active_mc: return

        gen_chains = active_mc.generated_chains

        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Generated Chains')
        col.separator()
        b3d_utils.draw_generic_list(col, gen_chains, '#generated_chain_list', 3, {'REMOVE', 'MOVE', 'CLEAR'})

        active_chain = gen_chains.get_selected()

        if not active_chain: return

        col.separator()
        col.operator(MET_OT_GenerateMap.bl_idname)
        
        col.separator(factor=2)
        b3d_utils.draw_box('Select Generated Map Collection', col)

        col.separator()
        col.operator(MET_OT_PrepareForExport.bl_idname)
        col.operator(MET_OT_ExportT3D.bl_idname)