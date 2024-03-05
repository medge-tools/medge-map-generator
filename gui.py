from bpy.types import Panel, Context


# -----------------------------------------------------------------------------
class MapGenMainPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'


class MET_PT_MapGenMainPanel(MapGenMainPanel, Panel):
    bl_idname = 'MET_PT_MapGenMainPanel'
    bl_label = 'Map Generator'
    
    def draw(self, context: Context):
        pass