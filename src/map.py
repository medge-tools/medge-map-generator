import bpy
from bpy.types import Operator, Context, Scene, Object, Collection, Operator, PropertyGroup, Panel
from bpy.props import PointerProperty, BoolProperty, IntProperty
from mathutils import Vector

import numpy     as     np
from itertools   import product
from math        import pi
from collections import UserList
from datetime    import datetime

from .gui       import MEdgeToolsPanel, GenerateTab, ExportTab
from ..          import b3d_utils
from ..b3d_utils import get_active_collection, new_collection
from .movement   import State
from .markov     import MET_PG_generated_chain, get_markov_chains_prop
from .modules    import CurveModule, MET_PG_curve_module_collection


# -----------------------------------------------------------------------------
class MET_SCENE_PG_map_gen_settings(PropertyGroup):
    
    def __str__(self):
        return f"\
{self.seed}_\
{str(self.align_orientation)[0]}_\
{str(self.resolve_intersection)[0]}\
"

    seed:                 IntProperty(name='Seed', default=2024, min=0)
    length:               IntProperty(name='Length', default=-1, min=-1, description='-1 will generate the full chain')

    align_orientation:    BoolProperty(name='Align Orientation')
    resolve_intersection: BoolProperty(name='Resolve Intersection', default=True)

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


    def build(self, _collection:Collection, _print:callable):
        cm:CurveModule
        # Prepare modules
        for k, cm in enumerate(self.data):
            cm.prepare(k, _collection)

        # Build modules
        for k, cm in enumerate(self.data):
            if (length := self.settings.length) != -1 and k >= length:
                return

            _print(f'Iteration: {k} / {len(self.data)}')
            cm.next_module()

            # Align
            self.align_module(k)

            # Check intersections
            if self.check_intersection(k) == 0: 
                continue

            # Resolve intersections
            if not self.settings.resolve_intersection: 
                continue
            
            self.resolve_intersections(k)


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
        print(f'Resolving intersections...')
        
        module_names_indices:list[list[int]] = []
        current_candidates:list[int] = []

        # Find resolve candidate
        for k in range(_start, -1, -1):
            if (start_candidate := self.is_candidate[k]) != 0:
                break

        intersections_resolved = False

        # Try different candidates
        for k in range(start_candidate, -1, -1):
            i = self.resolve_candidates[k]
            cm:CurveModule = self.data[i]

            module_names_indices.append(range(len(cm.module_names)))
            current_candidates.append(i)
        
            for permutation in product(*module_names_indices):
                self.apply_configuration(current_candidates, permutation)

                hits = self.check_intersections_range(_start)
                print(f'Hits: {hits}')

                if hits == 0:
                    intersections_resolved = True
                    break
        
            if intersections_resolved:
                break


    def apply_configuration(self, _indices:list[int], _permutation:tuple[int, ...]) -> int:
        print(f'Applied permutation: {_permutation}')
        
        lowest_idx = len(self.data) - 1
        names = []

        # Apply permutation
        for i, p in zip(_indices, _permutation):
            cm:CurveModule = self.data[i]
            cm.next_module(p)
            names.append(cm.curve.name)

            if i < lowest_idx: 
                lowest_idx = i

        print(f'Objects: {names}')

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

        module_groups = get_curve_module_groups_prop(_context)

        settings = get_medge_map_gen_settings(_context)
        
        time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        collection = new_collection(f'POPULATED_{active_mc.name}_[{settings}]_{time}' )

        self.generate(gen_chain, module_groups.items, settings, collection)

        return {'FINISHED'}


    def generate(self, 
                 _gen_chain:MET_PG_generated_chain, 
                 _module_group:list[MET_PG_curve_module_collection], 
                 _settings:MET_SCENE_PG_map_gen_settings, 
                 _target_collection:Collection):
    
        if bpy.context.object:
            bpy.ops.object.mode_set(mode='OBJECT')
        
        b3d_utils.deselect_all_objects()

        # Generation data
        np.random.seed(_settings.seed)

        states = _gen_chain.split()

        map = Map(None, _settings)

        # Instantiate all CurveModules
        for k, str_state in enumerate(states):
            state = int(str_state)

            # Handle specific cases:
            # Handle state compared to the next state
            if (n := k + 1) < len(states):
                next_state = int(states[n])

                # Case 1: Jump -> WallClimbing
                # To go into WallCLimbing the jump distance should be so short we can just ignore it
                if state == State.Jump:
                    if next_state == State.WallClimbing:
                        continue

                # Case 2: WallClimbing -> WallClimb180TurnJump
                # To do a WallClimb180TurnJump the height of the wall can be longer than the player can climb
                # The WallClimb180TurnJump should have its own wall
                elif state == State.WallClimbing:
                    if next_state == State.WallClimb180TurnJump:
                        continue

            # Handle state compared to the previous state
            if (p := k - 1) >= 0:
                prev_state = int(states[p])

                # Case 3: WallClimb180TurnJump -> Falling
                # There are falling modules the could end up back where the player came from
                # Falling should be included in the WallClimb180TurnJump module
                if state == State.Falling:
                    if prev_state == State.WallClimb180TurnJump:
                        continue

            if not (mn := _module_group[state].collect_curve_names()): 
                continue

            cm = CurveModule(state, mn)
            map.append(cm)
            
        # Build the map
        map.build(_target_collection, self.print)

        print('Finished!')

    
    def print(self, _text:str):
        self.report({'INFO'}, _text)


# # -----------------------------------------------------------------------------
# class MET_OT_generate_all_maps(Operator):
#     bl_idname = 'medge_generate.generate_all_maps'
#     bl_label = 'Generate All Maps'
#     bl_options = {'UNDO'}


#     def execute(self, _context:Context):
#         mc = get_markov_chains_prop(_context)
#         active_mc = mc.get_selected()

#         module_groups = get_curve_module_groups_prop(_context)

#         settings = get_medge_map_gen_settings(_context)

#         for  gen_chain in active_mc.generated_chains.items:
#             time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
#             collection = new_collection(f'POPULATED_{active_mc.name}_[{settings}]_{time}' )

#             generate(gen_chain, module_groups.items, settings, collection)

#         return {'FINISHED'}


# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_prepare_for_export(Operator):
    bl_idname = 'medge_generate.prepare_for_export'
    bl_label = 'Prepare For Export'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        settings = get_medge_map_gen_settings(_context)
        self.prepare_for_export(settings, collection)
        return {'FINISHED'}
    

    def prepare_for_export(_settings:MET_SCENE_PG_map_gen_settings, _collection:Collection):
        new_collection = b3d_utils.new_collection('PrepareForExport', _collection)

        # Add player start
        bpy.ops.medge_map_editor.add_actor(type='PLAYER_START')
        ps = bpy.context.object

        b3d_utils.link_object_to_scene(ps, new_collection)
        
        ps.location = Vector((0, 0, 0))

        # Add directional light
        bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 3), scale=(1, 1, 1))
        light = bpy.context.object

        b3d_utils.link_object_to_scene(light, new_collection)

        # Add killvolume
        scale = 500

        bpy.ops.medge_map_editor.add_actor(type='KILL_VOLUME')
        kv = bpy.context.object

        b3d_utils.link_object_to_scene(kv, new_collection)

        kv.location = 0, 0, -50
        kv.scale = scale, scale, 10

        # Add skydome top
        scale = 7000
        bpy.ops.medge_map_editor.add_skydome()
        sd = bpy.context.object

        b3d_utils.link_object_to_scene(sd, new_collection)

        sd.location = 0, 0, 0
        sd.scale = scale, scale, scale

        if _settings.skydome:
            sd.medge_actor.static_mesh.use_prefab = True
            sd.medge_actor.static_mesh.prefab = _settings.skydome

        if _settings.only_top: return

        # Add skydome bottom
        bpy.ops.medge_map_editor.add_skydome()
        sd = bpy.context.object
        b3d_utils.link_object_to_scene(sd, new_collection)

        sd.location = (0, 0, 0)
        sd.scale = (scale, scale, scale)
        sd.rotation_euler.x = pi
            
        if _settings.skydome:
            sd.medge_actor.static_mesh.use_prefab = True
            sd.medge_actor.static_mesh.prefab = _settings.skydome


# -----------------------------------------------------------------------------
class MET_OT_export_t3d(Operator):
    bl_idname = 'medge_generate.export_t3d'
    bl_label = 'Export T3D'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        self.export(collection)
        return {'FINISHED'}
    

    def export(_collection:Collection):
        b3d_utils.deselect_all_objects()

        for obj in _collection.all_objects:
            if obj.type != 'LIGHT':
                if obj.medge_actor.type == 'NONE': continue
            
            b3d_utils.select_object(obj)

        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        bpy.ops.medge_map_editor.t3d_export('INVOKE_DEFAULT', selected_collection=True)

        bpy.ops.ed.undo()


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

        settings = get_medge_map_gen_settings(_context)

        col.prop(settings, 'seed')
        col.prop(settings, 'length')
        col.prop(settings, 'align_orientation')
        col.prop(settings, 'resolve_intersection')
        
        col.separator(factor=2)
        b3d_utils.draw_box(col, 'Select Generated Chain')

        col.separator()
        col.operator(MET_OT_generate_map.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_export_map(MEdgeToolsPanel, ExportTab, Panel):
    bl_label = 'Export'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Select Collection')

        settings = get_medge_map_gen_settings(_context)

        col.separator()
        col.prop(settings, 'only_top')
        col.prop(settings, 'skydome')
        col.separator()
        col.operator(MET_OT_prepare_for_export.bl_idname)
        col.operator(MET_OT_export_t3d.bl_idname)


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
    Scene.medge_map_gen_settings    = PointerProperty(type=MET_SCENE_PG_map_gen_settings)


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_map_gen_settings'):    del Scene.medge_map_gen_settings