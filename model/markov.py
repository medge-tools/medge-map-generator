from bpy.types          import Object
from mathutils          import Vector
import bmesh

import numpy as np
from math import degrees
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
        self.connected = []
        self.nstates = 0
        self.same_direction_2d = 0


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object]):
        self.reset()

        for obj in objects:

            t, s, l, c = DatasetOps.get_data(obj)

            self.timestamps.extend(t)
            self.states.extend(s)
            self.locations.extend(l)
            self.connected.extend(c)

        n = max(self.states) + 1
                                            # Probabilities:
        TM = np.zeros((n, n), dtype=float)  # Transition matrix
        OM = [[Offset()]*n]*n               # Offset matrix
        SD = 0                              # Change axis

        # Populate transition matrix
        transitions = zip(self.states, self.states[1:])
        prev_offset = None

        for k, (i,j) in enumerate(transitions):
            if not self.connected[k]: continue

            start = self.locations[k]
            end = self.locations[k + 1]
            offset = end - start

            # Update matrices
            TM[i][j] += 1.0
            OM[i][j].add(offset)
            
            if i == 21 and j == 21:
                print(k)
                for x in OM[21][21]:
                    print(str(x))
                print()

            # Calculate change of axis
            offset = Vector((offset.x, offset.y, 0))
            if not prev_offset:
                prev_offset = offset

            if offset.length != 0 and prev_offset.length != 0:
                radians = prev_offset.angle(offset)
                if degrees(radians) < 90:
                    SD += 1

            prev_offset = offset

            
        # Normalize 
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]

        for i in range(n):
            for j in range(n):
                OM[i][j].normalize()

        SD /= k



        # with open('transition_matrix.txt', 'w') as f:
        #     for row in TM:
        #         for k in row:
        #             f.write(str(k) + ',')
        #         f.write('\n')

        # Store matrices
        self.transition_matrix = TM
        self.offset_matrix = OM
        self.nstates = n
        self.same_direction_2d = SD


    def generate_chain(self, length: int, seed: int, spacing: float):

        np.random.seed(seed)
        
        probabilities = np.zeros(self.nstates)
        probabilities[movement.State.Walking] = 1.0

        dataset = Dataset()
        dataset.append(movement.State.Walking, Vector())

        prev_offset = None
        same_direction_2d = False

        for _ in range(length):
            probabilities = probabilities @ self.transition_matrix

            last = len(dataset) - 1
            prev_state = dataset[last][Attributes.PLAYER_STATE]
            prev_loc   = dataset[last][Attributes.LOCATION]

            next_state = np.random.choice(self.nstates, p=probabilities)

            # same_direction_2d = np.random.rand() <= self.same_direction_2d

            offset_dict = self.offset_matrix[prev_state][next_state]
            offset_probs = list(offset_dict.values())
            search_offset = True

            while search_offset:
                offset_idx = np.random.choice(len(offset_dict), p=offset_probs)
                if prev_state == 21 and next_state == 21:
                    for x in list(offset_dict):
                        print(str(x) + '\n')
                    print()
                new_offset = list(offset_dict)[offset_idx]
                search_offset = False
                
                if not prev_offset: break

                radians = prev_offset.angle(new_offset)
                if degrees(radians) > 135: # Prevent going back
                    search_offset = True

                # if same_direction_2d:
                #     po2d = Vector((prev_offset.x, prev_offset.y, 0))
                #     no2d = Vector((new_offset.x, new_offset.y, 0))

                #     if po2d.length != 0 and no2d.length != 0:
                #         radians = po2d.angle(no2d)
                #         if degrees(radians) > 45: 
                #             search_offset = True

            player_state = movement.State(next_state)
            location = prev_loc + new_offset * spacing

            dataset.append(player_state, location,)
            
            prev_offset = new_offset
            probabilities = np.zeros(self.nstates)
            probabilities[player_state] = 1.0

        DatasetOps.create_polyline(dataset)
