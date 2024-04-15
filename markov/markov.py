from bpy.types import Object

import numpy as np

from ..dataset.dataset  import Attribute, Dataset
from ..dataset          import dataset
from ..dataset.movement import PlayerState
from .chains            import Chain, ChainPool, GeneratedChain, GenChainSettings
from .bounds            import Hit


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
    def create_transition_matrix(self, _objects:list[Object], _min_chain_length=1, _name='') -> bool:
        self.reset()
        self.name = _name

        D = Dataset()
        N = 0

        for obj in _objects:
            if not obj.visible_get(): continue
            if not dataset.is_dataset(obj): continue

            d = dataset.get_dataset(obj)
            D.extend(d)


        if len(D) == 0: return False

        N = max(D[:, Attribute.PLAYER_STATE.value]) + 1
        TM = np.zeros((N, N), dtype=float)
        CP = [ChainPool() for _ in range(N)]

        # Populate ChainPools
        sps = D.seqs_per_state()
        for state, seqs in sps.items():
            for s in seqs:
                if len(s) < _min_chain_length: continue
                CP[state].append(state, s)

        # Populate transition matrix
        transitions = zip(D, D[1:])
        for (entry1, entry2) in transitions:
            if not entry1[Attribute.CONNECTED]: continue

            i = entry1[Attribute.PLAYER_STATE]
            j = entry2[Attribute.PLAYER_STATE]

            if len(CP[i]) == 0 or len(CP[j]) == 0:
                continue

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
        # Update properties
        for cp in self.chain_pools:
            for c in cp:
                c.radius = _settings.collision_radius
                c.aabb.margin = _settings.aabb_margin

        # Prepare chain generation
        np.random.seed(_settings.seed)

        start_state = PlayerState.Walking.value
        
        prev_state = start_state
        prev_chain = self.chain_pools[start_state].random_chain()
        
        gen_chain = GeneratedChain(None, _settings)
        gen_chain.append(prev_chain)
        
        for k in range(_settings.length):
            print(f'--- Iteration: {k} ---')

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

        # Create Polyline from LiveChain
        name = f'{self.name}_{_settings.length}_{_settings.seed}_{_settings.collision_radius}'
        gen_chain.to_polyline(name)
        return gen_chain

        
    def update_statistics(self, _from_state:int, _to_state:int):
        data = np.zeros((0, 2), dtype=str)

        t = self.transition_matrix[_from_state][_to_state]

        header = [[PlayerState(_from_state).name + ' -> ' + PlayerState(_to_state).name, str(round(t, 3))]]

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

