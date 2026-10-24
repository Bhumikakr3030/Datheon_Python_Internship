#!/usr/bin/env python3
"""Terminal-based Hangman game. Run with: python hangman.py"""

import csv
import random
import string
from pathlib import Path

MAX_MISTAKES = 6

HANGMAN_STAGES = [
    r"""
     +---+
     |   |
         |
         |
         |
    =========""",
    r"""
     +---+
     |   |
     O   |
         |
         |
    =========""",
    r"""
     +---+
     |   |
     O   |
     |   |
         |
    =========""",
    r"""
     +---+
     |   |
     O   |
    /|   |
         |
    =========""",
    r"""
     +---+
     |   |
     O   |
    /|\  |
         |
    =========""",
    r"""
     +---+
     |   |
     O   |
    /|\  |
    /    |
    =========""",
    r"""
     +---+
     |   |
     O   |
    /|\  |
    / \  |
    =========""",
]

FALLBACK_WORDS = [
    "python", "hangman", "computer", "keyboard", "journey", "library",
    "puzzle", "rainbow", "mountain", "diamond", "picture", "science",
    "freedom", "sunshine", "elephant", "sandwich", "treasure", "whisper",
]


def load_words():
    """Load eligible words from words.csv beside this script, if available."""
    csv_path = Path(__file__).with_name("words.csv")
    if csv_path.is_file():
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                words = []
                for row in reader:
                    word = (row.get("word") or "").strip().lower()
                    eligible = (row.get("hangman_ok") or "").strip().lower()
                    if word.isalpha() and len(word) >= 4 and (
                        eligible == "yes" or not row.get("hangman_ok")
                    ):
                        words.append(word)
                if words:
                    return list(dict.fromkeys(words))
        except (OSError, csv.Error):
            pass
    return FALLBACK_WORDS


def display_game(secret_word, guessed_letters, mistakes):
    print(HANGMAN_STAGES[mistakes])
    masked_word = " ".join(
        letter.upper() if letter in guessed_letters else "_"
        for letter in secret_word
    )
    print(f"\nWord: {masked_word}")
    print(f"Incorrect guesses: {mistakes}/{MAX_MISTAKES}")
    if guessed_letters:
        print("Guessed letters: " + " ".join(sorted(guessed_letters).upper())
              if False else "Guessed letters: " + " ".join(
                  letter.upper() for letter in sorted(guessed_letters)
              ))
    else:
        print("Guessed letters: (none)")
    print()


def play_game():
    secret_word = random.choice(load_words()).lower()
    guessed_letters = set()
    mistakes = 0

    print("=" * 36)
    print("          H A N G M A N")
    print("=" * 36)
    print(f"Guess the hidden word! You have {MAX_MISTAKES} incorrect guesses.")
    print("Enter one letter at a time, or type 'quit' to exit.\n")

    while mistakes < MAX_MISTAKES:
        display_game(secret_word, guessed_letters, mistakes)

        if all(letter in guessed_letters for letter in secret_word):
            print("🎉 YOU WIN! 🎉")
            print(f"The word was: {secret_word.upper()}")
            return

        guess = input("Your guess: ").strip().lower()

        if guess in {"quit", "exit"}:
            print(f"\nGame ended. The word was: {secret_word.upper()}")
            return

        if len(guess) != 1 or guess not in string.ascii_lowercase:
            print("Please enter a single letter from A to Z.\n")
            continue

        if guess in guessed_letters:
            print(f"You already guessed '{guess.upper()}'. Try another letter.")
            print("No attempt was deducted.\n")
            continue

        guessed_letters.add(guess)

        if guess in secret_word:
            print(f"Correct! '{guess.upper()}' is in the word.\n")
        else:
            mistakes += 1
            print(f"Sorry, '{guess.upper()}' is not in the word.\n")

    display_game(secret_word, guessed_letters, mistakes)
    print("GAME OVER — YOU'RE OUT OF ATTEMPTS!")
    print(f"The word was: {secret_word.upper()}")


if __name__ == "__main__":
    try:
        play_game()
    except (KeyboardInterrupt, EOFError):
        print("\n\nGame closed. Thanks for playing!")
