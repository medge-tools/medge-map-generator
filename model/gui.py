from bpy.types  import Context, Panel

from ..gui          import *
from .ops           import *
from .props         import get_markov_chains
from ..b3d_utils    import draw_generic_list_ops

# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(MapGenMainPanel, Panel):
    bl_parent_id = MET_PT_MapGenMainPanel.bl_idname
    bl_label = 'Markov Chains'

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        chains = get_markov_chains(context)

        col = layout.column(align=True)

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
            col.prop(item, 'spacing')

            col.separator()
            col.operator(MET_OT_GenerateChain.bl_idname)