import bpy
from bpy.types import Operator, Context, Scene, Object, Collection, Spline, Operator, PropertyGroup, UIList, UILayout, Panel
from bpy.props import StringProperty, PointerProperty, BoolProperty, IntProperty, CollectionProperty
from mathutils import Vector, Matrix

import numpy      as     np
from math         import radians

from .gui              import MEdgeToolsPanel, ModulesTab
from ..                 import b3d_utils
from ..b3d_utils        import GenericList, rotation_matrix, update_matrices, duplicate_object_with_children, remove_object_with_children, check_objects_intersection
from .movement import State
from .markov            import get_markov_chains_prop


# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class CurveModule:
    def __init__(self, 
                 _state:int,
                 _module_names:list[str]):
        
        self.state = _state
        self.module_names = _module_names.copy()
        np.random.shuffle(self.module_names)

        self.curve:Object = None
        self.current_name_index = np.random.randint(len(self.module_names))
        self.index = 0
        self.collection = None


    @property
    def path(self) -> Spline:
        return self.curve.data.splines[0]
    
    @property
    def points(self) -> Spline:
        return self.path.points
    
    @property
    def volume(self) -> Object | None:
        return get_curve_module_prop(self.curve).collision_volume

    def __getitem__(self, _key:int):
        return self.path.points[_key].co


    def prepare(self, _index:int, _collection:Collection):
        self.index = _index
        self.collection = _collection


    def next_module(self, _index=-1):
        if self.curve:
            remove_object_with_children(self.curve)

        if _index >= 0 or _index < len(self.module_names):
            idx = _index
        else:
            idx = self.current_name_index
            self.current_name_index += 1
            self.current_name_index %= len(self.module_names)
        
        name = self.module_names[idx]
        module = bpy.data.objects[name]
        
        self.curve = duplicate_object_with_children(module, False, self.collection, False)
        self.curve.name = f'{self.index}_{module.name}'


    def align(self, other:'CurveModule', _align_direction=False, _rotation_offset=0):
        if not other:
            self.curve.location.xyz = 0, 0, 0
            update_matrices(self.curve)
            return

        # My direction
        my_mw = self.curve.matrix_world.copy()
        my_dir = my_mw @ self.points[1].co - (start := my_mw @ self.points[0].co)
        my_dir.normalize()

        # Other direction
        other_wm = other.curve.matrix_world.copy()
        other_dir = (end := other_wm @ other.points[-1].co) - other_wm @ other.points[-2].co
        other_dir.normalize()
        
        # Add rotation offset
        R = Matrix.Rotation(radians(_rotation_offset), 3, 'Z')

        if _align_direction:
            # Get rotation matrix around z-axis from direction vectors
            a = my_dir.xyz    * Vector((1, 1, 0))
            b = other_dir.xyz * Vector((1, 1, 0))

            if a.length == 0 or b.length == 0:
                raise Exception(f'Direction vector has 0 length. Perhaps overlapping control points for curve: {self.curve.name}')

            A = rotation_matrix(a, b)
            R = R @ A

        self.curve.matrix_world = my_mw @ R.to_4x4()

        # Move chain to the end of the other chain
        self.curve.location = end.xyz
        update_matrices(self.curve)

    
    def intersect(self, _other:'CurveModule') -> list[tuple[int, int]] | None:
        if not (vol1 := self.volume) or not (vol2 := _other.volume):
            return None

        return check_objects_intersection(vol1, vol2)
        

# -----------------------------------------------------------------------------
# Property Groups
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def add_collision_volume(_obj:Object) -> Object:
    if _obj.type != 'CURVE': return

    b3d_utils.update_matrices(_obj)

    cube = b3d_utils.create_cube((1, 1, 1.95))
    volume = b3d_utils.new_object(cube, 'Volume', bpy.context.collection, _obj, False)
    volume.display_type = 'WIRE'
    volume.location = _obj.location
    volume.location.x += .5
    volume.location.z += (1.95 * .5)

    get_curve_module_prop(_obj).collision_volume = volume

    return volume


# -----------------------------------------------------------------------------
def create_curve_module() -> Object:
    curve, _ = b3d_utils.create_curve('POLY', 3, 1)
    module = b3d_utils.new_object(curve, 'CurveModule', 'Modules')
    
    add_collision_volume(module)

    return module


# -----------------------------------------------------------------------------
class MET_OBJECT_PG_curve_module(PropertyGroup):

    def __on_update_collision_volume(self, _context:Context):
        if not (volume := self.collision_volume): return

        volume.display_type = 'WIRE'
        volume.name = 'CollisionVolume'
            

    collision_volume: PointerProperty(type=Object, name='Collision Volume', update=__on_update_collision_volume)


# -----------------------------------------------------------------------------
class MET_PG_curve_module_collection(PropertyGroup):

    def collect_curve_names(self) -> list[str]:
        if self.collection:            
            
            names = []

            for obj in self.collection.objects:
                if obj.type != 'CURVE': continue
                names.append(obj.name)

            return names

        return None
    
    
    def add_module(self):
        if self.collection:
            module = create_curve_module()
            b3d_utils.link_object_to_scene(module, self.collection)


    def __get_name(self):
        name = State(self.state).name
        
        if self.collection:
            if not self.collection.all_objects:
                name = '[EMPTY]_' + name
        else:
            name = '[EMPTY]_' + name

        return f'{self.state}_{name}'


    name:  StringProperty(name='Name', get=__get_name)
    state: IntProperty(name='PRIVATE')

    collection: PointerProperty(type=Collection, name='Collection')


# -----------------------------------------------------------------------------
class MET_SCENE_PG_curve_module_collection_list(PropertyGroup, GenericList):

    # Override to define return type
    def get_selected(self) -> MET_PG_curve_module_collection:
        if self.items:
            return self.items[self.selected_item_idx]
        
        return None


    def reset_collections(self):        
        self.items.clear()
        
        for state in State:
            mc:MET_PG_curve_module_collection = self.add()
            mc.state = state


    def update_collections(self):
        for state in State:
            if self.exists(state): continue
            mc:MET_PG_curve_module_collection = self.add()
            mc.state = state


    def exists(self, _state:int):
        mc:MET_PG_curve_module_collection
        for mc in self.items:
            if _state == mc.state:
                return True
    
                    
    items: CollectionProperty(type=MET_PG_curve_module_collection)   



# -----------------------------------------------------------------------------
class MET_UL_curve_module_group_draw(UIList):

    def draw_item(self, _context, _layout, _data, _item:MET_PG_curve_module_collection, _icon, _active_data, _active_property, _index, _flt_flag):
        if self.layout_type == 'GRID':
            _layout.alignment = 'CENTER'

        ic = 'RADIOBUT_OFF'

        mc = get_markov_chains_prop(_context).get_selected()
        
        if mc:
            gen_chain = mc.get_selected_generated_chain()
            states = set(gen_chain.split())
            
            if str(_item.state) in states:
                ic = 'RADIOBUT_ON'

        _layout.label(text=_item.name, icon=ic)


    def draw_filter(self, _context:Context|None, _layout:UILayout):
        _layout.separator() 
        col = _layout.column(align=True) 
        col.prop(self, 'filter_gen_chain', text='', icon='RADIOBUT_ON') 


    def filter_items(self, _context:Context|None, _data, _property:str):
        items = getattr(_data, _property) 
        filtered = []

        if self.filter_gen_chain:
            filtered = [0] * len(items)
            
            mc = get_markov_chains_prop(_context).get_selected()
            gen_chain = mc.get_selected_generated_chain()

            states = set(gen_chain.split())

            for s in states:
                filtered[int(s)] = self.bitflag_filter_item
        
        return filtered, []


    filter_gen_chain: BoolProperty(name='Filter Generated Chain')


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_reset_module_collections(Operator):
    bl_idname      = 'medge_generate.reset_modules'
    bl_label       = 'Reset Module Collections'
    bl_description = 'Reset list elements or reset if they already exists'


    def execute(self, _context):
        modules = get_curve_module_groups_prop(_context)
        modules.reset_collections()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_update_module_collections(Operator):
    bl_idname      = 'medge_generate.update_modules'
    bl_label       = 'Update Module Collections'
    bl_description = 'Update list elements or reset if they already exists'


    def execute(self, _context):
        modules = get_curve_module_groups_prop(_context)
        modules.update_collections()

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_add_curve_module_to_group(Operator):
    bl_idname      = 'medge_generate.add_curve_module_to_group'
    bl_label       = 'Add CurveModule To Group'
    bl_description = 'Add curve module to collection'
    bl_options     = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()

        return mg.collection != None


    def execute(self, _context:Context):
        module_groups = get_curve_module_groups_prop(_context)
        mg = module_groups.get_selected()
        mg.add_module()

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_add_collision_volume(Operator):
    bl_idname      = 'medge_generate.add_collision_volume'
    bl_label       = 'Add Collision Volume'
    bl_description = 'Add collision volume to curve module'
    bl_options     = {'UNDO'}


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj and not get_curve_module_prop(obj).collision_volume


    def execute(self, _context:Context):
        objs = _context.selected_objects

        for obj in objs:
            add_collision_volume(obj)

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_modules(MEdgeToolsPanel, ModulesTab, Panel):
    bl_label = 'Modules'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        module_groups = get_curve_module_groups_prop(_context)
        
        row = col.row(align=True)
        row.template_list('MET_UL_curve_module_group_draw', '#modules', module_groups, 'items', module_groups, 'selected_item_idx', rows=3)
        
        col.separator()
        row = col.row(align=True)

        t = 'Reset'
        if not module_groups.items:
            t = 'Init'

        row.operator(MET_OT_reset_module_collections.bl_idname, text=t)
        row.operator(MET_OT_update_module_collections.bl_idname, text='Update')

        if len(module_groups.items) == 0: return

        col.separator(factor=2)

        mg = module_groups.get_selected()

        row = col.row(align=True)

        row.prop(mg, 'collection')
        row.operator(MET_OT_add_curve_module_to_group.bl_idname, text='', icon='ADD')


# -----------------------------------------------------------------------------
class MET_PT_curve_module(MEdgeToolsPanel, Panel):
    bl_label = 'Curve Module'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj and obj.type == 'CURVE'


    def draw(self, _context:Context):
        obj = _context.object

        if not obj: return

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Use the curve as parent for any level component')
        col.separator()

        row = col.row(align=True)

        cm = get_curve_module_prop(obj)
        row.prop(cm, 'collision_volume')
        row.operator(MET_OT_add_collision_volume.bl_idname, text='', icon='ADD')


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_curve_module_prop(_obj:Object) -> MET_OBJECT_PG_curve_module:
    return _obj.medge_curve_module


# -----------------------------------------------------------------------------
def get_curve_module_groups_prop(_context:Context) -> MET_SCENE_PG_curve_module_collection_list:
    return _context.scene.medge_curve_module_groups


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Object.medge_curve_module       = PointerProperty(type=MET_OBJECT_PG_curve_module)
    Scene.medge_curve_module_groups = PointerProperty(type=MET_SCENE_PG_curve_module_collection_list)


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_curve_module_groups'): del Scene.medge_curve_module_groups
    if hasattr(Object, 'medge_curve_module'):       del Object.medge_curve_module