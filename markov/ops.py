from bpy.types  import Operator, Context
from bpy.props  import *

from .stats     import MarkovChainStats
from .props     import *
from .chains    import Capsule


# -----------------------------------------------------------------------------
vis_is_enabled = False

def is_vis_enabled():
    global vis_is_enabled
    return vis_is_enabled


def set_vis_enabeld(state: bool):
    global vis_is_enabled
    vis_is_enabled = state


# -----------------------------------------------------------------------------
class MET_OT_EnableMarkovStats(Operator):
    bl_idname = 'medge_markov_model.enable_markov_statistics'
    bl_label  = 'Enable Statistics'


    @classmethod
    def poll(cls, context: Context):
        return not is_vis_enabled()


    def execute(self, context: Context):
        MarkovChainStats().add_handle(context)
        context.area.tag_redraw()
        set_vis_enabeld(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableMarkovStats(Operator):
    bl_idname = 'medge_markov_model.disable_markov_statistics'
    bl_label  = 'Disable Statistics'


    @classmethod
    def poll(cls, context: Context):
        return is_vis_enabled()


    def execute(self, context: Context):
        MarkovChainStats().remove_handle()
        context.area.tag_redraw()
        set_vis_enabeld(False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
    bl_idname = 'medge_markov_model.create_transition_matrix'
    bl_label  = 'Create Transition Matrix'


    def execute(self, context: Context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        item.create_transition_matrix(context)
        return {'FINISHED'}
        

# -----------------------------------------------------------------------------
class MET_OT_GenerateChain(Operator):
    bl_idname = 'medge_markov_model.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        return item.has_transition_matrix


    def execute(self, context: Context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        item.generate_chain(context)
        return {'FINISHED'}        