#!/usr/bin/env python3
"""Terminal Hangman - Datheon internship project.

Guess the hidden word one letter at a time. You have 6 wrong guesses
before the man is hanged. Repeated guesses never cost you an attempt.

Word source: 'words.csv' (columns: word, length, hangman_ok) in the same
folder as this script. Only rows with hangman_ok = yes are used. If the file
is missing or unreadable, a built-in word list is used instead.
"""

import csv
import os
import random

MAX_MISTAKES = 6
MIN_WORD_LENGTH = 4
WORD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.csv")

FALLBACK_WORDS = [
    "python", "internship", "developer", "keyboard", "terminal", "function",
    "variable", "algorithm", "compiler", "database", "network", "software",
    "program", "library", "package", "browser", "monitor", "textbook",
    "challenge", "solution",
]

# One ASCII picture per number of mistakes (0 to 6).
STAGES = [
    r"""
      +---+
      |   |
          |
          |
          |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
          |
          |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
      |   |
          |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
     /|   |
          |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
     /|\  |
          |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
     /|\  |
     /    |
          |
    =========
    """,
    r"""
      +---+
      |   |
      O   |
     /|\  |
     / \  |
          |
    =========
    """,
]


def load_words(path=WORD_FILE):
    """Load playable words from the CSV file, or fall back to the built-in list."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            words = [
                row["word"].strip().lower()
                for row in csv.DictReader(f)
                if row.get("hangman_ok", "").strip().lower() == "yes"
                and row["word"].strip().isalpha()
                and len(row["word"].strip()) >= MIN_WORD_LENGTH
            ]
        if words:
            return words
    except (OSError, KeyError, csv.Error):
        pass
    return FALLBACK_WORDS


def masked_word(word, correct):
    """Return the word with unguessed letters hidden, e.g. '_ A _ H E O N'."""
    return " ".join(ch.upper() if ch in correct else "_" for ch in word)


def get_guess(already_guessed):
    """Prompt until the player enters one new-or-repeated letter."""
    while True:
        raw = input("Guess a letter: ").strip().lower()
        if len(raw) != 1 or not raw.isalpha():
            print("Please enter a single letter (A-Z).")
        elif raw in already_guessed:
            print(f"You already guessed '{raw.upper()}'. No penalty - try another letter.")
        else:
            return raw


def play_round(words):
    word = random.choice(words)
    correct = set()
    wrong = set()

    print("\n=== HANGMAN ===")
    print(f"The word has {len(word)} letters. You may make {MAX_MISTAKES} mistakes.")

    while True:
        mistakes = len(wrong)
        print(STAGES[mistakes])
        print("Word:   ", masked_word(word, correct))
        print("Wrong:  ", " ".join(sorted(l.upper() for l in wrong)) or "-")
        print("Lives:  ", MAX_MISTAKES - mistakes)

        if set(word) <= correct:
            print(f"\nYou won! The word was '{word.upper()}'.")
            return
        if mistakes >= MAX_MISTAKES:
            print(f"\nGame over! The word was '{word.upper()}'.")
            return

        guess = get_guess(correct | wrong)
        if guess in word:
            correct.add(guess)
            print(f"Good guess! '{guess.upper()}' is in the word.")
        else:
            wrong.add(guess)
            print(f"Sorry, '{guess.upper()}' is not in the word.")


def main():
    words = load_words()
    while True:
        play_round(words)
        again = input("\nPlay again? (y/n): ").strip().lower()
        if again not in ("y", "yes"):
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()
