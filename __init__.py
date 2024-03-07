bl_info = {
    "name" : "Map Generator",
    "author" : "Tariq Bakhtali (didibib)",
    "description" : "",
    "blender" : (3, 4, 0),
    "version" : (1, 0, 0),
    "location" : "",
    "warning" : "",
    "category" : "MEdge Tools"
}


# -----------------------------------------------------------------------------
import bpy

from . import auto_load


# -----------------------------------------------------------------------------
def register():
    auto_load.init()
    auto_load.register()


# -----------------------------------------------------------------------------
def unregister():
    auto_load.unregister()