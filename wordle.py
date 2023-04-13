'''
@gilbellosta, 2023-04-04
'''

import json
import sys
import copy

from collections import Counter

wordle_number_letters = 5
first_guess = 'seria'

with open('data/popularidad.json', 'r') as f:
    corpus = json.load(f)


class State():
    def __init__(self):
        # green/correct characters
        self.p = ['.'] * wordle_number_letters
        # letters not in position i
        self.n = [set() for _ in  range(wordle_number_letters)]
        # other letters that are somewhere in the word
        self.other = set()
        # letters not in word
        self.excluded = set()

    def update(self, candidate, target):

        for i in range(wordle_number_letters):
            if target[i] == candidate[i]:
                self.p[i] = target[i]
            else:
                self.n[i].add(candidate[i])

        matches = set(candidate).intersection(target)
        self.other = self.other.union(matches)

        errors = set(candidate).difference(target)
        self.excluded = self.excluded.union(errors)


class Candidates():
    def __init__(self, corpus):
        self.corpus = corpus

    def size(self):
        return len(self.corpus)

    def head(self, n):
        return sorted(self.corpus.items(), key = lambda item: -item[1])[0:n]

    def get_words(self):
        return list(self.corpus.keys())

    def trim(self, n):
        self.corpus = {k : v for k, v in self.head(n)}

    def filter(self, state):

        tmp = self.get_words()

        for excluded in state.excluded:
            tmp = [w for w in tmp if not excluded in w ]

        for existing in state.other:
            tmp = [w for w in tmp if existing in w]

        for i in range(wordle_number_letters):

            if not state.p[i] == '.':
                tmp = [w for w in tmp if w[i] == state.p[i]]

            if len(state.n[i]) > 0:
                tmp = [w for w in tmp if not w[i] in state.n[i]]

        self.corpus = {w : self.corpus[w] for w in tmp}


def wordle(candidates, state, corpus):

    if candidates.size() == 1:
        print(f'   Solo queda una opción.')
        print('')
        return candidates.head(1)[0][0]

    print(f'   Quedan {candidates.size()} opciones.')
    print(f'   Las más populares son:')

    for word, popularity in candidates.head(5):
        print(f'     {word} : {popularity}')

    print('')

    # si solo hay dos, devolver la más frecuente
    if candidates.size() == 2:
        return candidates.head(1)[0][0]

    # si hay pocas opciones y una es mucho más corriente que el resto...
    if candidates.size() < 10:
        tmp = candidates.head(2)
        if (tmp[0][1] > 5 * tmp[1][1]):
            return candidates.head(1)[0][0]

    # we look for words not in candidates which:
    #     - contain the most frequent _other_ letters in our candidates
    #     - may prove to be good candidates later

    # first, we found the most frequent letters (among those still unknown)
    # in our set of candidates

    my_candidates = candidates.get_words()
    tmp = Counter(''.join(my_candidates))
    other_letters = {k : v for k, v in tmp.items() if not k in state.other}

    # now we are going to find words in the general corpus which contain many of
    # these yet available letters
    res = { word : sum([other_letters.get(l, 0) for l in set(word)])
           for word in corpus.keys() }

    res = sorted(res.items(), key = lambda x: -x[1])
    new_options = [k for (k, v) in res[0:20]]

    my_candidates.extend(new_options)

    # for each new candidate, we estimate the size of the
    # resulting candidates set and we'll keep the new candidate
    # that would break into the smallest dataset

    res = {}
    trimmed_candidates = copy.deepcopy(candidates)
    trimmed_candidates.trim(100)
    for word in my_candidates:
        res[word] = []
        for possible_target in trimmed_candidates.get_words():
            state_tmp = copy.deepcopy(state)
            candidates_tmp = copy.deepcopy(trimmed_candidates)
            state_tmp.update(word, possible_target)
            candidates_tmp.filter(state_tmp)
            res[word].append(candidates_tmp.size())

    res = {k : sum(v) / len(v) for k, v in res.items()}

    return min(res, key = res.get)


def main():

    my_target = sys.argv[1]
    my_guess = 'seria' if len(sys.argv) < 3 else sys.argv[2]

    game_state = State()
    candidates = Candidates(corpus)

    for i in range(6):
        if i == 0:
            my_candidate = my_guess
        else:
            my_candidate = wordle(candidates, game_state, corpus)

        print(f'Intento {i+1} -> {my_candidate}')
        print('')

        if my_candidate == my_target:
            print(f'Solución en {i+1} intentos: {my_candidate}')
            break

        game_state.update(my_candidate, my_target)
        candidates.filter(game_state)

if __name__ == "__main__":
    main()