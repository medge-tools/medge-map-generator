from mathutils import Vector

import numpy as np
from sys import float_info

from ..dataset.dataset import Attribute, Dataset

# -----------------------------------------------------------------------------
class OffsetNode():
    def __init__(self, parent = None, branches: list[Vector] = None):
        self.offsets = dict()
        self.children : list[OffsetNode] = []
        
        self.use_prev_branch = None
        self.prev_branch = None

        if parent:
            parent.children.append(self)

        if branches:
            for b in branches:
                self.add_branch(b)


    def add_branch(self, offset: Vector):
        self.offsets.setdefault(offset.freeze(), 0.0)
        self.children.append(OffsetNode())


    def closest_branch(self, offset: Vector):
        min_angle = float_info.max
        key = None
        child = -1

        for i, off in enumerate(self.offsets.keys()):
            if (a := offset.angle(off)) < min_angle:
                min_angle = a
                key = off
                child = i

        return key, child


    def insert(self, offset: Vector):
        if self.children:
            key, child = self.closest_branch(offset)

            self.offsets[key] += 1.0
            self.children[child].insert(offset)
        
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


    def statistics(self):
        data = np.zeros((0, 2), dtype=str)
        
        for k, v in self.offsets.items():
            key = str(k)
            val = str(round(v, 3))
            data = np.append(data, [[key, val]], axis=0)
        
        if self.use_prev_branch:
            key = 'Use Previous Branch '
            val = str(round(self.use_prev_branch, 3))
            data = np.append(data, [[key, val]], axis=0)

        return data


    # Find left and right non 0 probability neighbors of the previous branch
    def find_non_zero_neighbors(self) -> list[float]:
        n = len(self.offsets)

        if n < 3: return

        probs = list(self.offsets.values())

        # Init indices
        b = self.prev_branch
        bl = b - 1
        br = (b + 1) % n

        # Find non-zero probability neighbors of 'b'
        for k in range(2, n, 1):
            if (blp := probs[bl]) <= 0:
                if (bk := b - k) == br:
                    break
                bl = bk
            if (brp := probs[br]) <= 0:
                if (bk := b + k % n) == bl:
                    break
                br = (b + k) % n

        # Construct array of the next possible offset indices
        a = [b]
        if blp > 0 : a.append(bl)
        if brp > 0 : a.append(br)

        # Make indices not in 'a' zero...
        new_probs = probs.copy()

        for k in range(n):
            if k in a: continue
            new_probs[k] = 0
        
        # ... and normalize
        if (s := sum(new_probs)) > 0:
            factor = 1.0 / s
            new_probs = [x * factor for x in new_probs]
    
        return new_probs


    def random_offset(self):
        probs = list(self.offsets.values())
        n = len(self.offsets)

        if self.children:
            if not self.prev_branch:
                k = np.random.choice(n, p=probs)
                self.prev_branch = k

            else:
                if self.use_prev_branch and np.random.rand() <= self.use_prev_branch:
                    k = self.prev_branch    

                else:
                    new_probs = self.find_non_zero_neighbors()
                    k = np.random.choice(n, p=new_probs)

            child = self.children[k]
            self.prev_branch = k
            return child.random_offset()
        
        else:
            k = np.random.choice(n, p=probs)
            return list(self.offsets)[k]    
        

    def insert_seqs(self, sequences : list[list[Vector]]):
        # Calculate the probability of staying on the same branch
        same = 0.0
        switched = 0.0
        for seq in sequences:
            prev_branch = None
            transitions = zip(seq, seq[1:])
            for loc1, loc2 in transitions:
                offset = loc2 - loc1

                branch, _ = self.closest_branch(offset.normalized())

                if not prev_branch:
                    prev_branch = branch
                    continue

                if branch == prev_branch:
                    same += 1.0
                else:
                    switched += 1.0

                prev_branch = branch

        # Normalize
        if (s := same + switched) > 0:
            factor = 1.0 / s
            self.use_prev_branch = same * factor


# -----------------------------------------------------------------------------
def extract_seqs_per_state(dataset : Dataset):
    # Init dictionary
    sequences: dict[int, list[list[Vector]]] = {}
    for entry in dataset:
        sequences.setdefault(entry[Attribute.PLAYER_STATE.value], [])    
    
    entry0  = dataset[0]
    curr_state = entry0[Attribute.PLAYER_STATE.value]
    lchain = [entry0[Attribute.LOCATION.value]]

    for entry in dataset[1:]:
        s = entry[Attribute.PLAYER_STATE.value]
        l = entry[Attribute.LOCATION.value]

        if s == curr_state:
            lchain.append(l)
        else:
            sequences[curr_state].append(lchain)
            curr_state = s
            lchain = [l]

    return sequences


# -----------------------------------------------------------------------------
# class Offset(MutableMapping):
#     def __init__(self) -> None:
#         self.offsets = dict()


#     def __getitem__(self, key):
#         return self.offsets[key]


#     def __setitem__(self, key, value):
#         self.offsets[key] = value


#     def __delitem__(self, key):
#         del self.offsets[key]


#     def __iter__(self):
#         return iter(self.offsets)
    

#     def __len__(self):
#         return len(self.offsets)


#     def insert(self, offset: Vector):
#         for vec in self.offsets.keys():
#             if offset == vec:
#                 self.offsets[vec] += 1
#                 return

#         self.offsets.setdefault(offset.freeze(), 1)

        
#     def normalize(self):
#         if (s := sum(self.offsets.values())) > 0:
#             factor = 1.0 / s
#             for k, v in self.offsets.items():
#                 self.offsets[k] = v * factor


#     def random_offset(self):
#         offset_idx = np.random.choice(len(self.offsets), p=list(self.offsets.values()))
#         return list(self.offsets)[offset_idx]


