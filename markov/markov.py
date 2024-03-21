import blf
from bpy.types import Object
from mathutils import Vector

import numpy as np

from ..dataset.dataset  import Attribute, Dataset, DatasetOps
from ..dataset.movement import State
from ..dataset.props    import get_dataset
from .chains            import ChainList


# -----------------------------------------------------------------------------
class MarkovChain:

    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.chain_lists = None

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
            D.extend(d)


        if len(D) == 0: return

        N = max(D[:, Attribute.PLAYER_STATE.value]) + 1
        TM = np.zeros((N, N), dtype=float)
        CM = [ChainList() for _ in range(N)]

        # Populate transition matrix
        transitions = zip(D, D[1:])

        for (entry1, entry2) in transitions:
            if not entry1[Attribute.CONNECTED]: continue

            i = entry1[Attribute.PLAYER_STATE]
            j = entry2[Attribute.PLAYER_STATE]

            TM[i][j] += 1.0


        # Populate ChainLists
        sequences = D.seqs_per_state()
        for k, v in sequences.items():
            CM[k].append(v)


        # Normalize 
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]


        # Store matrices
        self.nstates = N
        self.transition_matrix = TM
        self.chain_lists = CM
        self.dataset = D


    def generate_chain(self, length: int, seed: int, spacing: float):
        np.random.seed(seed)
        start_state = State.Walking.value
        
        prev_state = start_state
        prev_chain = self.chain_lists[start_state].random_chain()
        
        dataset = Dataset()

        for p in prev_chain:
            dataset.append(start_state, p)

        for _ in range(length):
            probabilities = self.transition_matrix[prev_state]
            next_state = np.random.choice(self.nstates, p=probabilities)

            cl = self.chain_lists[next_state]
            next_chain = cl.random_chain()
            next_chain.align(prev_chain)

            for p in next_chain:
                dataset.append(State(next_state).value, p)
            
            prev_state = next_state
            prev_chain = next_chain

        name = self.name + '_' + str(length) + '_' + str(seed)
        DatasetOps.create_polyline(dataset, name)


    def update_statistics(self, from_state: int, to_state: int):
        data = np.zeros((0, 2), dtype=str)

        t = self.transition_matrix[from_state][to_state]
        off = self.chain_lists[from_state][to_state]

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

