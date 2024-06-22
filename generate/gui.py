from bpy.types import Context, Panel

from ..             import b3d_utils
from ..gui_defaults import MapGenPanel_DefaultProps

from .ops   import (MET_OT_CreateTransitionMatrix, MET_OT_GenerateChain, MET_OT_AddHandmadeChain,
                    MET_OT_InitModules, MET_OT_AddCurveModuleToGroup, MET_OT_AddCollisionVolume, MET_OT_RemoveCollisionVolume,
                    MET_OT_GenerateMap, MET_OT_PrepareForExport, MET_OT_ExportT3D)
from .props import get_markov_chains_prop, get_curve_module_groups_prop, get_curve_module_prop



# -----------------------------------------------------------------------------
# Curve Module
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_CurveModule(MapGenPanel_DefaultProps, Panel):
    bl_idname = 'MET_PT_CurveModule'
    bl_label = 'Map Gen: Curve Module'


    @classmethod
    def poll(cls, _context:Context):
        obj = _context.object
        return obj and obj.type == 'CURVE'


    def draw(self, _context:Context):
        obj = _context.object

        if not obj: return

        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        b3d_utils.draw_box(col, 'Use the curve as parent for any level component')
        col.separator()

        row = col.row(align=True)

        cm = get_curve_module_prop(obj)
        row.prop(cm, 'collision_volume')
        row.operator(MET_OT_AddCollisionVolume.bl_idname, text='', icon='ADD')
        row.operator(MET_OT_RemoveCollisionVolume.bl_idname, text='', icon='X')


# -----------------------------------------------------------------------------
# Generate
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_GenerateMain(MapGenPanel_DefaultProps, Panel):
    bl_idname = 'MET_PT_GenerateMain'
    bl_label = 'Map Gen: Generate'


    def draw(self, _context:Context):
        pass


# -----------------------------------------------------------------------------
# Markov Chains
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_MarkovChains(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_GenerateMain.bl_idname
    bl_label = 'Markov Chains'
    

    def draw(self, _context:Context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        
        col = layout.column(align=True)

        markov_chains = get_markov_chains_prop(_context)

        # ---------------------------------------------------------------------
        col.label(text='Dataset Collections')
        col.separator()
        b3d_utils.draw_generic_list(col, markov_chains, '#markov_chain_list')

        mc = markov_chains.get_selected()

        if not mc: return

        col = layout.column(align=True)
        col.prop(mc, 'collection')

        col.separator(factor=2)

        col.operator(MET_OT_CreateTransitionMatrix.bl_idname, text=MET_OT_CreateTransitionMatrix.bl_label)

        col.separator(factor=2)
        if mc.has_transition_matrix():
            col.prop(mc, 'length')
            col.prop(mc, 'seed')

            col.separator()
            col.operator(MET_OT_GenerateChain.bl_idname)

        gen_chains = mc.generated_chains

        
        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Generated Chains')
        col.separator()
        b3d_utils.draw_generic_list(col, gen_chains, '#generated_chain_list', 3, {'REMOVE', 'MOVE', 'CLEAR'})

        col.separator()
        row = col.row(align=True)
        row.prop(mc, 'handmade_chain')
        row.operator(MET_OT_AddHandmadeChain.bl_idname, text='', icon='ADD')

        active_chain = gen_chains.get_selected()

        if not active_chain: return

        col.separator()
        col.prop(mc, 'show_chain', expand=True)

        if mc.show_chain:
            col.separator(factor=2)
            b3d_utils.multiline_text(_context, col, active_chain.chain)
            col.separator(factor=2)


# -----------------------------------------------------------------------------
# Map Generation
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
class MET_PT_MapGeneration(MapGenPanel_DefaultProps, Panel):
    bl_parent_id = MET_PT_GenerateMain.bl_idname
    bl_label = 'Map Generation'


    def draw(self, _context:Context):
        markov_chains = get_markov_chains_prop(_context)
        active_mc = markov_chains.get_selected()

        if not active_mc: return

        gen_chains = active_mc.generated_chains
        active_chain = gen_chains.get_selected()

        if not active_chain: return
        
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True

        col = layout.column(align=True)

        col.label(text='Module Groups')
        col.separator()

        module_groups = get_curve_module_groups_prop(_context)
        
        row = col.row(align=True)
        row.template_list('MET_UL_CurveModuleGroupList', '#modules', module_groups, 'items', module_groups, 'selected_item_idx', rows=3)
        
        col.separator()
        col.operator(MET_OT_InitModules.bl_idname)
        col.operator(MET_OT_AddCurveModuleToGroup.bl_idname)

        if len(module_groups.items) == 0: return

        col.separator(factor=2)

        mg = module_groups.get_selected()

        col.prop(mg, 'use_collection')
        col.separator()

        if mg.use_collection:
            col.prop(mg, 'collection')
        else:
            col.prop(mg, 'module')

        # ---------------------------------------------------------------------
        col.separator(factor=2)
        col.label(text='Settings')
        col.separator()
                
        col.prop(module_groups, 'seed')
        col.prop(module_groups, 'align_orientation')
        col.prop(module_groups, 'resolve_volume_overlap')

        if module_groups.resolve_volume_overlap:
            col.prop(module_groups, 'max_depth')
            col.prop(module_groups, 'max_angle')
            col.prop(module_groups, 'angle_step')
            col.prop(module_groups, 'random_angles')

    
        col.separator()
        col.operator(MET_OT_GenerateMap.bl_idname)
        
        col.separator(factor=2)
        b3d_utils.draw_box(col, 'Select Generated Map Collection')

        col.separator()
        col.operator(MET_OT_PrepareForExport.bl_idname)
        col.operator(MET_OT_ExportT3D.bl_idname)