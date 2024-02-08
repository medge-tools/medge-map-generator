from bpy.types      import PropertyGroup, UILayout
from bpy.props      import *
from .dataset       import *


# -----------------------------------------------------------------------------
class MET_DS_PG_VisSettings(PropertyGroup):
    def draw(self, layout: UILayout):
        layout.prop(self, 'overlay_data')
        if self.overlay_data:
            layout.prop(self, 'only_selection')
            layout.prop(self, 'show_timestamps')
            layout.prop(self, 'font_size')

    overlay_data : BoolProperty(name='Overlay Data', default=True)
    only_selection : BoolProperty(name='Only Selection', default=False)
    show_timestamps : BoolProperty(name='Show Timestamps', default=False)

    font_size : IntProperty(name='Font Size', default=13)


# -----------------------------------------------------------------------------
class MET_MESH_PG_Dataset(PropertyGroup):
    vis_settings : PointerProperty(type=MET_DS_PG_VisSettings)