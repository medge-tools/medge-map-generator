from bpy.types  import Operator, Context

from .props import get_markov_chains_prop
from .      import stats

# -----------------------------------------------------------------------------
stats_state = False

def is_stats_enabled():
    global stats_state
    return stats_state


def set_stats_state(state: bool):
    global stats_state
    stats_state = state


# -----------------------------------------------------------------------------
class MET_OT_EnableMarkovStats(Operator):
    bl_idname = 'medge_markov.enable_markov_statistics'
    bl_label  = 'Enable Statistics'


    @classmethod
    def poll(cls, _context:Context):
        return not is_stats_enabled()


    def execute(self, context: Context):
        stats.add_handle(context)
        context.area.tag_redraw()
        set_stats_state(True)
        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_DisableMarkovStats(Operator):
    bl_idname = 'medge_markov.disable_markov_statistics'
    bl_label  = 'Disable Statistics'


    @classmethod
    def poll(cls, _context:Context):
        return is_stats_enabled()


    def execute(self, _context:Context):
        stats.remove_handle()
        _context.area.tag_redraw()
        set_stats_state(False)
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
    bl_idname = 'medge_markov.create_transition_matrix'
    bl_label  = 'Create Transition Matrix'


    def execute(self, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        item.create_transition_matrix()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_GenerateChain(Operator):
    bl_idname = 'medge_markov.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        return item.has_transition_matrix()


    def execute(self, _context:Context):
        chains = get_markov_chains_prop(_context)
        item = chains.get_selected()
        item.generate_chain()
        return {'FINISHED'}        
      