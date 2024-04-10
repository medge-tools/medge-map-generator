from bpy.types import Object

import copy
import numpy as np
from sys import float_info

from ..dataset.dataset  import Attribute, Dataset
from ..dataset          import dataset
from ..dataset.movement import PlayerState
from .chains            import ChainPool, GeneratedChain, Chain
from .bounds            import Hit


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
    def create_transition_matrix(self, objects: list[Object], _min_chain_length = 1, name = '') -> bool:
        self.reset()
        self.name = name

        D = Dataset()
        N = 0

        for obj in objects:
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

        # Store matrices
        self.nstates = N
        self.transition_matrix = TM
        self.chain_lists = CP
        self.dataset = D

        return True


    def generate_chain(self, length: int, seed: int) -> tuple[GeneratedChain, Object]:
        np.random.seed(seed)

        start_state = PlayerState.Walking.value
        
        prev_state = start_state
        prev_chain = self.chain_lists[start_state].random_chain()
        
        gen_chain = GeneratedChain()
        gen_chain.append(prev_chain)


        def collides(other: Chain) -> Hit | bool:
            for chain in gen_chain.sections:
                if (hit := other.collides(chain)): return hit
            return False

        
        def resolve_collisions(chain):
            # Store the penetration depth with the respective rotation
            smallest_pen_depth = float_info.max
            best_rotation = 0
            for r in range(145):
                # Rotate right
                temp = copy.deepcopy(chain)
                temp.align(gen_chain, _rotation_offset=r)
                hit = collides(temp)
                if not (hit): 
                    print(f'Resolved collision with rotation: {r}')
                    chain.align(gen_chain, _rotation_offset=r)
                    return
                
                if (l := hit.length) < smallest_pen_depth:
                    smallest_pen_depth = l
                    best_rotation = r
                
                # Rotate left
                rl = -r
                temp = copy.deepcopy(chain)
                temp.align(gen_chain, _rotation_offset=rl)
                hit = collides(temp)
                if not (hit): 
                    print(f'Resolved collision with rotation: {rl}')
                    chain.align(gen_chain, _rotation_offset=rl)
                    return
                
                if (l := hit.length) < smallest_pen_depth:
                    smallest_pen_depth = l
                    best_rotation = rl

            # No rotation found without collisions
            # Pick the rotation with the smallest penetration depth
            print(f'Could not resolve collision, best rotation: {best_rotation}')
            chain.align(gen_chain, best_rotation)


        for k in range(length):
            print(f'=== Iteration: {k} ===')
            if k == 65:
                print(k)
            # Choose the next state
            probabilities = self.transition_matrix[prev_state]
            next_state = np.random.choice(self.nstates, p=probabilities)

            # Choose random chain
            cl = self.chain_lists[next_state]
            next_chain = cl.random_chain()
            
            # Align the new chain to the current chain
            next_chain.align(gen_chain)

            # Resolve collisions
            if collides(next_chain):
                resolve_collisions(next_chain)

            gen_chain.append(next_chain)
            prev_state = next_state
            prev_chain = next_chain

        # Create Polyline from LiveChain
        name = self.name + '_' + str(length) + '_' + str(seed)
        gen_chain.to_polyline(name)
        return gen_chain


    def update_statistics(self, from_state: int, to_state: int):
        data = np.zeros((0, 2), dtype=str)

        t = self.transition_matrix[from_state][to_state]
        off = self.chain_lists[from_state][to_state]

        header = [[PlayerState(from_state).name + ' -> ' + PlayerState(to_state).name, str(round(t, 3))]]

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

