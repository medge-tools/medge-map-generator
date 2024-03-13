import  bmesh
from    mathutils   import Vector
from    bpy.types   import Object, Mesh

import ntpath
import json
import numpy as np
from enum import Enum

from ..         import b3d_utils
from .movement  import State


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
    

    TIMESTAMP       = 0, 'timestamp'
    PLAYER_STATE    = 1, 'player_state'
    LOCATION        = 2, 'location'
    CONNECTED       = 3, 'connected'


# -----------------------------------------------------------------------------
class Dataset(np.ndarray):
    def __new__(cls):
        return super().__new__(cls, (0, len(Attribute)), dtype=object, buffer=None, offset=0, strides=None, order=None)

    @staticmethod
    def append(data,
               player_state: int,
               location: Vector,
               timestamp = Vector((0, 0, 0)),
               connected: bool = True):
        values = [0 for _ in range(len(Attribute))]
        
        values[Attribute.TIMESTAMP.value] = timestamp
        values[Attribute.PLAYER_STATE.value] = player_state
        values[Attribute.LOCATION.value] = location
        values[Attribute.CONNECTED.value] = connected

        return np.append(data, [values], axis=0)

    @staticmethod
    def extend(data, other):
        return np.concatenate((data, other), axis=0)


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

            dataset = Dataset.append(dataset, player_state, location, timestamp)
        
        name = ntpath.basename(filepath)
        DatasetOps.create_polyline(dataset, name)


    def write_to_file(self, filepath: str) -> None:
        pass


# -----------------------------------------------------------------------------
class DatasetOps:

    @staticmethod
    def convert_to_dataset(obj: Object, dataset: Dataset):
        packed = list(dataset[:, Attribute.TIMESTAMP.value])
        timestamps = [0] * len(packed) * 3

        for k in range(len(packed)): 
            timestamps[k * 3 + 0] = packed[k].x
            timestamps[k * 3 + 1] = packed[k].y
            timestamps[k * 3 + 2] = packed[k].z

        player_states = list(dataset[:, Attribute.PLAYER_STATE.value] )

        t = obj.data.attributes.new(name=Attribute.TIMESTAMP.label, type='FLOAT_VECTOR', domain='POINT')
        t.data.foreach_set('vector', timestamps)

        p = obj.data.attributes.new(name=Attribute.PLAYER_STATE.label, type='INT', domain='POINT')
        p.data.foreach_set('value', player_states)


    @staticmethod
    def is_dataset(data: Mesh):
        if Attribute.TIMESTAMP.label not in data.attributes:
            return False
        if Attribute.PLAYER_STATE.label not in data.attributes:
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

            dataset = Dataset.append(dataset, s, l, t, c)
        
        s, l, t = retrieve(bm.verts[-1])
        dataset = Dataset.append(dataset, s, l, t, False)
        
        return dataset


    @staticmethod
    def resolve_overlap(obj: Object):
        """Necessary after snapping to grid"""
        mesh = obj.data

        if not DatasetOps.is_dataset(mesh): return
        if obj.mode != 'EDIT': return

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

        mesh = obj.data

        if not DatasetOps.is_dataset(mesh): 
            DatasetOps.convert_to_dataset(mesh)
        
        # Transform str to int
        bm = bmesh.from_edit_mesh(mesh)

        state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

        for v in bm.verts:
            if v.select:
                v[state_layer] = new_state

        bmesh.update_edit_mesh(mesh)


    @staticmethod
    def select_transitions(obj: Object, filter: str = '', restrict: bool = False):
        mesh = obj.data

        if not DatasetOps.is_dataset(mesh): return
        if obj.mode != 'EDIT': return

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

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
        mesh = obj.data

        if not filter: return
        if not DatasetOps.is_dataset(mesh): return
        if obj.mode != 'EDIT': return

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        bm = bmesh.from_edit_mesh(mesh)

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)

        b3d_utils.deselect_all_vertices(bm)

        for v in bm.verts:
            s = v[state_layer]

            if s in filter:
                v.select = True
            

        bmesh.update_edit_mesh(mesh)



