from bpy.types  import Context, Panel

from ..         import b3d_utils
from ..main_gui import MapGenPanel_DefaultProps, MET_PT_MapGenMainPanel

from .ops       import MET_OT_CreateTransitionMatrix, MET_OT_GenerateChain, MET_OT_EnableMarkovStats, MET_OT_DisableMarkovStats
from .props     import get_markov_chains_prop


# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_idname = 'MET_PT_MarkovChains'
    bl_label = 'Markov Chains'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        markov = get_markov_chains_prop(_context)

        col = layout.column(align=True)

        b3d_utils.draw_generic_list(col, markov, '#markov_chain_list')

        active_mc = markov.get_selected()

        if not active_mc: return

        col = layout.column(align=True)
        col.prop(active_mc, 'collection')

        col.separator(factor=2)
        col.operator(MET_OT_CreateTransitionMatrix.bl_idname)

        col.separator(factor=2)
        if active_mc.has_transition_matrix():
            col.prop(active_mc, 'length')
            col.prop(active_mc, 'seed')
            col.prop(active_mc, 'collision_height')
            col.prop(active_mc, 'collision_radius')
            col.prop(active_mc, 'angle_range')
            col.prop(active_mc, 'angle_step')
            
            col.prop(active_mc, 'align_orientation')
            col.prop(active_mc, 'random_angle')

            col.separator()
            col.operator(MET_OT_GenerateChain.bl_idname)


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

        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()

        if not item: return
        if not item.has_transition_matrix(): 
            b3d_utils.draw_box('Selected Markov Chain has no transition matrix', layout)
            return

        col.separator()
        col.prop(item, 'from_state')
        col.prop(item, 'to_state')

