import  bpy, blf, bmesh
from    bpy_extras  import view3d_utils
from    mathutils   import Vector
from    bpy.types   import Context, Object
from    .props      import *

import json

from . import b3d_utils
from . import movement

# -----------------------------------------------------------------------------
def get_medge_dataset(obj: Object) -> MET_MESH_PG_Dataset:
    return obj.data.medge_dataset

# -----------------------------------------------------------------------------
ATTR_TIMESTAMP = 'timestamp'
ATTR_PLAYER_STATE = 'player_state'
ATTR_LOCATION = 'location'


class DatasetIO:
    def import_from_file(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            log = json.load(f)

        entries = []

        for item in log:
            entry = {}

            ts = str(item[ATTR_TIMESTAMP]).split(':')
            entry[ATTR_TIMESTAMP] = Vector(( float(ts[0]), float(ts[1]), float(ts[2]) ))

            entry[ATTR_PLAYER_STATE] = int(item[ATTR_PLAYER_STATE])

            x = float(item[ATTR_LOCATION]['x'])
            y = float(item[ATTR_LOCATION]['y'])
            z = float(item[ATTR_LOCATION]['z'])
            entry[ATTR_LOCATION] = Vector((x * -1, y, z))

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
            verts.append( entry[ATTR_LOCATION] )
            
        for i in range(len(verts) - 1):
            edges.append( (i, i + 1) )
        
        # Add to scene
        mesh = b3d_utils.create_mesh(verts, edges, [], 'PLAYER_PATH')
        obj = b3d_utils.new_object('PLAYER PATH', mesh)  

        # Add attributes
        timestamps = b3d_utils.unpack([entry[ATTR_TIMESTAMP] for entry in entries])
        player_states = [entry[ATTR_PLAYER_STATE] for entry in entries]

        a = obj.data.attributes.new(name=ATTR_TIMESTAMP, type='FLOAT_VECTOR', domain='POINT')
        a.data.foreach_set('vector', timestamps)
        
        b = obj.data.attributes.new(name=ATTR_PLAYER_STATE, type='INT', domain='POINT')
        b.data.foreach_set('value', player_states)  


# -----------------------------------------------------------------------------
bmeshes = {}

class DatasetVis:
    def __init__(self, context) -> None:
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback,(context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')


    def draw_callback(self, context: Context):
        # Validate
        obj = context.object

        if not obj: return
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if ATTR_PLAYER_STATE not in mesh.attributes: return
        if context.mode == 'EDIT_MESH':
            bm = bmeshes.get(mesh.name, bmesh.from_edit_mesh(mesh))
        else:
            bmeshes.clear()
            return
        
        # Draw 
        region = context.region
        region_3d = context.space_data.region_3d

        state_layer = bm.verts.layers.int.get(ATTR_PLAYER_STATE)
        time_layer = bm.verts.layers.float_vector.get(ATTR_TIMESTAMP)

        vis_settings = get_medge_dataset(obj).vis_settings
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

            idx = vert[state_layer]
            state = movement.State(idx).name

            blf.size(0, font_size * 1.5)
            blf.position(0, co[0] - font_size, co[1], 0)
            blf.draw(0, str(state))



# -----------------------------------------------------------------------------
class DatasetOps:

    def select_transitions(self, context: Context):
         # Validate
        obj = context.object

        if not obj: return
        if obj.mode != 'EDIT': return

        mesh = obj.data

        if ATTR_PLAYER_STATE not in mesh.attributes: return
        if context.mode == 'EDIT_MESH':
            bm = bmeshes.get(mesh.name, bmesh.from_edit_mesh(mesh))
        else:
            bmeshes.clear()
            return

        # Select transitions
        state_layer = bm.verts.layers.int.get(ATTR_PLAYER_STATE)

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



