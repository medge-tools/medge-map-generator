from bpy.types      import PropertyGroup, UILayout
from bpy.props      import *
from .dataset       import *


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    def draw(self, layout: UILayout):
        layout.prop(self, 'overlay_data')
        if self.overlay_data:
            layout.prop(self, 'overlay_selection')
            layout.prop(self, 'font_size')


    overlay_data : BoolProperty(name='Overlay Data', default=True)
    overlay_selection : BoolProperty(name='Only Selection', default=False)
    font_size : IntProperty(name='Font Size', default=13)