from bpy.types          import Object
import bmesh

import numpy as np

from ..dataset.logdata  import LogDataOps
from ..                 import b3d_utils


# -----------------------------------------------------------------------------
class MarkovChain:

    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.transition_matrix = None
        self.timestamps = []
        self.states = []
        self.locations = []


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object]):
        self.reset()
        
        bm = bmesh.new()

        for obj in objects:
            b3d_utils.set_object_mode(obj, 'OBJECT')
            bm.from_mesh(obj.data)

            t, s, l = LogDataOps.get_data(bm)

            self.timestamps.extend(t)
            self.states.extend(s)
            self.locations.extend(l)

            bm.free()

        n = max(self.states) + 1

        M = np.zeros((n, n), dtype=float)

        for (i,j) in zip(self.states, self.states[1:]):
            M[i][j] += 1

        for row in M:
            s = sum(row)
            if s > 0:
                row[:] = [f/s for f in row]

        self.transition_matrix = M


    def generate_chain(self, length: int):
        state = np.zeros(max(self.states) + 1)
