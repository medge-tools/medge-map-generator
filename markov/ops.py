from bpy.types  import Operator, Context
from bpy.props  import *

from .props import *
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
        chains = get_markov_chains(_context)
        item = chains.get_selected()
        item.create_transition_matrix()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_GenerateChain(Operator):
    bl_idname = 'medge_markov.generate_chain'
    bl_label  = 'Generate Chain'


    @classmethod
    def poll(cls, _context:Context):
        chains = get_markov_chains(_context)
        item = chains.get_selected()
        return item.has_transition_matrix()


    def execute(self, _context:Context):
        chains = get_markov_chains(_context)
        item = chains.get_selected()
        item.generate_chain()
        return {'FINISHED'}        
    

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# from .chains import Chain

# class MET_OT_CapsuleCollisionTest(Operator):
#     bl_idname = 'medge_markov.collision_test'
#     bl_label  = 'Collision Test'


#     def execute(self,  _context:Context):
#         objs = _context.selected_objects
#         obj1 = objs[0]
#         obj2 = objs[1]

#         v1s = []
#         for v in obj1.data.vertices:
#             v1s.append(obj1.matrix_world @ v.co)

#         v2s = []
#         for v in obj2.data.vertices:
#             v2s.append(obj2.matrix_world @ v.co)

#         c1 = Chain(1, v1s, 1, False)
#         c2 = Chain(1, v2s, 1, False)
#         print(f'My: {obj1.name}, Other: {obj2.name}')

#         hit = c1.collides(c2, True)
#         if hit:
#             print(hit.result)
#             print(f'Direction: {hit.direction}')
#             print(f'My point: {hit.my_point}')
#             print(f'Other point: {hit.other_point}')
#         else:
#             print('No hit')

#         return {'FINISHED'} 
    
