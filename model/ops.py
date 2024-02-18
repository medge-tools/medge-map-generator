from bpy.types  import Operator, Context
from bpy.props  import *

from .markov    import *
from .          import props 


# -----------------------------------------------------------------------------
class MET_OT_CreateTransitionMatrix(Operator):
    bl_idname = 'medge_markov_model.create_transition_matrix'
    bl_label = 'Create Transition Matrix'


    def execute(self, context: Context):
        chains = props.get_markov_chains(context)
        item = chains.get_selected()
        item.create_transition_matrix(context)
        return {'FINISHED'}
        

# -----------------------------------------------------------------------------
# COLLECTION OPERATORS
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_Add_MarkovModel(Operator):
    bl_idname = 'medge_markov_model.add_markov_model'
    bl_label = 'Add Markov Model'


    def execute(self, context: Context):
        chains = props.get_markov_chains(context)
        chains.add()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_Remove_MarkovModel(Operator):
    bl_idname = 'medge_markov_model.remove_markov_model'
    bl_label = 'Remove Markov Model'
    bl_options = {'UNDO'}
    

    def execute(self, context: Context):
        chains = props.get_markov_chains(context)
        chains.remove_selected()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_Clear_MarkovModel(Operator):
    bl_idname = 'medge_markov_model.clear_markov_model'
    bl_label = 'Clear Markov Models'
    bl_options = {'UNDO'}


    def execute(self, context: Context):
        chains = props.get_markov_chains(context)
        chains.clear()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_Move_MarkovModel(Operator):
    bl_idname = 'dib.move_shape'
    bl_label = 'Move Shape'
    

    direction : EnumProperty(items=(
        ('UP', 'Up', ''),
        ('DOWN', 'Down', ''),
    ))


    def execute(self, context: Context):
        chains = props.get_markov_chains(context)
        dir = (-1 if self.direction == 'UP' else 1)
        chains.move(dir)
        return {'FINISHED'}
