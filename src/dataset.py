import bpy, bmesh, blf
from   bpy.types           import PropertyGroup, Object, Mesh, MeshVertex, Operator, Context, Panel, SpaceView3D
from   bpy.props           import BoolProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty, PointerProperty
from   bpy_extras          import view3d_utils
from   bpy_extras.io_utils import ImportHelper
from   bmesh.types         import BMesh, BMLayerAccessVert
from   mathutils           import Vector

import ntpath, json
import numpy       as np
from   enum        import Enum
from   collections import UserList
from   typing      import Generator

from ..        import b3d_utils
from .gui      import MEdgeToolsPanel, DatasetTab
from .movement import State, StateProperty

# -----------------------------------------------------------------------------
# region Dataset
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class AttributeType(str, Enum):
    NONE         = 'NONE'
    INT          = 'INT'
    FLOAT_VECTOR = 'FLOAT_VECTOR'


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/43862184/associating-string-representations-with-an-enum-that-uses-integer-values
class Attribute(int, Enum):
    def __new__(cls, 
                _value: int, 
                _label: str, 
                _type: str):
        obj = int.__new__(cls, _value)
        obj._value_ = _value
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


    STATE           = 0, 'state'          , AttributeType.INT
    LOCATION        = 1, 'location'       , AttributeType.NONE
    TIMESTAMP       = 2, 'timestamp'      , AttributeType.FLOAT_VECTOR
    CONNECTED       = 3, 'connected'      , AttributeType.INT
    SEQUENCE_START  = 4, 'sequence_start' , AttributeType.INT


# -----------------------------------------------------------------------------
class DatabaseEntry(UserList):
    def __init__(self) -> None:
        data = []

        for att in Attribute:
            match(att.type):
                case AttributeType.NONE:
                    data.append(None)
                case AttributeType.INT:
                    data.append(0)
                case AttributeType.FLOAT_VECTOR:
                    data.append(Vector())

        self.data = np.array(data, dtype=object)


    def __getitem__(self, _key:int|str):
        if isinstance(_key, int):
            return self.data[_key]
        
        if isinstance(_key, str):
            return self.data[Attribute.from_string(_key).value]
    

    def __setitem__(self, _key:int|str, _value):
        if isinstance(_key, int):        
            self.data[_key] = _value

        if isinstance(_key, str):
            self.data[Attribute.from_string(_key).value] = _value


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
            entry[Attribute.STATE.value]       = player_state
            entry[Attribute.TIMESTAMP.value]   = timestamp
            entry[Attribute.LOCATION.value]    = location
            entry[Attribute.SEQUENCE_START.value] = False

            if not prev_state or prev_state != player_state:
                entry[Attribute.SEQUENCE_START.value] = True

            dataset.append(entry)

            prev_state = player_state

        name = ntpath.basename(_filepath)
        self.create_polyline(dataset, name)


    def create_polyline(self, _dataset:Dataset, _name:str) -> Object:
        # Create polyline
        verts = _dataset[:, Attribute.LOCATION.value]
        edges = [(i, i + 1) for i in range(len(verts) - 1)]

        mesh = b3d_utils.new_mesh(verts, edges, [], _name)
        obj = b3d_utils.new_object(mesh, _name)  

        # Add dataset to obj
        to_dataset(obj, _dataset)
        update_attributes(obj)

        return obj


# -----------------------------------------------------------------------------
def update_attributes(_obj:Object):
    if not is_dataset(_obj): return

    bm = b3d_utils.get_bmesh_from_object(_obj)
    bm.verts.ensure_lookup_table()

    layers = bm.verts.layers

    connected = layers.int.get(Attribute.CONNECTED.label)
    seq_start = layers.int.get(Attribute.SEQUENCE_START.label)

    # Check if v1 and v2 (consecutive vertices) are connected
    for v1, v2 in zip(bm.verts, bm.verts[1:]):
        conn = False
        if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
            conn = True

        v1[connected] = conn

    # Check if it is sequence start
    for v1, v2 in zip(bm.verts, bm.verts[1:]):
        if not v1[connected]:
            v2[seq_start] = True

    b3d_utils.update_mesh_from_bmesh(_obj.data, bm)


# -----------------------------------------------------------------------------
def is_dataset(_obj:Object):
    if _obj.type != 'MESH': return False

    for att in Attribute:
        if att.type == AttributeType.NONE: 
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
    player_states   = [State.Walking.value] * n
    timestamps      = [0] * n * 3
    connections     = [True] * n
    sequence_starts = [False] * n


    def unpack(_packed:list, _dest:list):
        for k in range(n):
            _dest[k * 3 + 0] = _packed[k].x
            _dest[k * 3 + 1] = _packed[k].y
            _dest[k * 3 + 2] = _packed[k].z


    if _dataset:
        player_states = list(_dataset[:, Attribute.STATE.value] )

        packed_ts = list(_dataset[:, Attribute.TIMESTAMP.value])
        unpack(packed_ts, timestamps)

        connections = list(_dataset[:, Attribute.CONNECTED.value])
        
        sequence_starts = list(_dataset[:, Attribute.SEQUENCE_START.value])


    def add_attribute(_att:Attribute, _data:list):
        if _att.label not in mesh.attributes:
            x = mesh.attributes.new(name=_att.label, type=_att.type, domain='POINT')
            match(_att.type):
                case AttributeType.INT:
                    x.data.foreach_set('value', _data)
                case AttributeType.FLOAT_VECTOR:
                    x.data.foreach_set('vector', _data)
                case _:
                    raise Exception(f'Unknown case for attribute: {_att.type}')


    add_attribute(Attribute.STATE         , player_states)
    add_attribute(Attribute.TIMESTAMP     , timestamps)
    add_attribute(Attribute.CONNECTED     , connections)
    add_attribute(Attribute.SEQUENCE_START, sequence_starts)
        
    b3d_utils.set_object_mode(_obj, prev_mode)


# -----------------------------------------------------------------------------
def dataset_entries(_obj:Object) -> Generator[DatabaseEntry, None, None]:
    bm = b3d_utils.get_bmesh_from_object(_obj)


    def attribute_layers() -> Generator[BMLayerAccessVert, None, None]:
        nonlocal bm
        layers = bm.verts.layers

        for att in Attribute:
            match(att.type):
                case AttributeType.INT:
                    yield layers.int.get(att.label)
                case AttributeType.FLOAT_VECTOR:
                    yield layers.float_vector.get(att.label)


    def retrieve_entry(_vert:MeshVertex) -> DatabaseEntry:
        nonlocal bm
        entry = DatabaseEntry()
        entry[Attribute.LOCATION.value] = _vert.co

        for layer in attribute_layers(bm):
            entry[layer.name] = _vert[layer]

        return entry


    bm.verts.ensure_lookup_table()

    for v in bm.verts:
        yield retrieve_entry(v)
    


# -----------------------------------------------------------------------------
def dataset_sequences(_obj:Object) -> Generator[tuple[int, list[Vector], float, bool], None, None]:
    """Yields ( state, list of locations, total length, connected )"""
    entries = dataset_entries(_obj)
    first_entry = next(entries)

    prev_loc = first_entry[Attribute.LOCATION.value]

    curr_state  = first_entry[Attribute.STATE.value]
    curr_conn   = first_entry[Attribute.CONNECTED.value]
    curr_locs   = [prev_loc]
    curr_length = 0

    for entry in entries:
        state      = entry[Attribute.STATE.value]
        loc        = entry[Attribute.LOCATION.value]
        start      = entry[Attribute.SEQUENCE_START.value]
        curr_conn  = entry[Attribute.CONNECTED.value]

        curr_length += (loc - prev_loc).length
        
        if curr_conn:
            curr_locs.append(loc)
        
        if state != curr_state or start:
            yield curr_state, curr_locs, curr_length, curr_conn
            curr_state  = state
            curr_length = 0
            curr_locs   = []

        prev_loc = loc
    
    yield curr_state, curr_locs, curr_length, curr_conn
    
# endregion


# -----------------------------------------------------------------------------
# region Visualization
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
draw_handle_post_pixel = None


# -----------------------------------------------------------------------------
def add_handle(_context:Context):
    global draw_handle_post_pixel

    if draw_handle_post_pixel:
        remove_handle()

    draw_handle_post_pixel = SpaceView3D.draw_handler_add(
        draw_callback_post_pixel,(_context,), 'WINDOW', 'POST_PIXEL')


# -----------------------------------------------------------------------------
def remove_handle():
    global draw_handle_post_pixel

    if draw_handle_post_pixel:
        SpaceView3D.draw_handler_remove(draw_handle_post_pixel, 'WINDOW')
        draw_handle_post_pixel = None


# -----------------------------------------------------------------------------
def draw_callback_post_pixel(_context:Context):
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
    state_layer       = bm.verts.layers.int.get(Attribute.STATE.label)
    time_layer        = bm.verts.layers.float_vector.get(Attribute.TIMESTAMP.label)
    chain_start_layer = bm.verts.layers.int.get(Attribute.SEQUENCE_START.label)

    # Settings
    vis_settings      = get_dataset_prop(obj).get_vis_settings()
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
# region Property Groups
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_DS_PG_vis_settings(PropertyGroup):

    to_name:           BoolProperty(name='To Name', default=False)
    only_selection:    BoolProperty(name='Only Selection', default=False)
    show_timestamps:   BoolProperty(name='Show Timestamps', default=False)
    min_draw_distance: FloatProperty(name='Min Draw Distance', subtype='DISTANCE', default=50)
    max_draw_distance: FloatProperty(name='Max Draw Distance', subtype='DISTANCE', default=100)
    default_color:     FloatVectorProperty(name='Default Color', subtype='COLOR_GAMMA', default=(.9, .9, .9))
    start_chain_color: FloatVectorProperty(name='Start Chain Color', subtype='COLOR_GAMMA', default=(.0, .9, .0))
    font_size:         IntProperty(name='Font Size', default=13)


# -----------------------------------------------------------------------------
class MET_DS_PG_ops_settings(PropertyGroup):

    use_filter: BoolProperty(name='Use Filter')
    restrict:   BoolProperty(name='Restrict')
    filter:     StringProperty(name='Filter', description='List of [str | int] seperated by a comma')

    new_state:  StateProperty()


# -----------------------------------------------------------------------------
class MET_MESH_PG_dataset(PropertyGroup):

    def get_vis_settings(self) -> MET_DS_PG_vis_settings:
        return self.vis_settings

    def get_ops_settings(self) -> MET_DS_PG_ops_settings:
        return self.ops_settings

    vis_settings: PointerProperty(type=MET_DS_PG_vis_settings)
    ops_settings: PointerProperty(type=MET_DS_PG_ops_settings)

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
vis_state = False

def is_vis_enabled():
    global vis_state
    return vis_state


def set_vis_state(state: bool):
    global vis_state
    vis_state = state


# -----------------------------------------------------------------------------
class MET_OT_enable_dataset_vis(Operator):
    bl_idname = 'medge_dataset.enable_dataset_vis'
    bl_label  = 'Enable Dataset Vis'


    @classmethod
    def poll(cls, _context:Context):
        return not is_vis_enabled()


    def execute(self, _context:Context):
        add_handle(_context)
        
        _context.area.tag_redraw()
        
        set_vis_state(True)

        return{'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_disable_dataset_vis(Operator):
    bl_idname = 'medge_dataset.disable_dataset_vis'
    bl_label  = 'Disable Dataset Vis'


    @classmethod
    def poll(cls, _context:Context):
        return is_vis_enabled()


    def execute(self, _context:Context):
        remove_handle()
        
        _context.area.tag_redraw()
        
        set_vis_state(False)

        return {'FINISHED'}


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
        settings = get_dataset_prop(obj).get_ops_settings()
        
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
        obj = _context.object

        settings = get_dataset_prop(obj).get_ops_settings()
        filter = settings.filter
        restrict = settings.restrict

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        mesh = obj.data
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

        self.report({'INFO'}, f'{count} transitions')

        return {'FINISHED'}
    

# -----------------------------------------------------------------------------
class MET_OT_select_states(Operator):
    bl_idname = 'medge_dataset.select_states'
    bl_label  = 'Select States'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        filter = get_dataset_prop(obj).get_ops_settings().filter

        return filter and is_dataset(obj) and obj.mode == 'EDIT'


    def execute(self, _context:Context):
        obj = _context.object
        filter = get_dataset_prop(obj).get_ops_settings().filter

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

        for state, locations, _, _ in dataset_sequences(obj):
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

        obj = _context.active_object

        if not obj: 
            b3d_utils.draw_box(layout, 'Select Object')
            return

        col = layout.column(align=True)

        if not (dataset := get_dataset_prop(obj)): 
            col.operator(MET_OT_convert_to_dataset.bl_idname)
            b3d_utils.draw_box(layout, 'Make sure it is a polyline')
        
            return
        
        else:
            b3d_utils.draw_box(layout, 'Update attributes if you have made edits to the mesh')
            col.operator(MET_OT_update_attributes.bl_idname)

        settings = dataset.get_ops_settings()
        
        if not settings: return

        col.separator(factor=2)
        col.prop(settings, 'new_state')
        col.separator()
        col.operator(MET_OT_set_state.bl_idname)
        
        col.separator()
        col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_select_states.bl_idname)
        
        col.separator()
        col.prop(settings, 'use_filter')

        if settings.use_filter:
            col.prop(settings, 'restrict')
            col.prop(settings, 'filter')
        
        col.separator()
        col.operator(MET_OT_select_transitions.bl_idname)
        col.operator(MET_OT_resolve_overlap.bl_idname)
        col.operator(MET_OT_extract_curves.bl_idname)


# -----------------------------------------------------------------------------
class MET_PT_dataset_vis(MEdgeToolsPanel, DatasetTab, Panel):
    bl_label = 'Visualization'


    def draw(self, _context: Context):        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)
        row = col.row(align=True)

        row.operator(MET_OT_enable_dataset_vis.bl_idname, text='Enable')
        row.operator(MET_OT_disable_dataset_vis.bl_idname, text='Disable')
        
        if not is_vis_enabled(): 
            box = layout.box()
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text='Visualization renders in Edit Mode')
            return

        if not (obj := _context.active_object): return
        if not (dataset := get_dataset_prop(obj)): return

        vis_settings = dataset.get_vis_settings()
        
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
def get_dataset_prop(_obj:Object) -> MET_MESH_PG_dataset:
    if is_dataset(_obj):
        return _obj.data.medge_dataset
    return None


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, _context:Context):
    self.layout.operator(MET_OT_import_dataset.bl_idname, text='MEdge Dataset (.json)')


# -----------------------------------------------------------------------------
def register():
    Mesh.medge_dataset = PointerProperty(type=MET_MESH_PG_dataset)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)


# -----------------------------------------------------------------------------
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)
    if hasattr(Mesh, 'medge_dataset'): del Mesh.medge_dataset