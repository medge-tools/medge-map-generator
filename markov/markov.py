import blf
from bpy.types import Object
from mathutils import Vector

import numpy as np

from ..dataset.dataset  import Attribute, Dataset, DatasetOps
from ..dataset.movement import State
from ..dataset.props    import get_dataset
from .offset            import OffsetNode, extract_seqs_per_state


# -----------------------------------------------------------------------------
compass = [Vector(( 1,  0, 0)), Vector((-1,  0, 0)), Vector(( 0,  1, 0)), Vector(( 0, -1, 0))]

class MarkovChain:

    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.offset_matrix = None

        self.dataset = None
        self.nstates = 0

        self.statistics = []


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, objects: list[Object], name = ''):
        self.reset()
        self.name = name

        D = Dataset()
        N = 0

        for obj in objects:
            if not obj.visible_get(): continue
            if not get_dataset(obj): continue

            d = DatasetOps.get_dataset(obj)
            D = Dataset.extend(D, d)


        if len(D) == 0: return

        N = max(D[:, Attribute.PLAYER_STATE.value]) + 1
        TM = np.zeros((N, N), dtype=float)                                  # Transition matrix
        OM = [[OffsetNode(branches=compass) for _ in range(N)] for _ in range(N)]    # Offset matrix

        # Populate matrices
        transitions = zip(D, D[1:])

        for (entry1, entry2) in transitions:
            if not entry1[Attribute.CONNECTED]: continue

            start = entry1[Attribute.LOCATION]
            end = entry2[Attribute.LOCATION]
            offset = end - start
            
            # Update matrices
            i = entry1[Attribute.PLAYER_STATE]
            j = entry2[Attribute.PLAYER_STATE]

            TM[i][j] += 1.0
            OM[i][j].insert(offset.normalized())


        # Extract sequences and calculate 'same branch' probability
        sequences = extract_seqs_per_state(D)
        for k, v in sequences.items():
            OM[k][k].insert_seqs(v)


        # Normalize 
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]

        for entry1 in range(N):
            for entry2 in range(N):
                OM[entry1][entry2].normalize()

        # Store matrices
        self.nstates = N
        self.transition_matrix = TM
        self.offset_matrix = OM
        self.dataset = D


    def generate_chain(self, length: int, seed: int, spacing: float):
        np.random.seed(seed)
        
        dataset = Dataset()
        dataset = Dataset.append(dataset, State.Walking.value, Vector())

        prev_state = 1
        prev_location = Vector()

        for _ in range(length):
            probabilities = self.transition_matrix[prev_state]

            next_state = np.random.choice(self.nstates, p=probabilities)

            offset_tree = self.offset_matrix[prev_state][next_state]
            new_offset = offset_tree.random_offset()

            next_location = prev_location + new_offset * spacing

            dataset = Dataset.append(dataset, State(next_state).value, next_location,)
            
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

