from bpy.types import Panel, Context, Scene
from bpy.props import EnumProperty

from ..prefs import get_prefs


# -----------------------------------------------------------------------------
class MEdgeToolsPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'


# -----------------------------------------------------------------------------
class MET_PT_map_gen_panel(MEdgeToolsPanel, Panel):
    bl_idname = 'MET_PT_map_gen_panel'
    bl_label = 'Map Generation'


    def draw(self, _context:Context):
        scene = _context.scene
        
        layout = self.layout

        row = layout.row()
        row.scale_y = 1.2
        row.prop(scene, 'medge_map_gen_active_tab', expand=True)


# -----------------------------------------------------------------------------
class DatasetTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname

    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'DATASET'
    

# -----------------------------------------------------------------------------
class GenerateTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname

    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'GENERATE'


# -----------------------------------------------------------------------------
class ModulesTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname

    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'MODULES'


# -----------------------------------------------------------------------------
class ExportTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname

    @classmethod
    def poll(cls, _context:Context):
        return _context.scene.medge_map_gen_active_tab == 'EXPORT'
    

# -----------------------------------------------------------------------------
class EvaluateTab:
    bl_parent_id = MET_PT_map_gen_panel.bl_idname
    
    @classmethod
    def poll(cls, _context:Context):
        return get_prefs().enable_evaluation


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
def register():
    Scene.medge_map_gen_active_tab = EnumProperty(items=(
        ('DATASET' , 'Dataset' , 'Dataset Tab'), 
        ('MODULES' , 'Modules' , 'Modules Tab'),
        ('GENERATE', 'Generate', 'Generate Tab'),
        ('EXPORT'  , 'Export'  , 'Export Tab'),
    ))


# -----------------------------------------------------------------------------
def unregister():
    if hasattr(Scene, 'medge_map_gen_active_tab'): del Scene.medge_map_gen_active_tab