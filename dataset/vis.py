import  blf
import  bmesh
from    bpy_extras  import view3d_utils
from    bpy.types   import Context, SpaceView3D

from ..         import b3d_utils
from .dataset   import Attribute, DatasetOps
from .movement  import State
from .props     import get_dataset

# -----------------------------------------------------------------------------
draw_handle = None

class DatasetVis():
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

        mesh = obj.data

        if not DatasetOps.is_dataset(mesh): return
        if obj.mode != 'EDIT': return

        bm = bmesh.from_edit_mesh(mesh)
        
        # Draw 
        region = context.region
        region_3d = context.space_data.region_3d
        view_mat = region_3d.view_matrix

        state_layer = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)
        time_layer = bm.verts.layers.float_vector.get(Attribute.TIMESTAMP.label)

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
                state = State(state).name

            blf.size(0, font_size * 1.5)
            blf.position(0, co_2d[0] - font_size, co_2d[1], 0)
            blf.draw(0, str(state))