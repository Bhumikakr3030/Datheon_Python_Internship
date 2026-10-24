#!/usr/bin/env python3
"""Hangman - a terminal game using the google-10000-english word list.

Word source (in order of preference):
  1. words.txt next to this script (one word per line)
  2. downloaded from the google-10000-english GitHub repo, then cached to words.txt
"""

import random
import string
import sys
import urllib.request
from pathlib import Path

WORDS_URL = (
    "https://raw.githubusercontent.com/first20hours/google-10000-english/"
    "master/google-10000-english-no-swears.txt"
)
WORDS_FILE = Path(__file__).with_name("words.txt")
MIN_LENGTH = 4  # words shorter than this make for a dull game
MAX_MISSES = 6

STAGES = [
    """
  +---+
  |   |
      |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========""",
]


def load_words():
    """Return a list of playable words, using the local cache or downloading."""
    if WORDS_FILE.exists():
        text = WORDS_FILE.read_text()
    else:
        print("Downloading word list...")
        try:
            with urllib.request.urlopen(WORDS_URL, timeout=10) as resp:
                text = resp.read().decode("utf-8")
            WORDS_FILE.write_text(text)
        except OSError as err:
            sys.exit(f"Could not download the word list ({err}).\n"
                     f"Save it as {WORDS_FILE} and run again.")
    words = [w.strip().lower() for w in text.splitlines()]
    return [w for w in words if w.isalpha() and len(w) >= MIN_LENGTH]


def display_word(word, guessed):
    return " ".join(c if c in guessed else "_" for c in word)


def get_guess(guessed):
    """Prompt until the player enters a single new letter."""
    while True:
        raw = input("Guess a letter: ").strip().lower()
        if len(raw) != 1 or raw not in string.ascii_lowercase:
            print("Please enter a single letter (a-z).")
        elif raw in guessed:
            print(f"You already guessed '{raw}'.")
        else:
            return raw


def play_round(word):
    """Play one game. Returns True if the player won."""
    guessed = set()
    misses = 0

    while misses < MAX_MISSES:
        print(STAGES[misses])
        print(f"\nWord:   {display_word(word, guessed)}")
        wrong = sorted(g for g in guessed if g not in word)
        print(f"Missed: {' '.join(wrong) if wrong else '-'}  "
              f"({MAX_MISSES - misses} left)")

        letter = get_guess(guessed)
        guessed.add(letter)

        if letter in word:
            print(f"Yes! '{letter}' is in the word.")
            if all(c in guessed for c in word):
                print(STAGES[misses])
                print(f"\nWord:   {display_word(word, guessed)}")
                return True
        else:
            misses += 1
            print(f"No '{letter}' in the word.")

    print(STAGES[MAX_MISSES])
    print(f"\nOut of guesses! The word was '{word}'.")
    return False


def main():
    words = load_words()
    wins = losses = 0
    print("=== HANGMAN ===")
    print(f"{len(words)} words loaded. You get {MAX_MISSES} wrong guesses.")

    while True:
        if play_round(random.choice(words)):
            wins += 1
            print("You won!")
        else:
            losses += 1
        print(f"Score - wins: {wins}, losses: {losses}")

        again = input("\nPlay again? (y/n): ").strip().lower()
        if again != "y":
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
