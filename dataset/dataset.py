import  bpy, blf, bmesh
from    bpy_extras  import view3d_utils
from    mathutils   import Vector
from    bpy.types   import SpaceView3D, Context, Object

import json

from .props     import is_dataset, get_dataset
from ..         import b3d_utils
from .          import movement


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
        ds = get_dataset(obj)
        ds.is_dataset = True

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

        return states, locations, timestamps, connected


    @staticmethod
    def resolve_overlap(obj: Object):
        """Necessary after snapping to grid"""
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
    

    @staticmethod
    def set_state(obj: Object):
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if not is_dataset(obj): 
            player_states = [0] * len(mesh.vertices)
            a = obj.data.attributes.new(name=Attributes.PLAYER_STATE, type='INT', domain='POINT')
            a.data.foreach_set('value', player_states)
        
        # Get settings
        settings = get_dataset(obj).get_ops_settings()
        new_state = int(settings.new_state)

        # Transform str to int
        bm = bmesh.from_edit_mesh(mesh)

        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)

        for v in bm.verts:
            if v.select:
                v[state_layer] = new_state

        bmesh.update_edit_mesh(mesh)


    @staticmethod
    def select_transitions(obj: Object):
        if not is_dataset(obj): return
        if obj.mode != 'EDIT': return

        # Get settings
        settings = get_dataset(obj).get_ops_settings()
        filter = settings.filter
        restrict = settings.restrict

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else movement.State[s] for s in filter]

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
    def select_states(obj: Object):
        if not filter: return
        if not is_dataset(obj): return
        if obj.mode != 'EDIT': return

        
        # Get settings
        settings = get_dataset(obj).get_ops_settings()
        filter = settings.filter

        # Transform str to int
        if filter:
            filter = filter.split(',')
            filter = [int(s) if s.isnumeric() else movement.State[s] for s in filter]

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


# -----------------------------------------------------------------------------
draw_handle = None

class DatasetVis:

    def add_handle(self, context):
        global draw_handle
        if draw_handle:
            self.remove_handle()
        draw_handle = SpaceView3D.draw_handler_add(
            self.draw_callback,(context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        global draw_handle
        if draw_handle:
            SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
            draw_handle = None


    def draw_callback(self, context: Context):
        # Validate
        obj = context.object

        if not obj: return
        if not is_dataset(obj): return
        if obj.mode != 'EDIT': return

        mesh = obj.data

        bm = bmesh.from_edit_mesh(mesh)
        
        # Draw 
        region = context.region
        region_3d = context.space_data.region_3d
        view_mat = region_3d.view_matrix

        state_layer = bm.verts.layers.int.get(Attributes.PLAYER_STATE)
        time_layer = bm.verts.layers.float_vector.get(Attributes.TIMESTAMP)

        vis_settings = get_dataset(obj).get_vis_settings()
        min_draw_distance = vis_settings.min_draw_distance
        max_draw_distance = vis_settings.max_draw_distance
        color = vis_settings.color
        font_size = vis_settings.font_size

        for v in bm.verts:
            if vis_settings.only_selection:
                if not v.select: continue

            location = obj.matrix_world @ v.co
            co_2d = view3d_utils.location_3d_to_region_2d(region, region_3d, location)
            
            if not co_2d: continue
            
            # Get distance to virtual camera
            if region_3d.is_perspective:
                distance = (view_mat @ v.co).length
            else:
                distance = -(view_mat @ v.co).z

            alpha = b3d_utils.map_range(distance, min_draw_distance, max_draw_distance, 1, 0)
            
            if alpha <= 0: continue

            blf.color(0, *color, alpha)

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
                state = movement.State(state).name

            blf.size(0, font_size * 1.5)
            blf.position(0, co_2d[0] - font_size, co_2d[1], 0)
            blf.draw(0, str(state))
