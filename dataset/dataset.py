import  bmesh
from    mathutils   import Vector
from    bpy.types   import Object, Mesh

import ntpath
import json
import numpy as np
from enum import Enum

from ..         import b3d_utils
from .movement  import PlayerState


# -----------------------------------------------------------------------------
# https://stackoverflow.com/questions/43862184/associating-string-representations-with-an-enum-that-uses-integer-values
class Attribute(int, Enum):
    def __new__(cls, value, label):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        return obj
    
    def __int__(self):
        return self.value
    
    PLAYER_STATE    = 0, 'player_state'
    LOCATION        = 1, 'location'
    TIMESTAMP       = 2, 'timestamp'
    CONNECTED       = 3, 'connected'
    CHAIN_START     = 4, 'chain_start'
    # If CHAIN_START is True then LENGTH is the length of the chain
    # Else LENGTH is the distance to CHAIN_START
    LENGTH          = 5, 'length'
    AABB_MIN        = 6, 'aabb_min'
    AABB_MAX        = 7, 'aabb_max'


# -----------------------------------------------------------------------------
class Dataset():
    def __init__(self):
        self.data = np.empty((0, len(Attribute)), dtype=object)

    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __len__(self):
        return len(self.data)
    

    def append(self,
               player_state : int,
               location     : Vector,
               timestamp    : Vector = Vector(),
               connected    : bool = True,
               chain_start  : bool = False,
               length : int = 0,
               aabb_min     : Vector = Vector(),
               aabb_max     : Vector = Vector()):
        
        entry = [0] * len(Attribute)

        entry[Attribute.PLAYER_STATE.value] = player_state
        entry[Attribute.LOCATION.value]     = location
        entry[Attribute.TIMESTAMP.value]    = timestamp
        entry[Attribute.CONNECTED.value]    = connected
        entry[Attribute.CHAIN_START.value]  = chain_start
        entry[Attribute.LENGTH.value] = length
        entry[Attribute.AABB_MIN.value]     = aabb_min
        entry[Attribute.AABB_MAX.value]     = aabb_max

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

            dataset.append(player_state, location, timestamp)
        
        name = ntpath.basename(filepath)
        DatasetOps.create_polyline(dataset, name)


    def write_to_file(self, filepath: str) -> None:
        pass


# -----------------------------------------------------------------------------
class DatasetOps:

    @staticmethod
    def convert_to_dataset(obj: Object, dataset: Dataset = None):
        prev_mode = obj.mode
        b3d_utils.set_object_mode(obj, 'OBJECT')
        mesh = obj.data

        if dataset:
            packed_ts = list(dataset[:, Attribute.TIMESTAMP.value])
            timestamps = [0] * len(packed_ts) * 3

            for k in range(len(packed_ts)): 
                timestamps[k * 3 + 0] = packed_ts[k].x
                timestamps[k * 3 + 1] = packed_ts[k].y
                timestamps[k * 3 + 2] = packed_ts[k].z

            player_states = list(dataset[:, Attribute.PLAYER_STATE.value] )
            chain_starts  = list(dataset[:, Attribute.CHAIN_START.value])
            lengths = list(dataset[:, Attribute.LENGTH.value])

            packed_mins = list(dataset[:, Attribute.AABB_MIN.value])
            packed_maxs = list(dataset[:, Attribute.AABB_MAX.value])
            aabb_mins   = [0] * len(packed_mins) * 3
            aabb_maxs   = [0] * len(packed_maxs) * 3

            for k in range(len(packed_mins)):
                aabb_mins[k * 3 + 0] = packed_mins[k].x
                aabb_mins[k * 3 + 1] = packed_mins[k].y
                aabb_mins[k * 3 + 2] = packed_mins[k].z

                aabb_maxs[k * 3 + 0] = packed_maxs[k].x
                aabb_maxs[k * 3 + 1] = packed_maxs[k].y
                aabb_maxs[k * 3 + 2] = packed_maxs[k].z

        else:
            n = len(mesh.vertices)
            timestamps    = [0] * n * 3
            player_states = [PlayerState.Walking.value] * n
            chain_starts  = [False] * n
            lengths       = [0] * n
            aabb_mins     = [0] * n * 3
            aabb_maxs     = [0] * n * 3
        
        if Attribute.TIMESTAMP.label not in mesh.attributes:
            t = mesh.attributes.new(name=Attribute.TIMESTAMP.label, type='FLOAT_VECTOR', domain='POINT')
            t.data.foreach_set('vector', timestamps)

        if Attribute.PLAYER_STATE.label not in mesh.attributes:
            p = mesh.attributes.new(name=Attribute.PLAYER_STATE.label, type='INT', domain='POINT')
            p.data.foreach_set('value', player_states)

        if Attribute.CHAIN_START.label not in mesh.attributes:
            # We have to store this as a INT (even tough it is a BOOLEAN),
            # otherwise we can't retrieve the value during a draw_callback
            cs = mesh.attributes.new(name=Attribute.CHAIN_START.label, type='INT', domain='POINT')
            cs.data.foreach_set('value', chain_starts)

        if Attribute.LENGTH.label not in mesh.attributes:
            cl = mesh.attributes.new(name=Attribute.LENGTH.label, type='INT', domain='POINT')
            cl.data.foreach_set('value', lengths)   

        if Attribute.AABB_MIN.label not in mesh.attributes:
            bmin = mesh.attributes.new(name=Attribute.AABB_MIN.label, type='FLOAT_VECTOR', domain='POINT')
            bmin.data.foreach_set('vector', aabb_mins)

        if Attribute.AABB_MAX.label not in mesh.attributes:
            bmax = mesh.attributes.new(name=Attribute.AABB_MAX.label, type='FLOAT_VECTOR', domain='POINT')
            bmax.data.foreach_set('vector', aabb_maxs)

        
        b3d_utils.set_object_mode(obj, prev_mode)


    @staticmethod
    def is_dataset(obj: Object):
        if obj.type != 'MESH': return False
        for att in Attribute:
            if att.name == Attribute.LOCATION.name: continue
            if att.name == Attribute.CONNECTED.name: continue
            if att.label not in obj.data.attributes:
                print(obj.name + ' is missing dataset attribute: ' + att.label)
                return False
        return True
    

    @staticmethod
    def create_polyline(dataset: Dataset, name = 'DATASET'):
        # Create polyline
        verts = dataset[:, Attribute.LOCATION.value]
        edges = []

        for i in range(len(verts) - 1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = b3d_utils.create_mesh(verts, edges, [], name)
        obj = b3d_utils.new_object(name, mesh)  

        DatasetOps.convert_to_dataset(obj, dataset)


    @staticmethod
    def get_dataset(obj: Object):
        b3d_utils.set_object_mode(obj, 'OBJECT')

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)
        time_layer = bm.verts.layers.float_vector.get(Attribute.TIMESTAMP.label)

        def retrieve(vert):
            s = vert[state_layer]
            l = vert.co
            t = vert[time_layer]
            return s, l, t

        dataset = Dataset()

        bm.verts.ensure_lookup_table()

        for v1, v2 in zip(bm.verts, bm.verts[1:]):
            s, l, t = retrieve(v1)
            
            # Check if v1 and v2 are connected
            c = False
            if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
                c = True

            dataset.append(s, l, t, c)
        
        s, l, t = retrieve(bm.verts[-1])
        dataset.append(s, l, t, False)
        
        return dataset


    @staticmethod
    def resolve_overlap(obj: Object):
        if not DatasetOps.is_dataset(obj): return
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
    

    @staticmethod
    def set_state(obj: Object, new_state: int):
        if obj.mode != 'EDIT': return
        if not DatasetOps.is_dataset(obj): 
            DatasetOps.convert_to_dataset(obj)
        
        # Transform str to int
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

        for v in bm.verts:
            if v.select:
                v[state_layer] = new_state

        bmesh.update_edit_mesh(mesh)


    @staticmethod
    def select_transitions(obj: Object, filter: str = '', restrict: bool = False):
        if not DatasetOps.is_dataset(obj): return
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
        

    @staticmethod
    def select_states(obj: Object, filter: str = ''):

        if not filter: return
        if not DatasetOps.is_dataset(obj): return
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



