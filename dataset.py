import bpy
import  bmesh
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
bmeshes = {}
draw_handle = None

class DatasetVis:
    def __init__(self, context) -> None:
        draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback,(context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        bpy.types.SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')


    def draw_callback(self, context: Context):
        obj = context.object

        if obj.mode != 'EDIT': return

        mesh = obj.data
        
        if PLAYER_STATE not in mesh.attributes: return
        if context.mode == 'EDIT_MESH':
            bmeshes.setdefault(mesh.name, bmesh.from_edit_mesh(mesh))

        region = context.region
        region_3d = context.space_data.region_3d

        bm = bmeshes[mesh.name]
        layer = bm.verts.layers.int.get(PLAYER_STATE)

        for vert in bm.verts:
            point = obj.matrix_world @ vert.co
            co = view3d_utils.location_3d_to_region_2d(region, region_3d, point)
            
            if not co: continue

            state = vert[layer]
            
            blf.size(0, 13, 72)
            blf.position(0, co[0], co[1], 0)
            blf.draw(0, str(state))


# -----------------------------------------------------------------------------
class DatasetOps:
    pass