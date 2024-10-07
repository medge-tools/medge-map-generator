import bpy, bmesh, blf
from   bpy.types           import PropertyGroup, Object, Mesh, MeshVertex, Operator, Context, Panel, SpaceView3D, Scene
from   bpy.props           import BoolProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty, PointerProperty
from   bpy_extras          import view3d_utils
from   bpy_extras.io_utils import ImportHelper
from   bmesh.types         import BMesh, BMLayerAccessVert, BMLayerItem
from   mathutils           import Vector

import ntpath, json
import numpy       as np
from   enum        import Enum
from   collections import UserList
from   typing      import Generator

from ..        import b3d_utils
from .gui      import MEdgeToolsPanel, DatasetTab
from .movement import State, StateEnumProperty

# -----------------------------------------------------------------------------
# region Dataset
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class LayerType(str, Enum):
    NONE         = 'NONE'
    INT          = 'INT'
    FLOAT_VECTOR = 'FLOAT_VECTOR'


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/43862184/associating-string-representations-with-an-enum-that-uses-integer-values
class Attribute(int, Enum):
    def __new__(cls, _value: int, _label: str, _type: str):
        obj = int.__new__(cls, _value)
        obj._value_ = _value
        obj.index = _value
        obj.label = _label
        obj.type = _type
        
        return obj
    
    def __int__(self):
        return self.value
    
    @classmethod
    def from_string(cls, _s):
        for att in cls:
            if att.label == _s:
                return att
            
        raise ValueError(cls.__name__ + ' has no value matching "' + _s + '"')

    # From .json file
    STATE           = 0, 'state'          , LayerType.INT
    LOCATION        = 1, 'location'       , LayerType.NONE
    TIMESTAMP       = 2, 'timestamp'      , LayerType.FLOAT_VECTOR
    
    # These will be updated after import
    # A vertex is a sequence start when it has a different state than the previous vertex or it is disconnected from the previous vertex
    SEQUENCE_START  = 3, 'sequence_start' , LayerType.INT


# -----------------------------------------------------------------------------
class DatabaseEntry(UserList):
    def __init__(self) -> None:
        data = []

        for att in Attribute:
            match(att.type):
                case LayerType.NONE:
                    data.append(None)
                case LayerType.INT:
                    data.append(0)
                case LayerType.FLOAT_VECTOR:
                    data.append(Vector())

        self.data = np.array(data, dtype=object)


    def __getitem__(self, _key:int|str):
        if isinstance(_key, int):
            return self.data[_key]
        
        if isinstance(_key, str):
            return self.data[Attribute.from_string(_key).index]
    

    def __setitem__(self, _key:int|str, _value):
        if isinstance(_key, int):        
            self.data[_key] = _value

        if isinstance(_key, str):
            self.data[Attribute.from_string(_key).index] = _value


# -----------------------------------------------------------------------------
class Dataset:
    def __init__(self):
        self.data = np.empty((0, len(Attribute)), dtype=object)

    def __getitem__(self, _key):
        return self.data[_key]
    
    def __setitem__(self, _key, _value):
        self.data[_key] = _value
    
    def __len__(self):
        return len(self.data)
    
   
    def append(self, _entry:DatabaseEntry):
        V = np.array([_entry], dtype=object)
        self.data = np.append(self.data, V, axis=0)


    def extend(self, _other):
        self.data = np.concatenate((self.data, _other.data), axis=0)


# -----------------------------------------------------------------------------
class DatasetIO:
    def import_from_file(self, _filepath:str) -> None:
        with open(_filepath, 'r') as f:
            log = json.load(f)

        dataset = Dataset()

        prev_state = None

        for item in log:
            player_state = int(item[Attribute.STATE.label])

            ts = str(item[Attribute.TIMESTAMP.label]).split(':')
            timestamp = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            x = float(item[Attribute.LOCATION.label]['x'])
            y = float(item[Attribute.LOCATION.label]['y'])
            z = float(item[Attribute.LOCATION.label]['z'])
            location = Vector((y, x, z))

            entry = DatabaseEntry()
            entry[Attribute.STATE.index]          = player_state
            entry[Attribute.TIMESTAMP.index]      = timestamp
            entry[Attribute.LOCATION.index]       = location
            entry[Attribute.SEQUENCE_START.index] = False

            if not prev_state or prev_state != player_state:
                entry[Attribute.SEQUENCE_START.index] = True

            dataset.append(entry)

            prev_state = player_state

        name = ntpath.basename(_filepath)
        self.create_polyline(dataset, name)


    def create_polyline(self, _dataset:Dataset, _name:str) -> Object:
        # Create polyline
        verts = _dataset[:, Attribute.LOCATION.index]
        edges = [(i, i + 1) for i in range(len(verts) - 1)]

        mesh = b3d_utils.new_mesh(verts, edges, [], _name)
        obj = b3d_utils.new_object(mesh, _name)  

        # Add data to vertex attributes
        to_dataset(obj, _dataset)
        update_attributes(obj)

        return obj


# -----------------------------------------------------------------------------
def is_dataset(_obj:Object):
    if _obj.type != 'MESH': return False

    for att in Attribute:
        if att.type == LayerType.NONE: 
            continue

        if att.label not in _obj.data.attributes:
            return False
        
    return True


# -----------------------------------------------------------------------------
def to_dataset(_obj:Object, _dataset:Dataset=None):
    prev_mode = _obj.mode
    
    b3d_utils.set_object_mode(_obj, 'OBJECT')
    
    mesh = _obj.data
    
    n               = len(mesh.vertices)
    player_states   = [State.Walking.index] * n
    timestamps      = [0] * n * 3
    sequence_starts = [False] * n


    def unpack(_packed:list, _dest:list):
        for k in range(n):
            _dest[k * 3 + 0] = _packed[k].x
            _dest[k * 3 + 1] = _packed[k].y
            _dest[k * 3 + 2] = _packed[k].z


    if _dataset:
        player_states = list(_dataset[:, Attribute.STATE.index] )

        packed_ts = list(_dataset[:, Attribute.TIMESTAMP.index])
        unpack(packed_ts, timestamps)

        sequence_starts = list(_dataset[:, Attribute.SEQUENCE_START.index])


    def add_attribute(_att:Attribute, _data:list):
        if _att.label not in mesh.attributes:
            x = mesh.attributes.new(name=_att.label, type=_att.type, domain='POINT')
            match(_att.type):
                case LayerType.INT:
                    x.data.foreach_set('value', _data)
                case LayerType.FLOAT_VECTOR:
                    x.data.foreach_set('vector', _data)
                case _:
                    raise Exception(f'Unknown case for attribute: {_att.type}')


    add_attribute(Attribute.STATE         , player_states)
    add_attribute(Attribute.TIMESTAMP     , timestamps)
    add_attribute(Attribute.SEQUENCE_START, sequence_starts)
        
    b3d_utils.set_object_mode(_obj, prev_mode)


# -----------------------------------------------------------------------------
def get_layer(_bm:BMesh, _att:Attribute) -> BMLayerItem | None:
    layers = _bm.verts.layers

    match(_att.type):
        case LayerType.NONE:
            return None
        case LayerType.INT:
            return layers.int.get(_att.label)
        case LayerType.FLOAT_VECTOR:
            return layers.float_vector.get(_att.label)


# -----------------------------------------------------------------------------
def update_attributes(_obj:Object):
    if not is_dataset(_obj): return

    bm = b3d_utils.get_bmesh_from_object(_obj)
    bm.verts.ensure_lookup_table()

    layers = bm.verts.layers
    seq_start = layers.int.get(Attribute.SEQUENCE_START.label)

    for v1, v2 in zip(bm.verts, bm.verts[1:]):
        if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
            continue

        # If v2 is not connected to v1, then v2 is a sequence start
        v2[seq_start] = True

    b3d_utils.update_mesh_from_bmesh(_obj.data, bm)


# -----------------------------------------------------------------------------
def dataset_entries(_obj:Object) -> Generator[DatabaseEntry, None, None]:
    bm = b3d_utils.get_bmesh_from_object(_obj)


    def get_layers() -> Generator[BMLayerAccessVert, None, None]:
        nonlocal bm

        for att in Attribute:
            yield get_layer(bm, att)


    def retrieve_entry(_vert:MeshVertex) -> DatabaseEntry:
        nonlocal bm
        entry = DatabaseEntry()
        entry[Attribute.LOCATION.index] = _vert.co

        for layer in get_layers():
            if not layer: continue
            entry[layer.name] = _vert[layer]

        return entry


    bm.verts.ensure_lookup_table()

    for v in bm.verts:
        yield retrieve_entry(v)
    

# -----------------------------------------------------------------------------
def dataset_sequences(_obj:Object) -> Generator[tuple[int, list[Vector], float, bool], None, None]:
    """Yields ( state, list of locations )"""
    entries = dataset_entries(_obj)
    first_entry = next(entries)

    curr_state = first_entry[Attribute.STATE.index]
    curr_locs  = [first_entry[Attribute.LOCATION.index]]

    for entry in entries:
        state = entry[Attribute.STATE.index]
        loc   = entry[Attribute.LOCATION.index]
        start = entry[Attribute.SEQUENCE_START.index]

        curr_locs.append(loc)
        
        if state != curr_state or start:
            yield curr_state, curr_locs

            curr_state  = state
            curr_locs   = []
    
    yield curr_state, curr_locs
    
# endregion


# -----------------------------------------------------------------------------
# region Property Groups
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PG_vis_settings(PropertyGroup):

    to_name:           BoolProperty(name='To Name', default=False)
    only_selection:    BoolProperty(name='Only Selection', default=False)
    show_timestamps:   BoolProperty(name='Show Timestamps', default=False)
    min_draw_distance: FloatProperty(name='Min Draw Distance', subtype='DISTANCE', default=50)
    max_draw_distance: FloatProperty(name='Max Draw Distance', subtype='DISTANCE', default=100)
    default_color:     FloatVectorProperty(name='Default Color', subtype='COLOR_GAMMA', default=(.9, .9, .9))
    start_chain_color: FloatVectorProperty(name='Start Chain Color', subtype='COLOR_GAMMA', default=(.0, .9, .0))
    font_size:         IntProperty(name='Font Size', default=13)


# -----------------------------------------------------------------------------
class MET_PG_ops_settings(PropertyGroup):

    use_filter: BoolProperty(name='Use Filter')
    restrict:   BoolProperty(name='Restrict')
    filter:     StringProperty(name='Filter', description='List of [str | int] seperated by a comma')

    new_state:  StateEnumProperty()


# -----------------------------------------------------------------------------
class MET_SCENE_PG_datasettings(PropertyGroup):

    def get_vis_settings(self) -> MET_PG_vis_settings:
        return self.vis_settings

    def get_ops_settings(self) -> MET_PG_ops_settings:
        return self.ops_settings

    vis_settings: PointerProperty(type=MET_PG_vis_settings)
    ops_settings: PointerProperty(type=MET_PG_ops_settings)

# endregion


# -----------------------------------------------------------------------------
# region Operators
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_import_dataset(Operator, ImportHelper):
    bl_idname = 'medge_dataset.import_dataset'
    bl_label = 'Import Dataset'
    filename_ext = '.json'

    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'},
        maxlen=255,
    )


    def execute(self, _context:Context):
        DatasetIO().import_from_file(self.filepath)

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
# region Visualization
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
draw_handle_post_pixel = None


class MET_OT_toggle_dataset_vis(Operator):
    bl_idname = 'medge_dataset.toggle_dataset_vis'
    bl_label  = 'Toggle Dataset Vis'

    def execute(self, _context:Context):

        toggle = get_toggle_vis(_context)

        if toggle:
            self.add_handle(_context)
            _context.area.tag_redraw()
        else: 
            self.remove_handle()
            _context.area.tag_redraw()

        toggle = not toggle

        return{'FINISHED'}


    def add_handle(self, _context:Context):
        global draw_handle_post_pixel

        if draw_handle_post_pixel:
            self.remove_handle()

        draw_handle_post_pixel = SpaceView3D.draw_handler_add(
            self.draw_callback_post_pixel,(_context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        global draw_handle_post_pixel

        if draw_handle_post_pixel:
            SpaceView3D.draw_handler_remove(draw_handle_post_pixel, 'WINDOW')
            draw_handle_post_pixel = None


    def draw_callback_post_pixel(self, _context:Context):
        # Validate
        obj = _context.object
        if not obj: return
        if not is_dataset(obj): return
        if obj.mode != 'EDIT': return

        bm = bmesh.from_edit_mesh(obj.data)
        
        # Region
        region    = _context.region
        region_3d = _context.space_data.region_3d
        view_mat  = region_3d.view_matrix

        # Layers
        state_layer       = get_layer(bm, Attribute.STATE)
        time_layer        = get_layer(bm, Attribute.TIMESTAMP)      
        chain_start_layer = get_layer(bm, Attribute.SEQUENCE_START) 

        # Settings
        vis_settings      = get_datasettings_prop(_context).get_vis_settings()
        min_draw_distance = vis_settings.min_draw_distance
        max_draw_distance = vis_settings.max_draw_distance
        default_color     = vis_settings.default_color
        start_chain_color = vis_settings.start_chain_color
        font_size         = vis_settings.font_size
        
        # Draw
        for v in bm.verts:
            # Only visualize selection
            if vis_settings.only_selection:
                if not v.select: continue

            # Get 2D coordinate
            location = obj.matrix_world @ v.co
            co_2d = view3d_utils.location_3d_to_region_2d(region, region_3d, location)

            if not co_2d: continue
            
            # Get distance to virtual camera
            if region_3d.is_perspective:
                distance = (view_mat @ v.co).length
            else:
                distance = -(view_mat @ v.co).z

            # Use distance to alpha blend
            alpha = b3d_utils.map_range(distance, min_draw_distance, max_draw_distance, 1, 0)
            
            if alpha <= 0: continue

            # Set color 
            if v[chain_start_layer]:
                blf.color(0, *start_chain_color, alpha)
            else:
                blf.color(0, *default_color, alpha)

            # Display timestamp
            if vis_settings.show_timestamps:
                ts = v[time_layer]
                
                blf.size(0, font_size)
                blf.position(0, co_2d[0], co_2d[1], 0)
                blf.draw(0, '{:.0f}:{:.0f}:{:.3f}'.format(*ts))
                co_2d[1] += font_size

            # Display state
            state = v[state_layer]
            
            if vis_settings.to_name:
                state = State(state).name

            blf.size(0, font_size * 1.5)
            blf.position(0, co_2d[0] - font_size, co_2d[1], 0)
            blf.draw(0, str(state))

# endregion


# -----------------------------------------------------------------------------
class MET_OT_convert_to_dataset(Operator):
    bl_idname = 'medge_dataset.convert_to_dataset'
    bl_label  = 'Convert To Dataset'


    @classmethod
    def poll(cls, _context:Context):
        return _context.object.type == 'MESH'


    def execute(self, _context:Context):
        to_dataset(_context.object)

        return {'FINISHED'}  


# -----------------------------------------------------------------------------
class MET_OT_update_attributes(Operator):
    bl_idname = 'medge_dataset.update_attributes'
    bl_label  = 'Update Attributes'
    bl_description = 'Update attributes if you have made edits to the mesh'


    @classmethod
    def poll(cls, _context:Context):
        return is_dataset(_context.object)


    def execute(self, _context:Context):
        update_attributes(_context.object)

        return {'FINISHED'} 


# -----------------------------------------------------------------------------
class MET_OT_set_state(Operator):
    bl_idname = 'medge_dataset.set_state'
    bl_label  = 'Set State'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        settings = get_datasettings_prop(_context).get_ops_settings()
        
        bm = b3d_utils.get_bmesh_from_object(obj)

        state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

        for v in bm.verts:
            if v.select:
                v[state_layer] = State[settings.new_state]

        bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'} 

        
# -----------------------------------------------------------------------------
class MET_OT_select_transitions(Operator):
    bl_idname = 'medge_dataset.select_transitions'
    bl_label  = 'Select Transitions'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, _context:Context):
        settings = get_datasettings_prop(_context).get_ops_settings()

        count = 0.0
        objs = _context.selected_objects

        for obj in objs:
            count += self.selected_transitions(obj, settings)

        self.report({'INFO'}, f'{count / len(objs)} average transitions')

        return {'FINISHED'}
    

    def selected_transitions(self, _obj:Object, _settings:MET_PG_ops_settings) -> int:
        filter = _settings.filter
        restrict = _settings.restrict

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        mesh = _obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

        b3d_utils.deselect_all_vertices(bm)

        count = 0

        for k in range(len(bm.verts) - 1):
            v1 = bm.verts[k]
            v2 = bm.verts[k + 1]
            
            s1 = v1[state_layer]
            s2 = v2[state_layer]

            if s1 == s2: continue

            if filter: 
                if s1 not in filter and s2 not in filter:
                    continue
                if restrict:
                    if s1 not in filter or s2 not in filter:
                        continue                    

            v1.select = True
            v2.select = True
            count += 1

        bmesh.update_edit_mesh(mesh)

        return count
    

# -----------------------------------------------------------------------------
class MET_OT_select_states(Operator):
    bl_idname = 'medge_dataset.select_states'
    bl_label  = 'Select States'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        filter = get_datasettings_prop(_context).get_ops_settings().filter

        return filter and is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        filter = get_datasettings_prop(_context).get_ops_settings().filter

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

        b3d_utils.deselect_all_vertices(bm)

        for v in bm.verts:
            s = v[state_layer]

            if s in filter:
                v.select = True

        bmesh.update_edit_mesh(mesh)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_resolve_overlap(Operator):
    bl_idname = 'medge_dataset.resolve_overlap'
    bl_label  = 'Resolve Overlap'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return is_dataset(obj) and obj.mode == 'EDIT'
    

    def execute(self, _context:Context):
        obj = _context.object

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        for k in range(len(bm.verts) - 1):
            v1 = bm.verts[k]
            v2 = bm.verts[k + 1]

            if v1.co != v2.co: continue

            v0 = bm.verts[k - 1]
            offset = v1.co - v0.co
            if k == 0:
                v0 = bm.verts[k + 2]
                offset = v0.co - v1.co

            for v in bm.verts[k+1:]:
                v.co += offset

        bmesh.update_edit_mesh(mesh)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
class MET_OT_extract_curves(Operator):
    bl_idname = 'medge_dataset.extract_curves'
    bl_label  = 'Extract Curves'


    @classmethod
    def poll(cls, _context:Context):
        return is_dataset(_context.object)


    def execute(self, _context:Context):
        obj = _context.object

        collection = b3d_utils.new_collection('EXTRACTED_CURVES_' + obj.name)

        for state, locations in dataset_sequences(obj):
            name = State(state).name

            curve_data, path = b3d_utils.create_curve('POLY', len(locations))

            # To origin
            offset = locations[0].copy()
            for p in locations:
                p -= offset

            # Update curve points
            for p1, p2 in zip(path.points, locations):
                p1.co = *p2, 1

            b3d_utils.new_object(curve_data, f'{name}_Curve', collection)

        return {'FINISHED'}

# endregion

# -----------------------------------------------------------------------------
# region GUI
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_dataset(MEdgeToolsPanel, DatasetTab, Panel):
    bl_label = 'Dataset'

    
    def draw(self, _context: Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        obj = _context.active_object

        if not obj: 
            b3d_utils.draw_box(col, 'Select Object')
            return

        if not (settings := get_datasettings_prop(_context)): 
            col.operator(MET_OT_convert_to_dataset.bl_idname)
            b3d_utils.draw_box(col, 'Make sure it is a polyline')
        
            return
        
        settings = settings.get_ops_settings()
        
        if not settings: return

        box = col.box()
        box.prop(settings, 'new_state')
        box.operator(MET_OT_set_state.bl_idname)
        
        box = col.box()
        box.prop(settings, 'filter')
        box.operator(MET_OT_select_states.bl_idname)

        box = col.box()
        box.prop(settings, 'use_filter')
        if settings.use_filter:
            box.prop(settings, 'restrict')
            box.prop(settings, 'filter')
        
        box.operator(MET_OT_select_transitions.bl_idname)

        col.separator()
        row = col.row()
        row.scale_y = 1.2
        row.operator(MET_OT_resolve_overlap.bl_idname)
        row.operator(MET_OT_extract_curves.bl_idname)

        col.separator()
        row = col.row()
        row.scale_y = 1.2
        row.operator(MET_OT_update_attributes.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_dataset_vis(MEdgeToolsPanel, DatasetTab, Panel):
    bl_label = 'Visualization'


    def draw_header(self,_context: Context ):
        self.layout.prop(_context.window_manager, 'toggle_vis', text='')


    def draw(self, _context: Context):     
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)

        if _context.mode != 'EDIT_MESH' or not get_toggle_vis(_context):
            b3d_utils.draw_box(col, 'Visualization renders in Edit Mode')
            return
        
        if not (settings := get_datasettings_prop(_context)): return
        
        vis_settings = settings.get_vis_settings()
        
        col = layout.column(align=True)
        col.separator()
        
        col.prop(vis_settings, 'to_name')
        col.prop(vis_settings, 'only_selection')
        col.prop(vis_settings, 'show_timestamps')
        col.prop(vis_settings, 'draw_aabb')
        col.separator()
        col.prop(vis_settings, 'default_color')
        col.prop(vis_settings, 'start_chain_color')
        col.separator()
        col.prop(vis_settings, 'font_size')
        col.separator()
        col.prop(vis_settings, 'min_draw_distance', text='Draw Distance Min')
        col.prop(vis_settings, 'max_draw_distance', text='Max')

# endregion


# -----------------------------------------------------------------------------
# Scene Utils
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def get_datasettings_prop(_context:Context) -> MET_SCENE_PG_datasettings:
    return _context.scene.medge_datasettings


# -----------------------------------------------------------------------------
def get_toggle_vis(_context:Context) -> bpy.types.BoolProperty:
    return _context.window_manager.toggle_vis


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, _context:Context):
    self.layout.operator(MET_OT_import_dataset.bl_idname, text='MEdge Dataset (.json)')


# -----------------------------------------------------------------------------
def __on_toggle_vis_update(self, _context:Context):
    bpy.ops.medge_dataset.toggle_dataset_vis()


# -----------------------------------------------------------------------------
def register():
    Scene.medge_datasettings = PointerProperty(type=MET_SCENE_PG_datasettings)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)
    bpy.types.WindowManager.toggle_vis = BoolProperty(name='Toggle Vis', default=False, update=__on_toggle_vis_update)


# -----------------------------------------------------------------------------
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)
    if hasattr(Mesh, 'medge_datasettings'): del Scene.medge_datasettings