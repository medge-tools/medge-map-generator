import bmesh
from   mathutils   import Vector
from   bpy.types   import Object
from   bmesh.types import BMesh, BMLayerAccessVert

import ntpath, json
import numpy       as np
from   enum        import Enum
from   collections import UserList
from   typing      import Generator

from ..        import b3d_utils
from .movement import State


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


    STATE           = 0, 'player_state', AttributeType.INT
    LOCATION        = 1, 'location'    , AttributeType.NONE
    TIMESTAMP       = 2, 'timestamp'   , AttributeType.FLOAT_VECTOR
    CONNECTED       = 3, 'connected'   , AttributeType.INT
    CHAIN_START     = 4, 'chain_start' , AttributeType.INT
    # If CHAIN_START is True then LENGTH is the length of the chain
    # Else LENGTH is the distance to CHAIN_START
    LENGTH          = 5, 'length'      , AttributeType.INT
    AABB_MIN        = 6, 'aabb_min'    , AttributeType.FLOAT_VECTOR
    AABB_MAX        = 7, 'aabb_max'    , AttributeType.FLOAT_VECTOR


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
def db_entry_sequences(first_entry:DatabaseEntry, rest_of_data:any) -> Generator[tuple[int, list[Vector], float, bool], None, None]:
    """Yields ( state, list of locations, total length, connected )"""
    prev_loc = first_entry[Attribute.LOCATION.value]

    curr_state  = first_entry[Attribute.STATE.value]
    curr_conn   = first_entry[Attribute.CONNECTED.value]
    curr_locs   = [prev_loc]
    curr_length = 0

    for entry in rest_of_data:
        state      = entry[Attribute.STATE.value]
        loc        = entry[Attribute.LOCATION.value]
        start      = entry[Attribute.CHAIN_START.value]
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


    def sequences(self):
        """Yields ( state, list of locations, total length, connected )"""
        return db_entry_sequences(self.data[0], self.data[1:])

# -----------------------------------------------------------------------------
class DatasetIO:
    def import_from_file(self, _filepath:str) -> None:
        with open(_filepath, 'r') as f:
            log = json.load(f)

        dataset = Dataset()

        for item in log:
            player_state = int(item[Attribute.STATE.label])

            ts = str(item[Attribute.TIMESTAMP.label]).split(':')
            timestamp = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            x = float(item[Attribute.LOCATION.label]['x'])
            y = float(item[Attribute.LOCATION.label]['y'])
            z = float(item[Attribute.LOCATION.label]['z'])
            location = Vector((y, x, z))

            entry = DatabaseEntry()
            entry[Attribute.STATE.value] = player_state
            entry[Attribute.TIMESTAMP.value] = timestamp
            entry[Attribute.LOCATION.value] = location

            dataset.append(entry)

        name = ntpath.basename(_filepath)
        create_polyline(dataset, name)


    def write_to_file(self, _filepath:str) -> None:
        pass


# -----------------------------------------------------------------------------
def to_dataset(_obj:Object, _dataset:Dataset=None):
    prev_mode = _obj.mode
    b3d_utils.set_object_mode(_obj, 'OBJECT')
    mesh = _obj.data
    
    n             = len(mesh.vertices)
    player_states = [State.Walking.value] * n
    timestamps    = [0] * n * 3
    connections   = [True] * n
    chain_starts  = [False] * n
    lengths       = [0] * n
    aabb_mins     = [0] * n * 3
    aabb_maxs     = [0] * n * 3


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
        chain_starts  = list(_dataset[:, Attribute.CHAIN_START.value])
        lengths = list(_dataset[:, Attribute.LENGTH.value])

        packed_mins = list(_dataset[:, Attribute.AABB_MIN.value])
        packed_maxs = list(_dataset[:, Attribute.AABB_MAX.value])
        unpack(packed_mins, aabb_mins)
        unpack(packed_maxs, aabb_maxs)


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


    add_attribute(Attribute.STATE, player_states)
    add_attribute(Attribute.TIMESTAMP  , timestamps)
    add_attribute(Attribute.CONNECTED  , connections)
    add_attribute(Attribute.CHAIN_START, chain_starts)
    add_attribute(Attribute.LENGTH     , lengths)
    add_attribute(Attribute.AABB_MIN   , aabb_mins)
    add_attribute(Attribute.AABB_MAX   , aabb_maxs)
        
    b3d_utils.set_object_mode(_obj, prev_mode)


# -----------------------------------------------------------------------------
def is_dataset(_obj:Object):
    if _obj.type != 'MESH': return False

    for att in Attribute:
        if att.type == AttributeType.NONE: continue
        if att.label not in _obj.data.attributes:
            return False
        
    return True


# -----------------------------------------------------------------------------
def create_polyline(_dataset:Dataset, _name='DATASET') -> Object:
    # Create polyline
    verts = _dataset[:, Attribute.LOCATION.value]
    edges = []

    for i in range(len(verts) - 1):
        edges.append( (i, i + 1) )
    
    mesh = b3d_utils.new_mesh(verts, edges, [], _name)
    obj = b3d_utils.new_object(_name, mesh)  

    # Add dataset to obj
    to_dataset(obj, _dataset)

    return obj


# -----------------------------------------------------------------------------
def attribute_layers(_bm:BMesh) -> Generator[BMLayerAccessVert, None, None]:
    layers = _bm.verts.layers
    for att in Attribute:
        match(att.type):
            case AttributeType.INT:
                yield layers.int.get(att.label)
            case AttributeType.FLOAT_VECTOR:
                yield layers.float_vector.get(att.label)


# -----------------------------------------------------------------------------
def dataset_entries(_obj:Object) -> Generator[DatabaseEntry, None, None]:
    bm = b3d_utils.get_bmesh(_obj)

    def retrieve_entry(vert):
        entry = DatabaseEntry()
        entry[Attribute.LOCATION.value] = vert.co

        for layer in attribute_layers(bm):
            entry[layer.name] = vert[layer]

        return entry

    bm.verts.ensure_lookup_table()

    for v1, v2 in zip(bm.verts, bm.verts[1:]):
        entry = retrieve_entry(v1)
        
        # Check if v1 and v2 (consecutive vertices) are connected
        c = False
        if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
            c = True

        entry[Attribute.CONNECTED.value] = c

        yield entry
    
    entry = retrieve_entry(bm.verts[-1])
    entry[Attribute.CONNECTED.value] = False

    yield entry


# -----------------------------------------------------------------------------
def dataset_sequences(_obj:Object):
    """Yields ( state, list of locations, total length, connected )"""
    entries = dataset_entries(_obj)
    entry0 = next(entries)

    return db_entry_sequences(entry0, entries)


# -----------------------------------------------------------------------------
def resolve_overlap(_obj:Object):
    if not is_dataset(_obj): return
    if _obj.mode != 'EDIT': return

    mesh = _obj.data
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


# -----------------------------------------------------------------------------
def set_player_state(_obj:Object, _new_state:int):
    if _obj.mode != 'EDIT': return
    if not is_dataset(_obj): return
    
    bm = b3d_utils.get_bmesh(_obj)

    state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

    for v in bm.verts:
        if v.select:
            v[state_layer] = _new_state

    bmesh.update_edit_mesh(_obj.data)


# -----------------------------------------------------------------------------
def select_transitions(_obj:Object, _filter:str='', _restrict:bool=False):
    if not is_dataset(_obj): return
    if _obj.mode != 'EDIT': return

    # Transform str to int
    if _filter:
        _filter = _filter.split(',')
        _filter = [int(s) if s.isnumeric() else State[s] for s in _filter]

    mesh = _obj.data
    bm = bmesh.from_edit_mesh(mesh)

    # Select transitions
    state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

    b3d_utils.deselect_all_vertices(bm)

    for k in range(len(bm.verts) - 1):
        v1 = bm.verts[k]
        v2 = bm.verts[k + 1]
        
        s1 = v1[state_layer]
        s2 = v2[state_layer]

        if s1 == s2: continue

        if _filter: 
            if s1 not in _filter and s2 not in _filter:
                continue
            if _restrict:
                if s1 not in _filter or s2 not in _filter:
                    continue                    

        v1.select = True
        v2.select = True

    bmesh.update_edit_mesh(mesh)
    

# -----------------------------------------------------------------------------
def select_player_states(_obj:Object, _filter:str=''):
    if not _filter: return
    if not is_dataset(_obj): return
    if _obj.mode != 'EDIT': return

    # Transform str to int
    if _filter:
        _filter = _filter.split(',')
        _filter = [int(s) if s.isnumeric() else State[s] for s in _filter]

    mesh = _obj.data
    bm = bmesh.from_edit_mesh(mesh)

    # Select transitions
    state_layer = bm.verts.layers.int.get(Attribute.STATE.label)

    b3d_utils.deselect_all_vertices(bm)

    for v in bm.verts:
        s = v[state_layer]

        if s in _filter:
            v.select = True

    bmesh.update_edit_mesh(mesh)



