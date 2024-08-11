from bpy.types import Operator, Context, Panel, PropertyGroup, Collection, Scene
from bpy.props import PointerProperty, IntProperty, StringProperty, BoolProperty

from datetime    import datetime
import csv
import os

from ..b3d_utils import new_collection, delete_hierarchy
from .gui        import MEdgeToolsPanel, EvaluateTab
from .markov     import MET_PG_markov_chain, get_markov_chains_prop
from .modules    import get_curve_module_groups_prop
from .map        import Map, filter_states, get_medge_map_gen_settings


# -----------------------------------------------------------------------------
# PropertyGroups
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_SCENE_PG_evaluation_settings(PropertyGroup):

    def __str__(self):
        return f"\
{self.collection.name}_\
{self.map_length}_\
{self.map_amount}_\
{self.seed_start}\
"
    
    collection: PointerProperty(type=Collection, name='Collection', description='Collection with datasets to use for Markov Data')
    map_length: IntProperty(name='Map Length', default=96, min=1)
    map_amount: IntProperty(name='Map Amount', default=100, min=1)
    seed_start: IntProperty(name='Seed Start', default=0, min=0)
    file_path:  StringProperty(name='File Path', default='C:\\Users\\')
    file_name:  StringProperty(name='File Name', default='performance_evaluation')
    cleanup:    BoolProperty(name='Cleanup', default=True, description='Deletes the Markov data')


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_evaluate_computational_performance(Operator):
    bl_idname  = 'medge_generate.evaluate_computational_performance'
    bl_label   = 'Computational Performance'
    bl_options = {'UNDO'}

    
    @classmethod
    def poll(cls, _context:Context):
        return get_medge_evaluation_settings(_context).collection


    def execute(self, _context:Context):
        mc = get_markov_chains_prop(_context)
        eval_settings = get_medge_evaluation_settings(_context)

        active_mc:MET_PG_markov_chain = mc.add()
        active_mc.collection = eval_settings.collection

        # Generate Markov Chains
        active_mc.create_transition_matrix()

        seed = eval_settings.seed_start

        for _ in range(eval_settings.map_amount):
            active_mc.length = eval_settings.map_length
            active_mc.seed = seed
            active_mc.generate_chain()
            seed += 1

        # Generate maps
        module_groups = get_curve_module_groups_prop(_context).items
        gen_settings = get_medge_map_gen_settings(_context)
        gen_settings.length = -1 # To ensure it generates the whole length

        time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        main_collection = new_collection(f'EVALUTATION_[{eval_settings}]_{time}' )

        data:list[tuple[float, float, int]] = []

        for k, gen_chain in enumerate(active_mc.generated_chains.items):
            print(f'Iteration {k}')

            time = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
            collection = new_collection(f'{k}_POPULATED_{active_mc.name}_[{gen_settings}]_{time}', _parent=main_collection )

            states = filter_states(gen_chain.split(), gen_settings)

            map = Map(None, gen_settings)
            map.debug = False
            map.prepare(states, module_groups)
            total_time, resolve_time, total_hits = map.build(collection)

            data.append((total_time, resolve_time, total_hits))

        # Export data
        path = eval_settings.file_path + eval_settings.file_name + '.csv'

        exists = os.path.exists(path)

        with open(path, 'a', newline='') as file:
            writer = csv.writer(file)
            if not exists: writer.writerow(('total_time', 'resolve_time', 'total_lowest_hits'))
            writer.writerows(data)

        self.report({'INFO'}, f'Data saved to: {path}')

        if eval_settings.cleanup:
            mc.remove()
        
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# GUI 
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_evaluate(MEdgeToolsPanel, EvaluateTab, Panel):
    bl_label = 'Evaluate'

    
    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        settings = get_medge_evaluation_settings(_context)

        col = layout.column(align=True)

        col.prop(settings, 'collection')
        col.separator()
        col.prop(settings, 'map_length')
        col.prop(settings, 'map_amount')
        col.prop(settings, 'seed_start')
        
        col.separator()

        col.prop(settings, 'file_path')
        col.prop(settings, 'file_name')

        col.separator()

        col.prop(settings, 'cleanup')

        col.separator()

        split = col.split(factor=0.07, align=True)
        split.scale_y = 1.4
        split.operator('wm.console_toggle', icon='CONSOLE', text='')
        split.operator(MET_OT_evaluate_computational_performance.bl_idname)
        

# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_medge_evaluation_settings(_context:Context) -> MET_SCENE_PG_evaluation_settings:
    return _context.scene.medge_evaluation_settings


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_evaluation_settings = PointerProperty(type=MET_SCENE_PG_evaluation_settings)


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_evaluation_settings'): del Scene.medge_evaluation_settings