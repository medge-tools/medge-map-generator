from mathutils import Vector

import numpy as np
from sys import float_info
from collections.abc import MutableMapping


# -----------------------------------------------------------------------------
class OffsetNode(MutableMapping):
    def __init__(self, parent = None):
        self.offsets = dict()
        self.children : list[OffsetNode] = []
        self.same_branch = .5
        self.prev_branch = None
        
        if parent:
            parent.children.append(self)

    #region Override
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

    def statistics(self):
        data = np.zeros((0, 2), dtype=int)
        
        for idx, (k, v) in enumerate(self.offsets.items()):
            child = self.children[idx]
            n = len(child.offsets)

            key = str(k)
            val = str(round(v, 3))

            data = np.append(data, [[key, val]], axis=0)

        return data


    def add_branch(self, offset: Vector):
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


    # Find left and right non 0 probability neighbors of the previous branch
    def find_non_zero_neighbors(self) -> list[float]:
        n = len(self.offsets)

        if n < 3: return

        probs = list(self.offsets.values())
        b = self.prev_branch
        bl = b - 1
        br = (b + 1) % n
        for k in range(2, n, 1):
            if (blp := probs[bl]) <= 0:
                bl = b - k
            if (brp := probs[br]) <= 0:
                br = (b + k) % n
            if bl == br:
                break

        a = [b]
        if blp > 0              : a.append(bl)
        if brp > 0 and bl != br : a.append(br)

        # The probabilities of the indices not in 'a' are set to be 0
        # The probabilities of the indices in 'a' have to sum to 1
        # If the probability was 0 then it has to stay 0
        rest = 0
        count = 0
        new_probs = probs.copy()

        for j in range(n):
            p = new_probs[j]
            
            if j in a: 
                if p == 0:
                    count += 1
                continue

            rest += p
            new_probs[j] = 0
            count += 1
        
        rest /= (n - count)

        for j in range(n):
            if j not in a or new_probs[j] == 0: 
                continue
            
            new_probs[j] += rest 

        return new_probs


    def random_offset(self):
        probs = list(self.offsets.values())
        n = len(self.offsets)

        if self.children:
            if not self.prev_branch:
                k = np.random.choice(n, p=probs)
                self.prev_branch = k

            else:
                if np.random.rand() <= self.same_branch:
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


# -----------------------------------------------------------------------------
class OffsetDoubleLevelTree(OffsetNode):
    def __init__(self):
        super().__init__()
        self.add_branch(Vector(( 1,  0, 0)))
        self.add_branch(Vector((-1,  0, 0)))
        self.add_branch(Vector(( 0,  1, 0)))
        self.add_branch(Vector(( 0, -1, 0)))


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


