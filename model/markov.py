from bpy.types          import Object
from mathutils          import Vector

import numpy as np
from sys import float_info
from collections.abc import MutableMapping

from ..                 import b3d_utils
from ..dataset.dataset  import Dataset, DatasetOps
from ..dataset.movement import State
from ..dataset.props    import is_dataset


# -----------------------------------------------------------------------------
class OffsetNode(MutableMapping):
    def __init__(self, parent = None) -> None:
        self.offsets = dict()
        self.children : list[OffsetNode] = []
        if parent:
            parent.children.append(self)

    #region 
    def __getitem__(self, key):
        return self.offsets[key]


    def __setitem__(self, key, value):
        self.offsets[key] = value


    def __delitem__(self, key):
        del self.offsets[key]


    def __iter__(self):
        return iter(self.offsets)
    

    def __len__(self):
        return len(self.offsets)
    #endregion

    def add_branch(self, offset: Vector):
        if offset.length == 0: return

        self.children.append(OffsetNode())
        self.offsets.setdefault(offset.freeze(), 0.0)


    def insert(self, offset: Vector):
        if self.children:
            min_angle = float_info.max
            idx = -1
            key = None

            for k, off in enumerate(self.offsets.keys()):
                if (a := offset.angle(off)) < min_angle:
                    min_angle = a
                    idx = k
                    key = off

            self.offsets[key] += 1.0
            self.children[idx].insert(offset)

        else:
            key = offset.freeze()
            if key in self.offsets:
                self.offsets[key] += 1.0
            else:
                self.offsets.setdefault(key, 1.0)

        
    def normalize(self):
        if (s := sum(self.offsets.values())) > 0:
            factor = 1.0 / s
            for k, v in self.offsets.items():
                self.offsets[k] = v * factor

        for child in self.children:
            child.normalize()


    def random_offset(self):
        n = len(self.offsets)
        k = np.random.choice(n, p=list(self.offsets.values()))

        if self.children:
            child = self.children[k]
            return child.random_offset()
        else:
            return list(self.offsets)[k]    

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


    def init_offset_hierarchy(self):
        root = OffsetNode()

        root.add_branch(Vector(( 1,  0, 0)))
        root.add_branch(Vector((-1,  0, 0)))
        root.add_branch(Vector(( 0,  1, 0)))
        root.add_branch(Vector(( 0, -1, 0)))

        return root
        

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
        TM = np.zeros((n, n), dtype=float)                                          # Transition matrix
        OM = [[self.init_offset_hierarchy() for _ in range(n)] for _ in range(n)]   # Offset matrix

        # Populate matrices
        transitions = zip(self.states, self.states[1:])

        for k, (i,j) in enumerate(transitions):
            if not self.connected[k]: continue

            start = self.locations[k]
            end = self.locations[k + 1]
            offset = end - start
            
            # Update matrices
            TM[i][j] += 1.0
            OM[i][j].insert(offset.normalized())
                
        # Normalize 
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

            offset_hierarchy = self.offset_matrix[prev_state][next_state]
            new_offset = offset_hierarchy.random_offset()

            next_location = prev_location + new_offset * spacing

            dataset.append(State(next_state), next_location,)
            
            prev_state = next_state
            prev_location = next_location

        DatasetOps.create_polyline(dataset)
