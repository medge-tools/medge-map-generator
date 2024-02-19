import  bpy, blf, bmesh
from    bpy_extras  import view3d_utils
from    mathutils   import Vector
from    bpy.types   import Context
from    bmesh.types import BMesh

import json

from .  import props
from .. import b3d_utils
from .  import movement


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


# -----------------------------------------------------------------------------
class DatasetOps:

    @staticmethod
    def create_polyline(dataset: Dataset):
        # Create polyline
        verts = []
        edges = []
        
        for entry in dataset:
            verts.append( entry[Attributes.LOCATION] )
            
        for i in range(len(verts) - 1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = b3d_utils.create_mesh(verts, edges, [], 'PLAYER_PATH')
        obj = b3d_utils.new_object('PLAYER PATH', mesh)  
        prop = props.get_dataset(obj)
        prop.is_dataset = True

        # Add attributes
        packed: list[Vector] = [entry[Attributes.TIMESTAMP] for entry in dataset]
        timestamps = [0] * len(packed) * 3

        for k in range(len(packed)): 
            timestamps[k * 3 + 0] = packed[k].x
            timestamps[k * 3 + 1] = packed[k].y
            timestamps[k * 3 + 2] = packed[k].z

        player_states = [entry[Attributes.PLAYER_STATE] for entry in dataset]

        a = obj.data.attributes.new(name=Attributes.TIMESTAMP, type='FLOAT_VECTOR', domain='POINT')
        a.data.foreach_set('vector', timestamps)
        
        b = obj.data.attributes.new(name=Attributes.PLAYER_STATE, type='INT', domain='POINT')
        b.data.foreach_set('value', player_states)  


    @staticmethod
    def get_data(bm: BMesh):
        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)
        time_layer = bm.verts.layers.float_vector.get(Attributes.TIMESTAMP)

        timestamps = []
        states = []
        locations = []

        for vert in bm.verts:
            ts = vert[time_layer]
            state = vert[state_layer]
            loc = vert.co
            
            timestamps.append(ts)
            states.append(state)
            locations.append(loc)

        return timestamps, states, locations


    @staticmethod
    def select_transitions(context: Context):
         # Validate
        obj = context.object

        if not obj: return
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if Attributes.PLAYER_STATE not in mesh.attributes: return
        if context.mode == 'EDIT_MESH':
            bm = bmeshes.get(mesh.name, bmesh.from_edit_mesh(mesh))
        else:
            bmeshes.clear()
            return

        # Select transitions
        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)

        b3d_utils.deselect_all_vertices(bm)

        for k in range(len(bm.verts) - 1):
            v1 = bm.verts[k]
            v2 = bm.verts[k + 1]
            
            s1 = v1[state_layer]
            s2 = v2[state_layer]

            if s1 == s2: continue

            v1.select = True
            v2.select = True

        bmesh.update_edit_mesh(mesh)


# -----------------------------------------------------------------------------
bmeshes = {}

class DatasetVis:
    def __init__(self, context) -> None:
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback,(context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')


    def draw_callback(self, context: Context):
        global bmeshes
        # Validate
        obj = context.object

        if not obj: return
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if Attributes.PLAYER_STATE not in mesh.attributes: return
        if context.mode == 'EDIT_MESH':
            bm = bmeshes.get(mesh.name, bmesh.from_edit_mesh(mesh))
        else:
            bmeshes.clear()
            return
        
        # Draw 
        region = context.region
        region_3d = context.space_data.region_3d

        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)
        time_layer = bm.verts.layers.float_vector.get(Attributes.TIMESTAMP)

        vis_settings = props.get_dataset(obj).vis_settings
        font_size = vis_settings.font_size

        for vert in bm.verts:
            if vis_settings.only_selection:
                if not vert.select: continue

            point = obj.matrix_world @ vert.co
            co = view3d_utils.location_3d_to_region_2d(region, region_3d, point)
            
            if not co: continue

            if vis_settings.show_timestamps:
                ts = vert[time_layer]
                
                blf.size(0, font_size)
                blf.position(0, co[0], co[1], 0)
                blf.draw(0, '{:.0f}:{:.0f}:{:.3f}'.format(*ts))
                co[1] += font_size

            state = vert[state_layer]
            
            if vis_settings.to_name:
                state = movement.State(state).name

            blf.size(0, font_size * 1.5)
            blf.position(0, co[0] - font_size, co[1], 0)
            blf.draw(0, str(state))



