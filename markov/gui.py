from bpy.types  import Context, Panel

from ..b3d_utils    import draw_generic_list_ops
from ..main_gui     import MapGenPanel_DefaultProps, MET_PT_MapGenMainPanel

from .ops           import *
from .props         import get_markov_chains

classes = []


# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_idname = 'MET_PT_MarkovChains'
    bl_label = 'Markov Chains'


    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        chains = get_markov_chains(context)

        col = layout.column(align=True)


        col.operator(MET_OT_Test.bl_idname)

        row = col.row(align=True)
        row.template_list('B3D_UL_GenericList', '#markov_chain_list', chains, 'items', chains, 'selected_item_idx', rows=4)
        
        col = row.column(align=True)
        draw_generic_list_ops(col, chains)

        item = chains.get_selected()

        if not item: return

        col = layout.column(align=True)
        col.prop(item, 'collection')

        col.separator(factor=2)
        col.operator(MET_OT_CreateTransitionMatrix.bl_idname)

        col.separator()
        if item.has_transition_matrix:
            col.prop(item, 'length')
            col.prop(item, 'seed')

            col.separator()
            col.operator(MET_OT_GenerateChain.bl_idname)

classes.append(MET_PT_MarkovChains)


# -----------------------------------------------------------------------------
class MET_PT_MarkovChainsStats(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_MarkovChains.bl_idname
    bl_label = 'Statistics'

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)
        row = col.row(align=True)
        
        row.operator(MET_OT_EnableMarkovStats.bl_idname, text='Enable')
        row.operator(MET_OT_DisableMarkovStats.bl_idname, text='Disable')

        if not is_vis_enabled(): return

        chains = get_markov_chains(context)
        item = chains.get_selected()

        if not item: return
        if not item.has_transition_matrix: 
            box = layout.box()
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text='Selected Markov Chain has no transition matrix')
            return

        col.separator()
        col.prop(item, 'from_state')
        col.prop(item, 'to_state')


classes.append(MET_PT_MarkovChainsStats)
