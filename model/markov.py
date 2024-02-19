from bpy.types          import Object
from mathutils          import Vector
import bmesh

import numpy as np
from enum   import IntEnum
from sys    import float_info

from ..                 import b3d_utils
from ..dataset.dataset  import Attributes, Dataset, DatasetOps
from ..dataset          import movement


# -----------------------------------------------------------------------------
class Direction(IntEnum):
    UP          = 0
    DOWN        = 1
    LEFT        = 2
    RIGHT       = 3
    FORWARD     = 4
    BACKWARD    = 5


# -----------------------------------------------------------------------------
direction_vectors = {
    Direction.UP        : Vector(( 0,  0,  1)),
    Direction.DOWN      : Vector(( 0,  0, -1)),
    Direction.LEFT      : Vector((-1,  0,  0)),
    Direction.RIGHT     : Vector(( 1,  0,  0)),
    Direction.FORWARD   : Vector(( 0,  1,  0)),
    Direction.BACKWARD  : Vector(( 0, -1,  0)),
}


# -----------------------------------------------------------------------------
class Offset(list):

    def __init__(self):
        super().__init__(range(len(Direction)))


    def append(self, offset: Vector) -> None:
        min_angle = float_info.max
        index = -1
        for k, v in direction_vectors.items():
            angle = offset.dot(v)
            if angle < min_angle:
                min_angle = angle
                index = k

        self[index] += 1


# -----------------------------------------------------------------------------
class MarkovChain:

    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.transition_matrix = None
        self.offset_matrix = None
        self.timestamps = []
        self.states = []
        self.locations = []
        self.nstates = 0


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object]):

        def normalize(l):
            s = sum(l)
            if s > 0: 
                factor = 1.0/s
                normalized = [float(k) * factor for k in l]
                x = len(np.argwhere(np.isnan(normalized)))
                assert x == 0
                return normalized
            return l
        

        self.reset()

        bm = bmesh.new()

        for obj in objects:
            b3d_utils.set_object_mode(obj, 'OBJECT')
            bm.from_mesh(obj.data)

            t, s, l = DatasetOps.get_data(bm)

            self.timestamps.extend(t)
            self.states.extend(s)
            self.locations.extend(l)

            bm.free()

        n = max(self.states) + 1

        TM = np.zeros((n, n), dtype=float)  # Transition matrix
        OM = [[Offset()]*n]*n               # Offset matrix

        # Populate matrices
        for (i,j) in zip(self.states, self.states[1:]):
            start = self.locations[i]
            end = self.locations[j]
            
            TM[i][j] += 1.0
            OM[i][j].append(end - start)

        # Normalize matrices
        for row in TM:
            row[:] = normalize(row)

        for row in OM:
            row[:] = [normalize(off) for off in row]
        
        # Store matrices
        self.transition_matrix = TM
        self.offset_matrix = OM


    def generate_chain(self, length: int, seed):
        
        np.random.seed(seed)
        n = max(self.states) + 1
        
        probabilities = np.zeros(n)
        probabilities[movement.State.Walking] = 1

        dataset = Dataset()

        dataset.append(movement.State.Walking, Vector((0, 0, 0)))

        for _ in range(length):
            probabilities = probabilities @ self.transition_matrix

            prev_state = dataset[len(dataset) - 1][Attributes.PLAYER_STATE]
            prev_loc = dataset[len(dataset) - 1][Attributes.LOCATION]

            next_state = np.random.choice(range(n), p=probabilities)

            offset_probs = self.offset_matrix[prev_state][next_state]
            offset_index = np.random.choice(range(len(Direction)), p=offset_probs)
            offset       = direction_vectors[offset_index]

            player_state = movement.State(next_state)
            location = prev_loc + offset

            dataset.append(player_state,
                           location,
                           )

        DatasetOps.create_polyline(dataset)
