import  bmesh
from    mathutils   import Vector
from    bpy.types   import Object
from    bmesh.types import BMesh

import ntpath
import json
import numpy as np
from enum import Enum
from collections import UserList

from ..        import b3d_utils
from .movement import PlayerState


# -----------------------------------------------------------------------------
class AttributeType(str, Enum):
    NONE = 'NONE'
    INT = 'INT'
    FLOAT_VECTOR = 'FLOAT_VECTOR'

# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/43862184/associating-string-representations-with-an-enum-that-uses-integer-values
class Attribute(int, Enum):
    def __new__(cls, 
                value: int, 
                label: str, 
                type: str):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.type = type
        return obj
    
    def __int__(self):
        return self.value
    
    @classmethod
    def from_string(cls, s):
        for att in cls:
            if att.label == s:
                return att
        raise ValueError(cls.__name__ + ' has no value matching "' + s + '"')


    PLAYER_STATE    = 0, 'player_state' , AttributeType.INT
    LOCATION        = 1, 'location'     , AttributeType.NONE
    TIMESTAMP       = 2, 'timestamp'    , AttributeType.FLOAT_VECTOR
    CONNECTED       = 3, 'connected'    , AttributeType.INT
    CHAIN_START     = 4, 'chain_start'  , AttributeType.INT
    # If CHAIN_START is True then LENGTH is the length of the chain
    # Else LENGTH is the distance to CHAIN_START
    LENGTH          = 5, 'length'       , AttributeType.INT
    AABB_MIN        = 6, 'aabb_min'     , AttributeType.FLOAT_VECTOR
    AABB_MAX        = 7, 'aabb_max'     , AttributeType.FLOAT_VECTOR


# -----------------------------------------------------------------------------
class DatabaseEntry(UserList):
    def __init__(self) -> None:
        self.data = []
        for att in Attribute:
            match(att.type):
                case AttributeType.NONE:
                    self.data.append(None)
                case AttributeType.INT:
                    self.data.append(0)
                case AttributeType.FLOAT_VECTOR:
                    self.data.append(Vector())


    def __getitem__(self, key: int | str):
        if isinstance(key, int):
            return self.data[key]
        if isinstance(key, str):
            return self.data[Attribute.from_string(key).value]
    

    def __setitem__(self, key, value):
        if isinstance(key, int):        
            self.data[key] = value
        if isinstance(key, str):
            self.data[Attribute.from_string(key).value] = value


# -----------------------------------------------------------------------------
class Dataset:
    def __init__(self):
        self.data = np.empty((0, len(Attribute)), dtype=object)

    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __len__(self):
        return len(self.data)
    
   
    def append(self, entry: DatabaseEntry):
        V = np.array([entry], dtype=object)
        self.data = np.append(self.data, V, axis=0)


    def extend(self, other):
        self.data = np.concatenate((self.data, other.data), axis=0)


    def seqs_per_state(self):
        # Init dictionary
        sequences: dict[int, list[list[Vector]]] = {}

        for entry in self.data:
            sequences.setdefault(entry[Attribute.PLAYER_STATE.value], [])    
        
        entry0 = self.data[0]
        curr_state = entry0[Attribute.PLAYER_STATE.value]
        curr_chain = [entry0[Attribute.LOCATION.value]]
        
        sequences[curr_state].append(curr_chain)

        for entry in self.data[1:]:
            s = entry[Attribute.PLAYER_STATE.value]
            l = entry[Attribute.LOCATION.value]

            if s == curr_state:
                curr_chain.append(l)
            else:
                curr_chain = [l]
                curr_state = s
                sequences[s].append(curr_chain)

        return sequences


# -----------------------------------------------------------------------------
class DatasetIO:
    def import_from_file(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            log = json.load(f)

        dataset = Dataset()

        for item in log:
            player_state = int(item[Attribute.PLAYER_STATE.label])

            ts = str(item[Attribute.TIMESTAMP.label]).split(':')
            timestamp = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            x = float(item[Attribute.LOCATION.label]['x'])
            y = float(item[Attribute.LOCATION.label]['y'])
            z = float(item[Attribute.LOCATION.label]['z'])
            location = Vector((x * -1, y, z))

            entry = DatabaseEntry()
            entry[Attribute.PLAYER_STATE.value] = player_state
            entry[Attribute.TIMESTAMP.value] = timestamp
            entry[Attribute.LOCATION.value] = location

            dataset.append(entry)

        name = ntpath.basename(filepath)
        create_polyline(dataset, name)


    def write_to_file(self, filepath: str) -> None:
        pass


# -----------------------------------------------------------------------------
def object_to_dataset(obj: Object, dataset: Dataset = None):
    prev_mode = obj.mode
    b3d_utils.set_object_mode(obj, 'OBJECT')
    mesh = obj.data
    
    n             = len(mesh.vertices)
    player_states = [PlayerState.Walking.value] * n
    timestamps    = [0] * n * 3
    connections     = [True] * n
    chain_starts  = [False] * n
    lengths       = [0] * n
    aabb_mins     = [0] * n * 3
    aabb_maxs     = [0] * n * 3


    def unpack(packed : list, dest : list):
        for k in range(n):
            dest[k * 3 + 0] = packed[k].x
            dest[k * 3 + 1] = packed[k].y
            dest[k * 3 + 2] = packed[k].z


    if dataset:
        player_states = list(dataset[:, Attribute.PLAYER_STATE.value] )

        packed_ts = list(dataset[:, Attribute.TIMESTAMP.value])
        unpack(packed_ts, timestamps)

        connections = list(dataset[:, Attribute.CONNECTED.value])
        chain_starts  = list(dataset[:, Attribute.CHAIN_START.value])
        lengths = list(dataset[:, Attribute.LENGTH.value])

        packed_mins = list(dataset[:, Attribute.AABB_MIN.value])
        packed_maxs = list(dataset[:, Attribute.AABB_MAX.value])
        unpack(packed_mins, aabb_mins)
        unpack(packed_maxs, aabb_maxs)


    def add_attribute(att: Attribute, data: list):
        if att.label not in mesh.attributes:
            x = mesh.attributes.new(name=att.label, type=att.type, domain='POINT')
            match(att.type):
                case AttributeType.INT:
                    x.data.foreach_set('value', data)
                case AttributeType.FLOAT_VECTOR:
                    x.data.foreach_set('vector', data)


    add_attribute(Attribute.PLAYER_STATE, player_states)
    add_attribute(Attribute.TIMESTAMP   , timestamps)
    add_attribute(Attribute.CONNECTED   , connections)
    add_attribute(Attribute.CHAIN_START , chain_starts)
    add_attribute(Attribute.LENGTH      , lengths)
    add_attribute(Attribute.AABB_MIN    , aabb_mins)
    add_attribute(Attribute.AABB_MAX    , aabb_maxs)
        
    b3d_utils.set_object_mode(obj, prev_mode)


# -----------------------------------------------------------------------------
def yield_attribute_layers(bm: BMesh):
    layers = bm.verts.layers
    for att in Attribute:
        match(att.type):
            case AttributeType.INT:
                yield layers.int.get(att.label)
            case AttributeType.FLOAT_VECTOR:
                yield layers.float_vector.get(att.label)


# -----------------------------------------------------------------------------
def is_dataset(obj: Object):
    if obj.type != 'MESH': return False
    for att in Attribute:
        if att.type == AttributeType.NONE: continue
        if att.label not in obj.data.attributes:
            print(obj.name + ' is missing dataset attribute: ' + att.label)
            return False
    return True


# -----------------------------------------------------------------------------
def create_polyline(dataset: Dataset, name = 'DATASET') -> Object:
    # Create polyline
    verts = dataset[:, Attribute.LOCATION.value]
    edges = []

    for i in range(len(verts) - 1):
        edges.append( (i, i + 1) )
    
    mesh = b3d_utils.create_mesh(verts, edges, [], name)
    obj = b3d_utils.new_object(name, mesh)  

    # Add dataset to obj
    object_to_dataset(obj, dataset)

    return obj


# -----------------------------------------------------------------------------
def get_dataset(obj: Object) -> Dataset | None:
    if not is_dataset(obj): return None

    bm = b3d_utils.get_bmesh(obj)

    def retrieve_entry(vert):
        entry = DatabaseEntry()
        entry[Attribute.LOCATION.label] = vert.co
        for layer in yield_attribute_layers(bm):
            entry[layer.name] = vert[layer]
        return entry

    dataset = Dataset()

    bm.verts.ensure_lookup_table()

    for v1, v2 in zip(bm.verts, bm.verts[1:]):
        entry = retrieve_entry(v1)
        
        # Check if v1 and v2 (consecutive vertices) are connected
        c = False
        if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
            c = True

        entry[Attribute.CONNECTED.label] = c
        dataset.append(entry)
    
    entry = retrieve_entry(bm.verts[-1])
    entry[Attribute.CONNECTED.label] = False
    dataset.append(entry)
    
    return dataset


# -----------------------------------------------------------------------------
def resolve_overlap(obj: Object):
    if not is_dataset(obj): return
    if obj.mode != 'EDIT': return

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


# -----------------------------------------------------------------------------
def set_player_state(obj: Object, new_state: int):
    if obj.mode != 'EDIT': return
    if not is_dataset(obj): 
        object_to_dataset(obj)
    
    # Transform str to int
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

    for v in bm.verts:
        if v.select:
            v[state_layer] = new_state

    bmesh.update_edit_mesh(mesh)


# -----------------------------------------------------------------------------
def select_transitions(obj: Object, filter: str = '', restrict: bool = False):
    if not is_dataset(obj): return
    if obj.mode != 'EDIT': return

    # Transform str to int
    if filter:
        filter = filter.split(',')
        filter = [int(s) if s.isnumeric() else PlayerState[s] for s in filter]

    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    # Select transitions
    state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

    b3d_utils.deselect_all_vertices(bm)

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

    bmesh.update_edit_mesh(mesh)
    

# -----------------------------------------------------------------------------
def select_player_states(obj: Object, filter: str = ''):

    if not filter: return
    if not is_dataset(obj): return
    if obj.mode != 'EDIT': return

    # Transform str to int
    if filter:
        filter = filter.split(',')
        filter = [int(s) if s.isnumeric() else PlayerState[s] for s in filter]

    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    # Select transitions
    state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

    b3d_utils.deselect_all_vertices(bm)

    for v in bm.verts:
        s = v[state_layer]

        if s in filter:
            v.select = True
        

    bmesh.update_edit_mesh(mesh)



