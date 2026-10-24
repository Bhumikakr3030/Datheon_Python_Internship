#!/usr/bin/env python3
"""Terminal Hangman: guess the hidden word letter by letter within 6 mistakes.

Usage:
    python hangman.py                 # play (loads words.csv / words.txt if present)
    python hangman.py my_words.csv    # use a custom word list (.csv or .txt)
    python hangman.py --ai            # watch the computer solve a word
    python hangman.py --benchmark 100 # test the model on unseen words (~1 min)

In the game, type a letter to guess, or ? for a hint from the letter model.

"Machine learning" here is a small statistical model learned from the word
list (standard library only). It combines two signals: (1) the share of
dictionary words that still fit the board and contain a letter, and (2) n-gram
statistics, i.e. how often a letter fills the blanks in matching fragments of
words ("t_e" -> h). The second signal lets it play well even on words it was
not trained on.
"""

import argparse
import csv
import os
import random
import re
import string
import sys
import time
from collections import Counter

MAX_MISTAKES = 6
MAX_HINTS = 3
MIN_WORD_LENGTH = 5
DEFAULT_WORD_FILES = ("words.csv", "words.txt")

# Fallback word list, used when no word file is found.
BUILTIN_WORDS = [
    "python", "variable", "function", "keyboard", "terminal", "algorithm",
    "database", "compiler", "software", "network", "developer", "internet",
    "elephant", "mountain", "chocolate", "umbrella", "adventure", "universe",
    "treasure", "labyrinth", "notebook", "airplane", "festival", "gallows",
    "mystery", "journey", "kingdom", "library", "painting", "squirrel",
]

# The bundled word list is scraped from the web, so it contains some spam,
# adult, and programming-junk entries. Skip those so every puzzle is a fair,
# family-friendly English word.
BLOCKLIST = {
    "starsmerchant", "acdbentity", "ampland", "bufing", "pichunter",
    "thumbzilla", "voyeurweb", "voyuer", "thehun", "kijiji", "msgstr",
    "msgid", "sbjct", "postposted", "nutten", "titten", "verzeichnis",
    "uniprotkb", "twiki", "vbulletin", "jelsoft", "dicke", "gratuit",
    "transexuales", "transexual", "transsexual", "travesti", "zshops",
    "hydrocodone", "phentermine", "tramadol", "cialis", "levitra",
    "valium", "ambien", "adipex", "fioricet", "zoloft", "paxil", "xanax",
    "propecia", "prozac", "ultram", "spank", "spanking", "beastality",
    "shaved", "sucking", "peeing", "chubby", "lingerie", "fetish", "naked",
    "nudist", "erotica", "hairy", "booty", "lesbian", "lesbians", "mature",
    "deviant", "thongs", "thong", "pantyhose", "stockings", "livecam",
    "babes", "teens", "teen", "sexual", "sexuality", "casino", "casinos",
    "poker", "gambling", "blackjack", "roulette", "holdem", "porn",
    "adult", "adults", "bikini", "bitch", "bondage", "boobs", "breast",
    "breasts", "cocks", "cumshot", "cumshots", "dicks", "ejaculation",
    "erotic", "escort", "escorts", "fucked", "fucking", "gangbang",
    "hardcore", "hentai", "incest", "livesex", "marijuana", "masturbating",
    "masturbation", "milfhunter", "milfs", "nipple", "nipples", "nudity",
    "orgasm", "panties", "penis", "playboy", "porno", "pussy", "sexcam",
    "sexually", "sluts", "sperm", "suicide", "swingers", "topless",
    "vagina", "viagra", "voyeur", "whore", "worldsex", "zoophilia",
    "drugs", "torture",
}

# One ASCII picture per number of mistakes (index 0 to 6).
STAGES = [
    """
      +---+
      |   |
          |
          |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
          |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
      |   |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|   |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
          |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
     /    |
          |
    =========
    """,
    """
      +---+
      |   |
      O   |
     /|\\  |
     / \\  |
          |
    =========
    """,
]

VICTORY_ART = r"""
  __   __  ___   _   _    __        _____ _   _ _
  \ \ / / / _ \ | | | |   \ \      / /_ _| \ | | |
   \ V / | | | || | | |    \ \ /\ / / | ||  \| | |
    | |  | |_| || |_| |     \ V  V /  | || |\  |_|
    |_|   \___/  \___/       \_/\_/  |___|_| \_(_)
"""

DEFEAT_ART = r"""
   ____    _    __  __ _____    _____     _______ ____
  / ___|  / \  |  \/  | ____|  / _ \ \   / / ____|  _ \
 | |  _  / _ \ | |\/| |  _|   | | | \ \ / /|  _| | |_) |
 | |_| |/ ___ \| |  | | |___  | |_| |\ V / | |___|  _ <
  \____/_/   \_\_|  |_|_____|  \___/  \_/  |_____|_| \_\
"""


# --------------------------------------------------------------------------
# Word list loading
# --------------------------------------------------------------------------

def read_word_file(path):
    """Read raw words from a .csv (word column, optional hangman_ok) or .txt file."""
    with open(path, encoding="utf-8", newline="") as f:
        if path.lower().endswith(".csv"):
            for row in csv.DictReader(f):
                if row.get("hangman_ok", "yes").strip().lower() != "yes":
                    continue
                yield row.get("word", "")
        else:
            for line in f:
                yield line


def load_words(path=None):
    """Return a cleaned, de-duplicated word list (order preserved)."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [path] if path else [os.path.join(here, n) for n in DEFAULT_WORD_FILES]
    for candidate in candidates:
        if not os.path.isfile(candidate):
            continue
        try:
            cleaned = (w.strip().lower() for w in read_word_file(candidate))
            words = [
                w for w in cleaned
                if w.isascii() and w.isalpha()
                and len(w) >= MIN_WORD_LENGTH and w not in BLOCKLIST
            ]
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
        if words:
            return list(dict.fromkeys(words))
    return BUILTIN_WORDS


# --------------------------------------------------------------------------
# The letter model ("ML")
# --------------------------------------------------------------------------

class LetterModel:
    """Letter recommender learned from a word list.

    Uses only what the player can see (the masked word and the wrong letters).
    Each unguessed letter gets a score from two learned signals:
      * n-gram evidence: for every fragment of the board (length 2-5) that has
        blanks, look at all words in the training list containing a matching
        fragment and count which letters fill the blanks (longer fragments are
        weighted more heavily);
      * dictionary evidence: the share of whole words that still fit the board
        and contain the letter (exact for words in the list).
    """

    MAX_NGRAM = 5
    DICT_WEIGHT = 3.0

    def __init__(self, words):
        self.by_length = {}
        for w in words:
            self.by_length.setdefault(len(w), []).append(w)
        # How many training words contain each letter (fallback / tie-break).
        self.prior = Counter(ch for w in words for ch in set(w))
        # One big string so fragment matching runs inside the regex engine.
        self.corpus = "\n" + "\n".join(words) + "\n"

    def candidates(self, pattern, wrong):
        """Words that fit: pattern is a list of letters/None, wrong a set of letters."""
        known = {ch for ch in pattern if ch}
        fits = []
        for w in self.by_length.get(len(pattern), ()):
            if wrong and not wrong.isdisjoint(w):
                continue
            for ch, p in zip(w, pattern):
                if p is None:
                    if ch in known:   # a revealed letter can't hide elsewhere
                        break
                elif ch != p:
                    break
            else:
                fits.append(w)
        return fits

    def ngram_scores(self, pattern, tried):
        """Weighted counts of letters that fill blanks in matching word fragments."""
        n = len(pattern)
        free = "".join(c for c in string.ascii_lowercase if c not in tried)
        scores = Counter()
        if not free:
            return scores
        blank = f"([{free}])"
        seen = set()
        for k in range(2, min(n, self.MAX_NGRAM) + 1):
            for i in range(n - k + 1):
                window = pattern[i:i + k]
                if all(window):
                    continue          # nothing to learn from a fully known fragment
                rx = "".join(c if c else blank for c in window)
                if i == 0:
                    rx = "(?<=\n)" + rx       # fragment sits at the start of the word
                if i + k == n:
                    rx += "(?=\n)"            # ...or at the end
                if rx in seen:
                    continue
                seen.add(rx)
                for m in re.finditer("(?=" + rx + ")", self.corpus):
                    for letter in m.groups():
                        scores[letter] += k ** 3
        return scores

    def suggest(self, pattern, wrong):
        """Return (letter, share_of_fitting_words_containing_it or None, n_fitting_words)."""
        tried = {ch for ch in pattern if ch} | set(wrong)
        fits = self.candidates(pattern, wrong)
        contain = Counter(ch for w in fits for ch in set(w) if ch not in tried)
        grams = self.ngram_scores(pattern, tried)
        top = max(grams.values()) if grams else 1
        total = {}
        for c in set(grams) | set(contain):
            total[c] = grams[c] / top + (self.DICT_WEIGHT * contain[c] / len(fits) if fits else 0)
        if total:
            letter = max(total, key=lambda c: (total[c], self.prior[c]))
            share = contain[letter] / len(fits) if fits else None
            return letter, share, len(fits)
        remaining = [c for c in string.ascii_lowercase if c not in tried]
        return max(remaining, key=lambda c: self.prior[c]), None, 0

    def baseline_suggest(self, pattern, wrong):
        """Naive strategy for comparison: most common letters overall, in order."""
        tried = {ch for ch in pattern if ch} | set(wrong)
        remaining = [c for c in string.ascii_lowercase if c not in tried]
        return max(remaining, key=lambda c: self.prior[c])


def make_pattern(secret, guessed):
    return [ch if ch in guessed else None for ch in secret]


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def masked_word(secret, guessed):
    """Return the word with unguessed letters hidden, e.g. 'P _ T H _ N'."""
    return " ".join(ch.upper() if ch in guessed else "_" for ch in secret)


def draw(secret, guessed, wrong, message="", hints_left=None):
    clear_screen()
    print("=" * 40)
    print("            H A N G M A N")
    print("=" * 40)
    print(STAGES[len(wrong)])
    print(f"  Word:    {masked_word(secret, guessed)}\n")
    print(f"  Wrong:   {' '.join(sorted(l.upper() for l in wrong)) or '-'}")
    print(f"  Guessed: {' '.join(sorted(l.upper() for l in guessed | wrong)) or '-'}")
    print(f"  Lives:   {'♥ ' * (MAX_MISTAKES - len(wrong))}"
          f"{'x ' * len(wrong)}({MAX_MISTAKES - len(wrong)} left)")
    if hints_left is not None:
        print(f"  Hints:   {hints_left} left  (type ? for a hint)")
    print()
    if message:
        print(f"  >> {message}\n")


def result_screen(won, secret, wrong, hints_used=0):
    if won:
        print(VICTORY_ART)
        print(f"  You saved him! The word was '{secret.upper()}'.")
        print(f"  Mistakes made: {len(wrong)}/{MAX_MISTAKES}"
              + (f"   Hints used: {hints_used}" if hints_used else "") + "\n")
    else:
        print(DEFEAT_ART)
        print(f"  The word was '{secret.upper()}'. Better luck next time!\n")


# --------------------------------------------------------------------------
# Game rounds
# --------------------------------------------------------------------------

def validate_guess(raw, already_used):
    """Return (letter, message). letter is None when the input is not usable."""
    if len(raw) != 1 or not raw.isalpha() or not raw.isascii():
        return None, "Please enter a single letter (A-Z), or ? for a hint."
    if raw in already_used:
        return None, f"You already guessed '{raw.upper()}'. No penalty, try another!"
    return raw, ""


def hint_message(model, secret, guessed, wrong):
    """Ask the model for a letter using only information visible to the player."""
    letter, share, n = model.suggest(make_pattern(secret, guessed), wrong)
    if share is None:
        return f"Hint: try '{letter.upper()}' (it fits the letter patterns seen so far)."
    return (f"Hint: try '{letter.upper()}' - it appears in {share:.0%} of the "
            f"{n} possible words that still fit.")


def play_round(words, model):
    secret = random.choice(words)
    letters_needed = set(secret)
    guessed = set()   # correct letters
    wrong = set()     # incorrect letters
    hints_used = 0
    message = "Good luck!"

    while True:
        draw(secret, guessed, wrong, message, MAX_HINTS - hints_used)

        if letters_needed <= guessed:
            result_screen(True, secret, wrong, hints_used)
            return True
        if len(wrong) >= MAX_MISTAKES:
            result_screen(False, secret, wrong)
            return False

        raw = input("  Guess a letter: ").strip().lower()

        if raw in ("?", "hint"):
            if hints_used >= MAX_HINTS:
                message = "No hints left!"
            else:
                hints_used += 1
                message = hint_message(model, secret, guessed, wrong)
            continue

        letter, message = validate_guess(raw, guessed | wrong)
        if letter is None:
            continue  # invalid or duplicate: no penalty

        if letter in secret:
            guessed.add(letter)
            message = f"Nice! '{letter.upper()}' is in the word."
        else:
            wrong.add(letter)
            message = f"Sorry, no '{letter.upper()}' in the word."


def play_ai_round(words, model, delay=0.8):
    """Watch the letter model solve a random word."""
    secret = random.choice(words)
    letters_needed = set(secret)
    guessed, wrong = set(), set()
    message = "The AI is thinking..."

    while True:
        draw(secret, guessed, wrong, message)
        if letters_needed <= guessed:
            result_screen(True, secret, wrong)
            return True
        if len(wrong) >= MAX_MISTAKES:
            result_screen(False, secret, wrong)
            return False

        time.sleep(delay)
        letter, share, n = model.suggest(make_pattern(secret, guessed), wrong)
        why = f" ({share:.0%} of {n} candidate words)" if share is not None else ""
        if letter in secret:
            guessed.add(letter)
            message = f"AI guesses '{letter.upper()}'{why}: hit!"
        else:
            wrong.add(letter)
            message = f"AI guesses '{letter.upper()}'{why}: miss."


def solve_silently(secret, suggest):
    """Run one game with a strategy; return (won, mistakes)."""
    guessed, wrong = set(), set()
    while len(wrong) < MAX_MISTAKES and not set(secret) <= guessed:
        letter = suggest(make_pattern(secret, guessed), wrong)
        (guessed if letter in secret else wrong).add(letter)
    return set(secret) <= guessed, len(wrong)


def benchmark(words, n):
    """Train on 80% of the words, then test on unseen words (held-out split).

    This measures how well the model generalises to words it has never seen,
    which is the honest test; in the real game the secret word is always in
    the model's vocabulary, so it plays even better there.
    """
    shuffled = random.sample(words, len(words))
    cut = int(len(shuffled) * 0.8)
    train, test = shuffled[:cut], shuffled[cut:]
    model = LetterModel(train)
    sample = random.sample(test, min(n, len(test)))
    print(f"\n  Trained on {len(train)} words, tested on {len(sample)} unseen words:\n")
    for name, strategy in (
        ("Naive letter-frequency", model.baseline_suggest),
        ("Letter model          ", lambda p, w: model.suggest(p, w)[0]),
    ):
        results = [solve_silently(s, strategy) for s in sample]
        wins = sum(won for won, _ in results)
        avg_miss = sum(m for _, m in results) / len(results)
        print(f"  {name}  win rate {wins / len(results):6.1%}   "
              f"avg mistakes {avg_miss:.2f}")
    print()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Terminal Hangman with a letter-prediction model.")
    parser.add_argument("wordfile", nargs="?", help="word list (.csv with a 'word' column, or .txt)")
    parser.add_argument("--ai", action="store_true", help="watch the computer play")
    parser.add_argument("--delay", type=float, default=0.8, help="seconds between AI guesses")
    parser.add_argument("--benchmark", type=int, metavar="N", help="test the model on N random words")
    args = parser.parse_args()

    words = load_words(args.wordfile)

    if args.benchmark:
        benchmark(words, args.benchmark)
        return

    model = LetterModel(words)

    wins = losses = 0
    try:
        while True:
            won = play_ai_round(words, model, args.delay) if args.ai else play_round(words, model)
            wins += won
            losses += not won
            print(f"  Score  ->  Wins: {wins}   Losses: {losses}\n")
            again = input("  Play again? (y/n): ").strip().lower()
            if again not in ("y", "yes"):
                break
    except (KeyboardInterrupt, EOFError):
        print()

    print("\n  Thanks for playing Hangman. Goodbye!\n")


if __name__ == "__main__":
    main()
