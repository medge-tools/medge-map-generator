import  bpy
import  blf
from    bpy_extras  import view3d_utils
from    mathutils   import Vector
from    bpy.types   import Context, Object, Mesh, Operator

import json

from . import utils
from . import dataset_utils as dsu

# -----------------------------------------------------------------------------
TIMESTAMP = 'timestamp'
PLAYER_STATE = 'player_state'
LOCATION = 'location'


class DatasetIO:
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
        verts = []
        edges = []
        
        for entry in entries:
            verts.append( entry[LOCATION] )
            
        for i in range(len(verts) - 1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = utils.create_mesh(verts, edges, [], 'PLAYER_PATH')
        obj = utils.new_object('PLAYER PATH', mesh)  

        # Add attributes
        timestamps = utils.unpack([entry[TIMESTAMP] for entry in entries])
        player_states = [entry[PLAYER_STATE] for entry in entries]

        a = obj.data.attributes.new(name=TIMESTAMP, type='FLOAT_VECTOR', domain='POINT')
        a.data.foreach_set('vector', timestamps)
        
        b = obj.data.attributes.new(name=PLAYER_STATE, type='INT', domain='POINT')
        b.data.foreach_set('value', player_states)  


# -----------------------------------------------------------------------------
class DatasetVis:

    @staticmethod
    def draw_callback_px(caller, context: Context):
        obj = context.active_object

        if not obj: return

        mesh : Mesh = obj.data
        dataset = dsu.get_medge_dataset(obj)

        if not dataset.overlay_data: return
        if PLAYER_STATE not in mesh.attributes: return

        region = context.region
        region_3d = context.space_data.region_3d

        player_states = [0] * len(mesh.vertices)
        x = mesh.attributes[PLAYER_STATE]

        T = obj.matrix_world

        for k, vert in enumerate(mesh.vertices):
            co = view3d_utils.location_3d_to_region_2d(region, region_3d, T@vert.co)
            if not co: continue
            state = player_states[k]
            
            blf.size(0, 13, 72)
            blf.position(0, co[0], co[1], 0)
            blf.draw(0, str(state))

# -----------------------------------------------------------------------------
class DatasetOps:
    pass