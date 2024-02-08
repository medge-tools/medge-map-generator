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
import  bpy
from    .           import auto_load
from    .io_ops     import MET_OT_ImportDataset
from    .props      import *
from    .dataset    import *


# -----------------------------------------------------------------------------
def menu_func_import_dataset(self, context):
    self.layout.operator(MET_OT_ImportDataset.bl_idname, text='MEdge Dataset (.json)')


# -----------------------------------------------------------------------------
def register():
    auto_load.init()
    auto_load.register()
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_dataset)

    bpy.types.Mesh.medge_dataset = bpy.props.PointerProperty(type=MET_MESH_PG_Dataset)
    bpy.types.Scene.invoked_datavis = bpy.props.BoolProperty(default=False)

# -----------------------------------------------------------------------------
def unregister():
    del bpy.types.Mesh.medge_dataset

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_dataset)

    auto_load.unregister()
    