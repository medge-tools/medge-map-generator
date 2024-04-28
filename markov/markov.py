from bpy.types import Object

import numpy as np

from ..dataset.dataset  import Attribute, Dataset, is_dataset, dataset_entries
from ..dataset.movement import State
from .chains            import ChainPool, GeneratedChain, GenChainSettings


# -----------------------------------------------------------------------------
class MarkovChain:
    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.chain_pools = None

        self.dataset = None
        self.nstates = 0

        self.statistics = []


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, _objects:list[Object], _name='') -> bool:
        self.reset()
        self.name = _name

        D = Dataset()
        N = 0

        for obj in _objects:
            if not obj.visible_get(): continue
            if not is_dataset(obj): continue

            for entry in dataset_entries(obj):
                D.append(entry)


        if len(D) == 0: return False

        N = max(D[:, Attribute.STATE.value]) + 1
        TM = np.zeros((N, N), dtype=float)
        CP = [ChainPool() for _ in range(N)]

        # Populate ChainPools
        sps = D.seqs_per_state()
        for state, seqs in sps.items():
            for s in seqs:
                CP[state].append(state, s)

        # Populate transition matrix
        transitions = zip(D, D[1:])
        for (entry1, entry2) in transitions:
            if not entry1[Attribute.CONNECTED.value]: continue

            i = entry1[Attribute.STATE.value]
            j = entry2[Attribute.STATE.value]

            TM[i][j] += 1.0

        # Normalize 
        for row in TM:
            s = sum(row)
            if s > 0: 
                factor = 1.0/s
                row[:] = [float(v) * factor for v in row]

        # Finalize
        self.nstates = N
        self.transition_matrix = TM
        self.chain_pools = CP
        self.dataset = D

        return True


    def generate_chain(self, _settings:GenChainSettings) -> GeneratedChain:
        # Scale the chain to combat floating point errors when calculating collisions
        scale = 1000000

        # Scale and update properties
        for cp in self.chain_pools:
            for chain in cp:
                chain.height = _settings.collision_height * scale
                chain.radius = _settings.collision_radius * scale
                chain.resize(scale)

        # Prepare chain generation
        np.random.seed(_settings.seed)

        start_state = State.Walking.value
        
        prev_state = start_state
        prev_chain = self.chain_pools[start_state].random_chain()
        
        gen_chain = GeneratedChain(None, _settings)
        gen_chain.append(prev_chain)
        
        for k in range(len(gen_chain), _settings.length, 1):
            print(f'---Iteration: {k}------------------------------------------------------------')

            # Choose the next state
            probabilities = self.transition_matrix[prev_state]
            next_state = np.random.choice(self.nstates, p=probabilities)

            # Choose random chain
            cl = self.chain_pools[next_state]
            next_chain = cl.random_chain()

            # Align the new chain to the generated chain
            next_chain.align(gen_chain, _settings.align_orientation)
            gen_chain.append(next_chain)

            # Resolve any collisions
            gen_chain.resolve_collisions()

            # Prepare for next iteration
            prev_state = next_state
            prev_chain = next_chain

        # Scale the chain back to original size
        invscale = 1 / scale

        for chain in gen_chain:
            chain.resize(invscale)

        # Create Polyline from LiveChain
        name = f'{self.name}_{_settings}'
        gen_chain.to_polyline(name)

        return gen_chain

        
    def update_statistics(self, _from_state:int, _to_state:int):
        data = np.zeros((0, 2), dtype=str)

        t = self.transition_matrix[_from_state][_to_state]

        header = [[State(_from_state).name + ' -> ' + State(_to_state).name, str(round(t, 3))]]

        data = np.append(data, header, axis=0)

        info = [['Transition', 'Probability']]
        data = np.append(data, info, axis=0)

        # Pretty printing
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

        # Finalize
        seperator = [['-' * max_width[0], '-' * max_width[1]]]
        data = np.insert(data, 1, seperator, axis=0)
        
        self.statistics = data
