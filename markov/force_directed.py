from bpy.types        import Scene, Depsgraph, Object
from bpy.app.handlers import frame_change_post, persistent

from ..      import b3d_utils
from .chains import GeneratedChain


# -----------------------------------------------------------------------------
generated_chain = None

# -----------------------------------------------------------------------------
def begin(obj: Object):
    pass    

# -----------------------------------------------------------------------------
def end():
    generated_chain = None


# -----------------------------------------------------------------------------

def run(): 
    if not generated_chain: return
    print('running force directed')


# -----------------------------------------------------------------------------
@persistent
def frame_change_post_callback(scene: Scene, depsgraph: Depsgraph):
    run()


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    b3d_utils.add_callback(frame_change_post, frame_change_post_callback)


# -----------------------------------------------------------------------------
def unregister():
    b3d_utils.remove_callback(frame_change_post, frame_change_post_callback)
