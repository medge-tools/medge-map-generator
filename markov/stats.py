import bpy, blf, os
from bpy.types import Context, SpaceView3D

from .props         import get_markov_chains

# -----------------------------------------------------------------------------
draw_handle = None

class MarkovChainStats():
    def add_handle(self, context):
        dir = os.path.dirname(os.path.abspath(__file__))
        bpy.data.fonts.load(
            filepath = dir + '\\..\\fonts\\MartianMono-StdRg.otf', 
            check_existing = True)
        
        global draw_handle
        if draw_handle:
            self.remove_handle()
        draw_handle = SpaceView3D.draw_handler_add(
            self.draw_callback,(context,), 'WINDOW', 'POST_PIXEL')


    def remove_handle(self):
        global draw_handle
        if draw_handle:
            SpaceView3D.draw_handler_remove(draw_handle, 'WINDOW')
            draw_handle = None


    def draw_callback(self, context: Context):
        mc = get_markov_chains(context)

        item = mc.get_selected()
        
        if not item: return

        data = item.data()

        if not data: return

        stats = data.statistics

        font = 1
        size = 13
        blf.color(font, 1, 1, 1, 1)
        blf.size(font, size)

        r = 0
        padding = size + 7
        for row in reversed(stats):
            text = ''
            for val in row:
                text += val + '   '
            blf.position(font, 50, 50 + r * padding, 0)
            blf.draw(font, text)
            r += 1