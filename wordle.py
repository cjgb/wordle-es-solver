'''
@gilbellosta, 2023-04-04
'''

import json
import sys
import copy
import argparse
from pathlib import Path

from collections import Counter

# Configuration constants
WORDLE_NUMBER_LETTERS = 5
DEFAULT_FIRST_GUESS = 'seria'
PLACEHOLDER_CHAR = '.'
TOP_WORDS_TO_SHOW = 5
MIN_CANDIDATES_FOR_TWO_OPTION_STRATEGY = 2
FEW_OPTIONS_THRESHOLD = 10
POPULARITY_MULTIPLIER = 5
NEW_OPTIONS_COUNT = 20
TRIMMED_CANDIDATES_SIZE = 100
MAX_ATTEMPTS = 6
VERBOSE = False

def get_data_file_path():
    """Get the path to the data file, works both in development and when installed"""
    # Try to find the data file relative to this file
    current_dir = Path(__file__).parent
    data_file = current_dir / "data" / "popularidad.json"

    if data_file.exists():
        return str(data_file)

    # Fallback for when installed as package
    return str(Path(__file__).parent / "data" / "popularidad.json")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Wordle solver - Finds optimal guesses for Wordle puzzles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  wordle jugar          # Solve for target word "jugar"
  wordle casa seria     # Solve for "casa" starting with "seria"
  wordle prueba -v      # Solve with verbose output
  wordle test -g prueba # Solve for "test" starting with "prueba"
        '''
    )

    parser.add_argument(
        'target',
        help=f'Target word to solve for (must be {WORDLE_NUMBER_LETTERS} letters)'
    )

    parser.add_argument(
        '--guess', '-g',
        default=DEFAULT_FIRST_GUESS,
        help=f'First guess word (default: {DEFAULT_FIRST_GUESS})'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output showing detailed reasoning'
    )

    return parser.parse_args()

# Load corpus data
data_file_path = get_data_file_path()
with open(data_file_path, 'r') as f:
    corpus = json.load(f)


class State():
    def __init__(self):
        # green/correct characters
        self.p = [PLACEHOLDER_CHAR] * WORDLE_NUMBER_LETTERS
        # letters not in position i
        self.n = [set() for _ in  range(WORDLE_NUMBER_LETTERS)]
        # other letters that are somewhere in the word
        self.other = set()
        # letters not in word
        self.excluded = set()

    def update(self, candidate, target):

        for i in range(WORDLE_NUMBER_LETTERS):
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

        for i in range(WORDLE_NUMBER_LETTERS):

            if not state.p[i] == PLACEHOLDER_CHAR:
                tmp = [w for w in tmp if w[i] == state.p[i]]

            if len(state.n[i]) > 0:
                tmp = [w for w in tmp if not w[i] in state.n[i]]

        self.corpus = {w : self.corpus[w] for w in tmp}


def verbose_print(message):
    """Print message only if verbose mode is enabled"""
    if VERBOSE:
        print(message)

def wordle(candidates, state, corpus):

    if candidates.size() == 1:
        verbose_print(f'   Solo queda una opción.')
        verbose_print('')
        return candidates.head(1)[0][0]

    verbose_print(f'   Quedan {candidates.size()} opciones.')
    verbose_print(f'   Las más populares son:')

    for word, popularity in candidates.head(TOP_WORDS_TO_SHOW):
        verbose_print(f'     {word} : {popularity}')

    verbose_print('')

    # si solo hay dos, devolver la más frecuente
    if candidates.size() == MIN_CANDIDATES_FOR_TWO_OPTION_STRATEGY:
        return candidates.head(1)[0][0]

    # si hay pocas opciones y una es mucho más corriente que el resto...
    if candidates.size() < FEW_OPTIONS_THRESHOLD:
        tmp = candidates.head(2)
        if (tmp[0][1] > POPULARITY_MULTIPLIER * tmp[1][1]):
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
    new_options = [k for (k, v) in res[0:NEW_OPTIONS_COUNT]]

    my_candidates.extend(new_options)

    # for each new candidate, we estimate the size of the
    # resulting candidates set and we'll keep the new candidate
    # that would break into the smallest dataset

    res = {}
    trimmed_candidates = copy.deepcopy(candidates)
    trimmed_candidates.trim(TRIMMED_CANDIDATES_SIZE)
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
    """Main function to run the Wordle solver"""
    try:
        args = parse_args()

        # Validate target word
        if len(args.target) != WORDLE_NUMBER_LETTERS:
            print(f"Error: Target word '{args.target}' must be exactly {WORDLE_NUMBER_LETTERS} letters long")
            sys.exit(1)

        # Validate first guess
        if len(args.guess) != WORDLE_NUMBER_LETTERS:
            print(f"Error: First guess '{args.guess}' must be exactly {WORDLE_NUMBER_LETTERS} letters long")
            sys.exit(1)

        # Set verbose flag globally
        global VERBOSE
        VERBOSE = args.verbose

        if VERBOSE:
            print(f"Starting Wordle solver...")
            print(f"Target: {args.target}")
            print(f"First guess: {args.guess}")
            print(f"Word length: {WORDLE_NUMBER_LETTERS}")
            print(f"Max attempts: {MAX_ATTEMPTS}")
            print("")

        game_state = State()
        candidates = Candidates(corpus)

        if VERBOSE:
            print(f"Initial corpus size: {candidates.size()} words")
            print("")

        for i in range(MAX_ATTEMPTS):
            if i == 0:
                my_candidate = args.guess
            else:
                my_candidate = wordle(candidates, game_state, corpus)

            print(f'Intento {i+1} -> {my_candidate}')
            print('')

            if my_candidate == args.target:
                print(f'Solución en {i+1} intentos: {my_candidate}')
                if VERBOSE:
                    print(f"Remaining candidates: {candidates.size()}")
                return 0

            game_state.update(my_candidate, args.target)
            candidates.filter(game_state)

            if VERBOSE and candidates.size() > 0:
                print(f"   After filtering: {candidates.size()} candidates remaining")
                print("")

        # If we reach here, we didn't find the solution
        print(f"No se encontró solución en {MAX_ATTEMPTS} intentos")
        if candidates.size() > 0:
            print(f"Palabras candidatas restantes: {candidates.size()}")
            if VERBOSE:
                print("Algunas opciones:", [w for w, _ in candidates.head(5)])
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)