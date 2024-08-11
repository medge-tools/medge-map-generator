import bpy
from bpy.types import Context, Collection, Operator, Panel
from mathutils import Vector

from math        import pi

from .gui        import MEdgeToolsPanel, ExportTab
from ..          import b3d_utils
from ..b3d_utils import get_active_collection
from .map        import get_medge_map_gen_settings, MET_SCENE_PG_map_gen_settings

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_OT_prepare_for_export(Operator):
    bl_idname = 'medge_generate.prepare_for_export'
    bl_label = 'Prepare For Export'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        settings = get_medge_map_gen_settings(_context)
        self.prepare_for_export(settings, collection)

        return {'FINISHED'}
    

    def prepare_for_export(self, _settings:MET_SCENE_PG_map_gen_settings, _collection:Collection):
        new_collection = b3d_utils.new_collection('PrepareForExport', _collection)

        # Add player start
        bpy.ops.medge_map_editor.add_actor(type='PLAYER_START')
        ps = bpy.context.object

        b3d_utils.link_object_to_scene(ps, new_collection)
        
        ps.location = Vector((0, 0, 0))

        # Add directional light
        bpy.ops.object.light_add(type='SUN', align='WORLD', location=(0, 0, 3), scale=(1, 1, 1))
        light = bpy.context.object

        b3d_utils.link_object_to_scene(light, new_collection)

        # Add killvolume
        scale = 500

        bpy.ops.medge_map_editor.add_actor(type='KILL_VOLUME')
        kv = bpy.context.object

        b3d_utils.link_object_to_scene(kv, new_collection)

        kv.location = 0, 0, -50
        kv.scale = scale, scale, 10

        # Add skydome top
        scale = 7000
        bpy.ops.medge_map_editor.add_skydome()
        sd = bpy.context.object

        b3d_utils.link_object_to_scene(sd, new_collection)

        sd.location = 0, 0, 0
        sd.scale = scale, scale, scale

        if _settings.skydome:
            sd.medge_actor.static_mesh.use_prefab = True
            sd.medge_actor.static_mesh.prefab = _settings.skydome

        if _settings.only_top: return

        # Add skydome bottom
        bpy.ops.medge_map_editor.add_skydome()
        sd = bpy.context.object
        b3d_utils.link_object_to_scene(sd, new_collection)

        sd.location = (0, 0, 0)
        sd.scale = (scale, scale, scale)
        sd.rotation_euler.x = pi
            
        if _settings.skydome:
            sd.medge_actor.static_mesh.use_prefab = True
            sd.medge_actor.static_mesh.prefab = _settings.skydome


# -----------------------------------------------------------------------------
class MET_OT_export_t3d(Operator):
    bl_idname = 'medge_generate.export_t3d'
    bl_label = 'Export T3D'
    bl_options = {'UNDO'}


    def execute(self, _context:Context):
        collection = get_active_collection()
        self.export(collection)

        return {'FINISHED'}
    

    def export(self, _collection:Collection):
        b3d_utils.deselect_all_objects()

        for obj in _collection.all_objects:
            if obj.type != 'LIGHT':
                if obj.medge_actor.type == 'NONE': continue
            
            b3d_utils.select_object(obj)

        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        
        bpy.ops.medge_map_editor.t3d_export('INVOKE_DEFAULT', selected_collection=True)

        bpy.ops.ed.undo()


# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_export_map(MEdgeToolsPanel, ExportTab, Panel):
    bl_label = 'Export'


    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Select Collection')

        settings = get_medge_map_gen_settings(_context)

        col.separator()
        col.prop(settings, 'skydome')
        col.prop(settings, 'only_top')
        col.separator()
        col.operator(MET_OT_prepare_for_export.bl_idname)
        col.operator(MET_OT_export_t3d.bl_idname)