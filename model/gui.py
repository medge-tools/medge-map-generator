from bpy.types  import Context, Panel

from .ops       import *
from .          import props


# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'
    bl_label = 'Markov Chains'

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        chains = props.get_markov_chains(context)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.template_list('MET_UL_GenericList', 'markov_chain_list', chains, 'items', chains, 'selected_item_idx', rows=4)
        col = row.column(align=True)
        col.operator(MET_OT_Add_MarkovModel.bl_idname, icon='ADD', text='')
        col.operator(MET_OT_Remove_MarkovModel.bl_idname, icon='REMOVE', text='')
        col.operator(MET_OT_Move_MarkovModel.bl_idname, icon='TRIA_UP', text='').direction = 'UP'
        col.operator(MET_OT_Move_MarkovModel.bl_idname, icon='TRIA_DOWN', text='').direction = 'DOWN'
        col.operator(MET_OT_Clear_MarkovModel.bl_idname, icon='TRASH', text='')

        item = chains.get_selected()

        if not item: return

        col = layout.column(align=True)
        col.prop(item, 'collection')

        col.separator(factor=2)

        col.operator(MET_OT_CreateTransitionMatrix.bl_idname)



