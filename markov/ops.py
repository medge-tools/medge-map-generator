from bpy.types  import Operator, Context
from bpy.props  import *

from .props import *
from .      import stats

# -----------------------------------------------------------------------------
vis_state = False

def is_vis_enabled():
    global vis_state
    return vis_state


def set_vis_state(state: bool):
    global vis_state
    vis_state = state


# -----------------------------------------------------------------------------
class MET_OT_EnableMarkovStats(Operator):
    bl_idname = 'medge_markov.enable_markov_statistics'
    bl_label  = 'Enable Statistics'


    @classmethod
    def poll(cls, context: Context):
        return not is_vis_enabled()


    def execute(self, context: Context):
        stats.add_handle(context)
        context.area.tag_redraw()
        set_vis_state(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableMarkovStats(Operator):
    bl_idname = 'medge_markov.disable_markov_statistics'
    bl_label  = 'Disable Statistics'


    @classmethod
    def poll(cls, context: Context):
        return is_vis_enabled()


    def execute(self, context: Context):
        stats.remove_handle()
        context.area.tag_redraw()
        set_vis_state(False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
    bl_idname = 'medge_markov.create_transition_matrix'
    bl_label  = 'Create Transition Matrix'


    def execute(self, context: Context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        item.create_transition_matrix()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_GenerateChain(Operator):
    bl_idname = 'medge_markov.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        return item.has_transition_matrix


    def execute(self, context: Context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        item.generate_chain()
        return {'FINISHED'}        
    

    
