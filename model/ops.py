from bpy.types  import Operator, Context
from bpy.props  import *

from .markov    import *
from .props     import get_markov_chains 


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
    bl_idname = 'medge_markov_model.create_transition_matrix'
    bl_label = 'Create Transition Matrix'


    def execute(self, context: Context):
        chains = get_markov_chains(context)
        item = chains.get_selected()
        item.create_transition_matrix(context)
        return {'FINISHED'}
        

# -----------------------------------------------------------------------------
class MET_OT_GenerateChain(Operator):
    bl_idname = 'medge_markov_model.generate_chain'
    bl_label = 'Generate Chain'


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


