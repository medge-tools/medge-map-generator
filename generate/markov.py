from bpy.types import Object

import numpy as np

from ..dataset.dataset  import is_dataset, dataset_sequences
from ..dataset.movement import State


# -----------------------------------------------------------------------------
class MarkovChain:
    def __init__(self) -> None:
        self.reset()


    def reset(self):
        self.name = ''
        self.transition_matrix = None
        self.nstates = 0


    # https://stackoverflow.com/questions/46657221/generating-markov-transition-matrix-in-python
    def create_transition_matrix(self, _objects:list[Object], _name='') -> bool:
        self.name = _name

        self.nstates = 0
        transitions:list[list] = []

        # Collect all states
        for obj in _objects:
            if not is_dataset(obj): continue

            states = []

            for state, _, _, _ in dataset_sequences(obj):
                self.nstates = max(self.nstates, state)
                states.append(state)

            transitions.append(states.copy())
            
        if len(transitions) == 0: return False

        self.nstates += 1
        self.transition_matrix = np.zeros((self.nstates, self.nstates), dtype=float)

        # Populate transition matrix
        # Instead of going through each vertex, we group 
        for sequence in transitions:
            for s1, s2 in zip(sequence, sequence[1:]):
                self.transition_matrix[s1][s2] += 1.0

        # Normalize 
        for row in self.transition_matrix:
            if (s := sum(row)) > 0: 
                factor = 1.0 / s
                row[:] = [float(v) * factor for v in row]

        return True


    def generate_chain(self, _length:int, _seed:int) -> list[int]:
        # Prepare chain generation
        np.random.seed(_seed)

        start_state = State.Walking.value
        prev_state = start_state

        gen_chain = [prev_state]
        
        for _ in range(1, _length, 1):
            # Choose the next state
            probabilities = self.transition_matrix[prev_state]
            next_state = np.random.choice(self.nstates, p=probabilities)

            gen_chain.append(next_state)

            # Prepare for next iteration
            prev_state = next_state

        return gen_chain
