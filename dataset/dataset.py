import  bmesh
from    mathutils   import Vector
from    bpy.types   import Object, Mesh

import json

from ..         import b3d_utils
from .movement  import State


# -----------------------------------------------------------------------------
class Attributes:
    TIMESTAMP = 'timestamp'
    PLAYER_STATE = 'player_state'
    LOCATION = 'location'


class Dataset(list):
    def append(self, player_state: int, location: Vector, timestamp = Vector((0, 0, 0))):
        super().append({
            Attributes.TIMESTAMP    : timestamp,
            Attributes.PLAYER_STATE : player_state,
            Attributes.LOCATION     : location,
        })


# -----------------------------------------------------------------------------
class DatasetIO:
    def import_from_file(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            log = json.load(f)

        dataset = Dataset()

        for item in log:
            player_state = int(item[Attributes.PLAYER_STATE])

            ts = str(item[Attributes.TIMESTAMP]).split(':')
            timestamp = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            x = float(item[Attributes.LOCATION]['x'])
            y = float(item[Attributes.LOCATION]['y'])
            z = float(item[Attributes.LOCATION]['z'])
            location = Vector((x * -1, y, z))

            dataset.append(player_state, location, timestamp)
        
        DatasetOps.create_polyline(dataset)

    def write_to_file(self, filepath: str) -> None:
        pass


# -----------------------------------------------------------------------------
class DatasetOps:

    @staticmethod
    def make_dataset(obj: Object):
        t = obj.data.attributes.new(name=Attributes.TIMESTAMP, type='FLOAT_VECTOR', domain='POINT')
        p = obj.data.attributes.new(name=Attributes.PLAYER_STATE, type='INT', domain='POINT')
        return t, p


    @staticmethod
    def is_dataset(data: Mesh):
        if Attributes.TIMESTAMP not in data.attributes:
            return False
        if Attributes.PLAYER_STATE not in data.attributes:
            return False
        return True
    

    @staticmethod
    def create_polyline(dataset: Dataset, name = 'DATASET'):
        # Create polyline
        verts = []
        edges = []
        
        for entry in dataset:
            verts.append( entry[Attributes.LOCATION] )
            
        for i in range(len(verts) - 1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = b3d_utils.create_mesh(verts, edges, [], name)
        obj = b3d_utils.new_object(name, mesh)  

        # Add attributes
        packed: list[Vector] = [entry[Attributes.TIMESTAMP] for entry in dataset]
        timestamps = [0] * len(packed) * 3

        for k in range(len(packed)): 
            timestamps[k * 3 + 0] = packed[k].x
            timestamps[k * 3 + 1] = packed[k].y
            timestamps[k * 3 + 2] = packed[k].z

        player_states = [entry[Attributes.PLAYER_STATE] for entry in dataset]
        t, p = DatasetOps.make_dataset(obj)
        t.data.foreach_set('vector', timestamps)
        p.data.foreach_set('value', player_states)


    @staticmethod
    def get_data(obj: Object):
        """returns states, locations, timestamps, connected"""
        b3d_utils.set_object_mode(obj, 'OBJECT')

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)
        time_layer = bm.verts.layers.float_vector.get(Attributes.TIMESTAMP)

        states = []
        locations = []
        timestamps = []
        connected = []

        for v in bm.verts:
            state = v[state_layer]
            ts = v[time_layer]
            loc = v.co
            
            states.append(state)
            locations.append(loc)
            timestamps.append(ts)

        for v1, v2 in zip(bm.verts, bm.verts[1:]):
            if v2 in [x for y in [a.verts for a in v1.link_edges] for x in y if x != v1]:
                connected.append(True)
            else:
                connected.append(False)
        connected.append(False)

        return states, locations, timestamps, connected


    @staticmethod
    def resolve_overlap(obj: Object):
        """Necessary after snapping to grid"""
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
    def set_state(obj: Object, new_state):
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if not DatasetOps.is_dataset(obj): 
            DatasetOps.make_dataset(obj)
        
        # Transform str to int
        bm = bmesh.from_edit_mesh(mesh)

        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)

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
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)

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
            filter = [int(s) if s.isnumeric() else State[s] for s in filter]

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)

        b3d_utils.deselect_all_vertices(bm)

        for v in bm.verts:
            s = v[state_layer]

            if s in filter:
                v.select = True
            

        bmesh.update_edit_mesh(mesh)



