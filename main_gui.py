from bpy.types import Panel, Context


# -----------------------------------------------------------------------------
class MapGenPanel_DefaultProps:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'MEdge Tools'


# -----------------------------------------------------------------------------
class MET_PT_MapGenMainPanel(MapGenPanel_DefaultProps, Panel):
    bl_idname = 'MET_PT_MapGenMainPanel'
    bl_label = 'Map Generator'
    
    def draw(self, _context:Context):
        pass

