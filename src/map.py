import bpy
from bpy.types import Context, Scene, Object, Collection, Operator, PropertyGroup, Panel
from bpy.props import PointerProperty, BoolProperty, IntProperty

import numpy     as     np
from itertools   import product
from collections import UserList
from datetime    import datetime
from time        import perf_counter

from .gui        import MEdgeToolsPanel, GenerateTab
from ..          import b3d_utils
from ..b3d_utils import new_collection
from .movement   import State
from .markov     import MET_PG_generated_chain, get_markov_chains_prop
from .modules    import CurveModule, MET_PG_curve_module_collection, get_curve_module_groups_prop


# -----------------------------------------------------------------------------
class MET_SCENE_PG_map_gen_settings(PropertyGroup):
    
    def __str__(self):
        return f"\
{self.seed}_\
{str(self.align_orientation)[0]}_\
{str(self.resolve_intersection)[0]}_\
{self.max_resolve_attempts}\
"

    # Gen settings
    seed:                 IntProperty(name='Seed', default=2024, min=0)
    length:               IntProperty(name='Length', default=0, min=-1, description='-1 will generate the full chain')

    align_orientation:    BoolProperty(name='Align Orientation')
    resolve_intersection: BoolProperty(name='Resolve Intersection', default=True)
    max_resolve_attempts: IntProperty(name='Max Resolve Attempts', default=50, min=1)

    # Export settings
    skydome:              PointerProperty(type=Object, name='Skydome')
    only_top:             BoolProperty(name='Only Top')


# -----------------------------------------------------------------------------
# Map
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class Map(UserList):
    """` list[CurveModule] `"""

    def __init__(self, _data=None, _settings:MET_SCENE_PG_map_gen_settings=None):
        super().__init__(_data)

        self.obj:Object = None
        self.settings = _settings
        self.debug = True

        np.random.seed(self.settings.seed)

        # Only contains indices that point to candidates to resolve intersection
        self.resolve_candidates:list[int] = []
        # If the CurveModule is a resolve candidate, store the index to resolve_candidates, otherwise it is 0
        self.is_candidate:list[int] = []


    def append(self, _item:CurveModule):
        super().append(_item)
        
        if (_item.state == State.Walking or 
            _item.state == State.WallRunningLeft or 
            _item.state == State.WallRunningRight):
            self.resolve_candidates.append(len(self.data) - 1)
            self.is_candidate.append(len(self.resolve_candidates) - 1)

        else:
            self.is_candidate.append(0)


    def prepare(self, 
                _states:list[int],
                _module_groups:list[MET_PG_curve_module_collection]):
        
        for state in _states:
            if not (mn := _module_groups[state].collect_curve_names()): 
                    continue

            cm = CurveModule(state, mn)
            self.append(cm)


    def build(self, _collection:Collection) -> tuple[float, float, int]:
        """ Returns the total build time and the total time resolving intersections """
        # Prepare modules
        cm:CurveModule
        for k, cm in enumerate(self.data):
            cm.prepare(k, _collection)

        # Build modules
        if self.debug: print('Building map...')

        start_time = perf_counter()

        resolve_time = 0
        total_lowest_hits = 0

        for k, cm in enumerate(self.data):
            if self.debug: print(f'Iteration: {k} / {len(self.data) - 1}')
            cm.next_module()

            # Align
            self.align_module(k)

            # Check intersections
            if self.check_intersection(k) == 0: 
                continue

            # Resolve intersections
            if not self.settings.resolve_intersection: 
                continue

            s = perf_counter()
            total_lowest_hits += self.resolve_intersections(k)
            e = perf_counter()

            resolve_time += e - s

        end_time = perf_counter()

        return end_time - start_time, resolve_time, total_lowest_hits


    def check_intersection(self, _index:int) -> int:
        cm1 = self.data[_index]
            
        total = 0

        for k in range(_index - 1, -1, -1):
            if _index == k: continue

            cm2 = self.data[k]

            if (hits := cm1.intersect(cm2)):
                total += len(hits)

        return total


    def check_intersections_range(self, _start:int) -> int:
        total = 0
        
        for j in range(_start, -1, -1):
            total += self.check_intersection(j)

        return total


    def resolve_intersections(self, _start:int) -> int:
        if self.debug: print(f'Resolving intersections...')
        
        module_names_indices:list[list[int]] = []
        current_candidates:list[int] = []

        # Find resolve candidate
        for k in range(_start, -1, -1):
            if (start_candidate := self.is_candidate[k]) != 0:
                break

        end_resolving = False
        lowest_hits = float('inf')
        best_candidates = None
        best_permutation = None

        # Try different candidates
        curr_iteration = 0

        for k in range(start_candidate, -1, -1):

            i = self.resolve_candidates[k]
            cm:CurveModule = self.data[i]

            module_names_indices.append(range(len(cm.module_names)))
            current_candidates.append(i)
        
            for permutation in product(*module_names_indices):
                self.apply_configuration(current_candidates, permutation)

                hits = self.check_intersections_range(_start)
                if self.debug:  print(f'Hits: {hits}')

                curr_iteration += 1

                if hits < lowest_hits:
                    lowest_hits = hits
                    best_candidates = current_candidates
                    best_permutation = permutation

                if hits == 0 or curr_iteration >= self.settings.max_resolve_attempts:
                    end_resolving = True
                    break
        
            if end_resolving:
                break

        if lowest_hits != 0:
            print('Applying best permutation')
            self.apply_configuration(best_candidates, best_permutation)

        return lowest_hits


    def apply_configuration(self, _indices:list[int], _permutation:tuple[int, ...]) -> int:
        lowest_idx = len(self.data) - 1
        names = []

        # Apply permutation
        for i, p in zip(_indices, _permutation):
            cm:CurveModule = self.data[i]
            cm.next_module(p)
            names.append(cm.curve.name)

            if i < lowest_idx: 
                lowest_idx = i

        if self.debug: print(f'Applied permutation: {_permutation}, Objects: {names}')

        # Align modules
        for k in range(lowest_idx, len(self.data), 1):
            self.align_module(k)


    def align_module(self, _index:int):
        cm:CurveModule = self.data[_index]
        if not cm.curve: return

        if _index == 0:
            cm.align(None)
        else:
            cm.align(self.data[_index - 1], self.settings.align_orientation)


# -----------------------------------------------------------------------------
def filter_states(_states:list[int], _settings:MET_SCENE_PG_map_gen_settings) -> list[int]:
    if bpy.context.object:
        bpy.ops.object.mode_set(mode='OBJECT')
    
    b3d_utils.deselect_all_objects()

    new_states = []

    k = -1
    while True:
        k += 1
        
        if k >= len(_states):
            break

        if (length := _settings.length) != -1 and k >= length:
            break

        state = _states[k]

        # Handle specific cases:
        # Handle state compared to the next state
        if (n := k + 1) < len(_states):
            next_state = _states[n]

            # Case 1: Jump -> WallClimbing
            # To go into WallClimbing the jump distance should be short, but the some jump modules can be to long. To solve this we just ignore the jump.
            if state == State.Jump:
                if next_state == State.WallClimbing:
                    continue
            # Case 2: Jump -> WallRunningLeft or WallRunningRight
            # Similar to Case 1, where the jump distance should be short.
                if (next_state == State.WallRunningLeft or 
                    next_state == State.WallRunningRight):
                    continue

            # Case 3: WallClimbing -> WallClimb180TurnJump
            # To do a WallClimb180TurnJump the height of the wall can be longer than the player can climb. WallClimbing can be followed by GrabPullUp. Therefore, we ignore WallClimbing and WallClimb180TurnJump should have its own wall.
            elif state == State.WallClimbing:
                if next_state == State.WallClimb180TurnJump:
                    continue

        # Handle state compared to the previous state
        if (p := k - 1) >= 0:
            prev_state = _states[p]

            # Case 4: WallClimb180TurnJump -> Falling
            # A falling curve can go quite low and could end up back where the player came from. In this case, Falling will be ignored.
            if state == State.Falling:
                if prev_state == State.WallClimb180TurnJump:
                    continue

        # Case 5: WallRunning[Left, Right] > WallRunJump > WallClimbing > WallClimbing180Jump
        # If you want to perform a WallClimbing180Jump after a WallRun, then you cannot be wall running for long and you are always jumping perpendicular after a wall run. These properties are not implicitly adhered to when choosing modules from each state and can result in a non-solvable level segment. To solve this, extra states have been made, namely: `WallRunningLeftWallClimb180TurnJump` and `WallRunningRightWallClimb180TurnJump`.
        if ((left := state == State.WallRunningLeft) or (right := state == State.WallRunningRight)):
            if k + 3 < len(_states):
                if (_states[k + 1] == State.WallRunJump and
                    _states[k + 2] == State.WallClimbing and
                    _states[k + 3] == State.WallClimb180TurnJump):

                    if left: 
                        state = State.WallRunningLeftWallClimb180TurnJump.value
                    elif right: 
                        state = State.WallRunningRightWallClimb180TurnJump.value

                    k += 3
        
        new_states.append(state)

    return new_states


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_generate_map(Operator):
    bl_idname = 'medge_generate.generate_map'
    bl_label = 'Generate Map'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        active_mc = mc.get_selected()
        gen_chain:MET_PG_generated_chain = active_mc.generated_chains.get_selected()

        module_groups = get_curve_module_groups_prop(_context).items

        settings = get_medge_map_gen_settings(_context)
        
        time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        collection = new_collection(f'GENERATED_{active_mc.name}_[{settings}]_{time}')

        states = filter_states(gen_chain.split(), settings)

        map = Map(None, settings)
        map.prepare(states, module_groups)
        map.build(collection)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_generate_map(MEdgeToolsPanel, GenerateTab, Panel):
    bl_label = 'Generate Map'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)
        mc = markov_chains.get_selected()

        if not mc: 
            b3d_utils.draw_box(col, 'No Markov Data')
            return

        chain = mc.get_selected_generated_chain()

        if not chain: 
            b3d_utils.draw_box(col, 'No Generated Chains')
            return

        settings = get_medge_map_gen_settings(_context)

        col.prop(settings, 'seed')
        col.prop(settings, 'length')
        col.prop(settings, 'align_orientation')
        col.prop(settings, 'resolve_intersection')

        if settings.resolve_intersection:
            col.prop(settings, 'max_resolve_attempts')
        
        col.separator(factor=2)
        b3d_utils.draw_box(col, 'Select Generated Chain')

        col.separator() 
        split = col.split(factor=0.07, align=True)
        split.scale_y = 1.4
        split.operator('wm.console_toggle', icon='CONSOLE', text='')
        split.operator(MET_OT_generate_map.bl_idname)


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_medge_map_gen_settings(_context:Context) -> MET_SCENE_PG_map_gen_settings:
    return _context.scene.medge_map_gen_settings


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_map_gen_settings = PointerProperty(type=MET_SCENE_PG_map_gen_settings)


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_map_gen_settings'): del Scene.medge_map_gen_settings