from bpy.types          import Object
from mathutils          import Vector
import bmesh

import numpy as np
from collections.abc import MutableMapping

from ..                 import b3d_utils
from ..dataset.dataset  import Attributes, Dataset, DatasetOps
from ..dataset          import movement


# -----------------------------------------------------------------------------
class Offset(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys


    def __getitem__(self, key):
        return self.store[self._keytransform(key)]


    def __setitem__(self, key, value):
        self.store[self._keytransform(key)] = value


    def __delitem__(self, key):
        del self.store[self._keytransform(key)]


    def __iter__(self):
        return iter(self.store)
    

    def __len__(self):
        return len(self.store)


    def _keytransform(self, key):
        return key


    def add(self, offset: Vector, min_dot: float = .75):
        offset.normalize()
        curr_dot = -1
        key = None

        for k in self.store.keys():
            dot = offset.dot(k)
            if dot > curr_dot and dot >= min_dot:
                curr_dot = dot
                key = k
        
        if key != None:
            self.store[key] += 1
        else:
            self.store.setdefault(offset.freeze(), 1)

        
    def normalize(self):
        factor = 1.0 / sum(self.store.values())
        for k, v in self.store.items():
            self.store[k] = v * factor


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


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object]):
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
        

        # Populate transition matrix
        transitions = zip(self.states, self.states[1:])
        
        for k, (i,j) in enumerate(transitions):
            start = self.locations[k]
            end = self.locations[k + 1]
            offset = end - start

            TM[i][j] += 1.0
            OM[i][j].add(offset)

            
        # Normalize matrices
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]

        for i in range(n):
            for j in range(n):
                OM[i][j].normalize()
        
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

            offset_dict = self.offset_matrix[prev_state][next_state]
            offset_probs = list(offset_dict.values())
            offset_idx = np.random.choice(range(len(offset_dict)), p=offset_probs)
            offset = list(offset_dict)[offset_idx]

            player_state = movement.State(next_state)
            location = prev_loc + offset

            dataset.append(player_state,
                           location,
                           )

        DatasetOps.create_polyline(dataset)
