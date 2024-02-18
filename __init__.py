bl_info = {
    "name" : "MEdge Tools: Dataset Editor",
    "author" : "Tariq Bakhtali (didibib)",
    "description" : "",
    "blender" : (3, 4, 0),
    "version" : (1, 0, 0),
    "location" : "",
    "warning" : "",
    "category" : "MEdge Tools"
}


# -----------------------------------------------------------------------------
from . import auto_load


# -----------------------------------------------------------------------------
def register():
    auto_load.init()
    auto_load.register()


# -----------------------------------------------------------------------------
def unregister():
    auto_load.unregister()