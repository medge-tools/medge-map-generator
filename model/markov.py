from bpy.types          import Object
from mathutils          import Vector

import numpy as np
from collections.abc import MutableMapping

from ..dataset.dataset  import Attributes, Dataset, DatasetOps
from ..dataset.movement import State
from ..dataset.props    import is_dataset

# -----------------------------------------------------------------------------
class Offset(MutableMapping):
    def __init__(self) -> None:
        self.store = dict()


    def __getitem__(self, key):
        return self.store[key]


    def __setitem__(self, key, value):
        self.store[key] = value


    def __delitem__(self, key):
        del self.store[key]


    def __iter__(self):
        return iter(self.store)
    

    def __len__(self):
        return len(self.store)


    def add(self, offset: Vector):
        if offset.length == 0: return

        offset.normalize()

        for vec in self.store.keys():
            if offset == vec:
                self.store[vec] += 1
                return

        self.store.setdefault(offset.freeze(), 1)

        
    def normalize(self):
        if (s := sum(self.store.values())) > 0:
            factor = 1.0 / s
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
        self.connected = []
        self.nstates = 0


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object]):
        self.reset()

        for obj in objects:
            if not obj.visible_get(): continue
            if not is_dataset(obj): continue

            s, l, t, c = DatasetOps.get_data(obj)

            self.timestamps.extend(t)
            self.states.extend(s)
            self.locations.extend(l)
            self.connected.extend(c)

        n = max(self.states) + 1
                                                                # Probabilities:
        TM = np.zeros((n, n), dtype=float)                      # Transition matrix
        OM = [[Offset() for _ in range(n)] for _ in range(n)]   # Offset matrix

        # Populate matrices
        transitions = zip(self.states, self.states[1:])

        for k, (i,j) in enumerate(transitions):
            if not self.connected[k]: continue

            start = self.locations[k]
            end = self.locations[k + 1]
            offset = end - start

            # Update matrices
            TM[i][j] += 1.0
            OM[i][j].add(offset)
                


        
        # Normalize 
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]

        for i in range(n):
            for j in range(n):
                OM[i][j].normalize()

        with open('transition_matrix.txt', 'w') as f:
            for row in TM:
                for v in row:
                    f.write(str(v) + ',')
                f.write('\n')

        # Store matrices
        self.transition_matrix = TM
        self.offset_matrix = OM
        self.nstates = n


    def generate_chain(self, length: int, seed: int, spacing: float):

        np.random.seed(seed)
        
        probabilities = np.zeros(self.nstates)
        probabilities[State.Walking] = 1.0

        dataset = Dataset()
        dataset.append(State.Walking, Vector())

        prev_state = 1
        prev_location = Vector()

        for _ in range(length):
            probabilities = self.transition_matrix[prev_state]

            next_state = np.random.choice(self.nstates, p=probabilities)

            offset_dict = self.offset_matrix[prev_state][next_state]
            offset_probs = list(offset_dict.values())

            if len(offset_dict) == 0:
                for k, p in enumerate(probabilities):
                    print('('+ str(k) + ' - ' + str(p) + '), ')

            offset_idx = np.random.choice(len(offset_dict), p=offset_probs)
            new_offset = list(offset_dict)[offset_idx]

            next_location = prev_location + new_offset * spacing

            dataset.append(State(next_state), next_location,)
            
            prev_state = next_state
            prev_location = next_location

        DatasetOps.create_polyline(dataset)
