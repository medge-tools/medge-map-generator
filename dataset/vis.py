import  blf
import  bmesh
from    bpy_extras  import view3d_utils
from    bpy.types   import Context, SpaceView3D

from ..         import b3d_utils
from .dataset   import Attribute
from .movement  import PlayerState
from .          import props, dataset

# -----------------------------------------------------------------------------
draw_handle_post_pixel = None
draw_handle_post_view = None


# -----------------------------------------------------------------------------
def draw_callback_post_pixel(_context:Context):
    # Validate
    obj = _context.object
    if not obj: return
    if not dataset.is_dataset(obj): return
    if obj.mode != 'EDIT': return

    bm = bmesh.from_edit_mesh(obj.data)
    
    # Region
    region    = _context.region
    region_3d = _context.space_data.region_3d
    view_mat  = region_3d.view_matrix

    # Layers
    state_layer       = bm.verts.layers.int.get(Attribute.PLAYER_STATE.label)
    time_layer        = bm.verts.layers.float_vector.get(Attribute.TIMESTAMP.label)
    chain_start_layer = bm.verts.layers.int.get(Attribute.CHAIN_START.label)

    # Settings
    vis_settings      = props.get_dataset(obj).get_vis_settings()
    min_draw_distance = vis_settings.min_draw_distance
    max_draw_distance = vis_settings.max_draw_distance
    default_color     = vis_settings.default_color
    start_chain_color = vis_settings.start_chain_color
    font_size         = vis_settings.font_size
    
    # Draw
    for v in bm.verts:
        # Only visualize selection
        if vis_settings.only_selection:
            if not v.select: continue

        # Get 2D coordinate
        location = obj.matrix_world @ v.co
        co_2d = view3d_utils.location_3d_to_region_2d(region, region_3d, location)

        if not co_2d: continue
        
        # Get distance to virtual camera
        if region_3d.is_perspective:
            distance = (view_mat @ v.co).length
        else:
            distance = -(view_mat @ v.co).z

        # Use distance to alpha blend
        alpha = b3d_utils.map_range(distance, min_draw_distance, max_draw_distance, 1, 0)
        
        if alpha <= 0: continue

        # Set color 
        if v[chain_start_layer]:
            blf.color(0, *start_chain_color, alpha)
        else:
            blf.color(0, *default_color, alpha)

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
            state = PlayerState(state).name

        blf.size(0, font_size * 1.5)
        blf.position(0, co_2d[0] - font_size, co_2d[1], 0)
        blf.draw(0, str(state))


# -----------------------------------------------------------------------------
def draw_callback_post_view(_context:Context): 
    # Validate
    obj = _context.object
    if not obj: return
    if not dataset.is_dataset(obj): return
    if obj.mode != 'EDIT': return

    bm = bmesh.from_edit_mesh(obj.data)
    
    # Layers
    chain_start_layer = bm.verts.layers.int.get(Attribute.CHAIN_START.label)
    aabb_min_layer    = bm.verts.layers.float_vector.get(Attribute.AABB_MIN.label)
    aabb_max_layer    = bm.verts.layers.float_vector.get(Attribute.AABB_MAX.label)
    
    # Settings
    vis_settings  = props.get_dataset(obj).get_vis_settings()
    default_color = vis_settings.default_color
    draw_abbb     = vis_settings.draw_aabb

    # Draw AABB 
    for v in bm.verts:
        if draw_abbb:
            if v[chain_start_layer]:
                bmin = obj.matrix_world @ v[aabb_min_layer] 
                bmax = obj.matrix_world @ v[aabb_max_layer]

                b3d_utils.draw_aabb_lines_3d(bmin, bmax, default_color)


# -----------------------------------------------------------------------------
def add_handle(_context:Context):
    global draw_handle_post_pixel
    global draw_handle_post_view

    if draw_handle_post_pixel or draw_handle_post_view:
        remove_handle()

    draw_handle_post_pixel = SpaceView3D.draw_handler_add(
        draw_callback_post_pixel,(_context,), 'WINDOW', 'POST_PIXEL')
    draw_handle_post_view = SpaceView3D.draw_handler_add(
        draw_callback_post_view,(_context,), 'WINDOW', 'POST_VIEW')


# -----------------------------------------------------------------------------
def remove_handle():
    global draw_handle_post_pixel
    global draw_handle_post_view

    if draw_handle_post_pixel:
        SpaceView3D.draw_handler_remove(draw_handle_post_pixel, 'WINDOW')
        draw_handle_post_pixel = None

    if draw_handle_post_view:
        SpaceView3D.draw_handler_remove(draw_handle_post_view, 'WINDOW')
        draw_handle_post_view = None
