import bpy
from bpy.types    import AddonPreferences, Context
from bpy.props    import BoolProperty


# -----------------------------------------------------------------------------
# Addon Prefences
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_map_gen_preferences(AddonPreferences):
    bl_idname = __package__

    enable_evaluation : BoolProperty(
        name='Enable Evaluation',
        default=False,
    )

    def draw(self, _context:Context):
        layout = self.layout
        layout.prop(self, 'enable_evaluation')


# -----------------------------------------------------------------------------
def get_prefs() -> MET_map_gen_preferences:
    return bpy.context.preferences.addons[__package__].preferences