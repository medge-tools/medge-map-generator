from bpy.types import Panel, Context, Scene
from bpy.props import EnumProperty


# -----------------------------------------------------------------------------
class MEdgeToolsPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'


# -----------------------------------------------------------------------------
class MET_PT_map_gen_panel(Panel, MEdgeToolsPanel):
    bl_idname = 'MET_PT_map_gen_panel'
    bl_label = 'Map Generation'


    def draw(self, _context:Context):
        scene = _context.scene
        
        layout = self.layout

        row = layout.row()
        row.scale_y = 1.2
        row.prop(scene, 'medge_map_gen_active_tab', expand=True)


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_map_gen_active_tab = EnumProperty(items=(
        ('DATASET', 'Dataset', 'Dataset Tab'), 
        ('MODULES', 'Modules', 'Modules Tab'),
        ('GENERATE', 'Generate', 'Generate Tab')
    ))


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_map_gen_active_tab'): del Scene.medge_map_gen_active_tab