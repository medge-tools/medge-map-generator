import blf
from bpy.types import Object
from mathutils import Vector

import numpy as np

from ..dataset.dataset  import Dataset, DatasetOps
from ..dataset.movement import State
from ..dataset.props    import get_dataset
from .offset        import OffsetDoubleLevelTree

# -----------------------------------------------------------------------------
class MarkovChain:

    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.offset_matrix = None

        self.timestamps = []
        self.states = []
        self.locations = []
        self.connected = []
        self.nstates = 0

        self.statistics = []


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object], name = ''):
        self.reset()

        self.name = name

        for obj in objects:
            if not obj.visible_get(): continue
            if not get_dataset(obj): continue

            s, l, t, c = DatasetOps.get_data(obj)

            self.timestamps.extend(t)
            self.states.extend(s)
            self.locations.extend(l)
            self.connected.extend(c)

        n = max(self.states) + 1
        TM = np.zeros((n, n), dtype=float)                                      # Transition matrix
        OM = [[OffsetDoubleLevelTree() for _ in range(n)] for _ in range(n)]    # Offset matrix

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
        self.nstates = n
        self.transition_matrix = TM
        self.offset_matrix = OM


    def generate_chain(self, length: int, seed: int, spacing: float):
        np.random.seed(seed)
        
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

        name = self.name + '_' + str(length) + '_' + str(seed)
        DatasetOps.create_polyline(dataset, name)


    def update_statistics(self, from_state: int, to_state: int):
        data = np.zeros((0, 2), dtype=str)

        t = self.transition_matrix[from_state][to_state]
        off = self.offset_matrix[from_state][to_state]

        header = [[State(from_state).name + ' -> ' + State(to_state).name, str(round(t, 3))]]

        data = np.append(data, header, axis=0)
        data = np.append(data, off.statistics(), axis=0)

        info = [['(Key)', '(Probability)']]
        data = np.append(data, info, axis=0)

        rows, cols = data.shape
        max_width = [0] * cols
        for k in range(cols):
            w = len(max(data[:, k], key=len))
            max_width[k] = w
        
        fill = ' '
        align = '<'
        for k in range(cols):
            width = max_width[k]
            a = data[:, k]
            for j in range(rows):
                a[j] = f'{a[j]:{fill}{align}{width}}'

        seperator = [['-' * max_width[0], '-' * max_width[1]]]
        data = np.insert(data, -1, seperator, axis=0)
        data = np.insert(data, 1, seperator, axis=0)
        
        self.statistics = data

