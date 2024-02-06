import bpy
import bmesh
from mathutils import Vector

import json

from . import utils

TIMESTAMP = 'timestamp'
PLAYER_STATE = 'player_state'
LOCATION = 'location'

class MET_Dataset:
    def import_from_file(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            log = json.load(f)

        entries = []

        for item in log:
            entry = {}

            ts = str(item[TIMESTAMP]).split(':')
            entry[TIMESTAMP] = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            entry[PLAYER_STATE] = int(item[PLAYER_STATE])

            x = float(item[LOCATION]['x'])
            y = float(item[LOCATION]['y'])
            z = float(item[LOCATION]['z'])
            entry[LOCATION] = Vector((x, y, z))

            entries.append(entry)
        
        self.create_scene(entries)


    def write_to_file(self, filepath: str) -> None:
        pass
        # data = list[dict]
        # for entry in self.entries:
        #     data['timestamp'] = entry.time
        #     data['player_state'] = entry.state
        #     data['location']['x'] = entry.location.x
        #     data['location']['y'] = entry.location.y
        #     data['location']['z'] = entry.location.z

        # dump = json.dumps(data, indent=4)

        # with open(filepath, 'w') as fp:
        #     fp.write(dump)


    def create_scene(self, entries : list) -> None:
        # Create polyline
        bm = bmesh.new()
        verts = []
        
        for entry in entries:
            verts.append( entry[LOCATION] )
            
        edges = []
        for i in range(len(verts)-1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = utils.create_mesh(verts, edges, [], 'PLAYER_PATH')
        obj = utils.new_object('PLAYER PATH', mesh)  

        # Add attributes
        timestamps = utils.unpack([entry[TIMESTAMP] for entry in entries])
        player_states = [entry[PLAYER_STATE] for entry in entries]

        a = obj.data.attributes.new(name='timestamp', type='FLOAT_VECTOR', domain='POINT')
        a.data.foreach_set('vector', timestamps)
        
        b = obj.data.attributes.new(name='player_state', type='INT', domain='POINT')
        b.data.foreach_set('value', player_states)  