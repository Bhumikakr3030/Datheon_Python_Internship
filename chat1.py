"""
Rule-based customer support chatbot.
Uses sample_faq.json for greeting keywords and FAQ answers.

Run:
    python chatbot.py
"""

import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).with_name("sample_faq.json")

EXIT_COMMANDS = {"bye", "exit", "quit", "goodbye"}


def load_dataset(path=DATA_FILE):
    """Load the greeting keywords and FAQ entries from the JSON dataset."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Could not find {path.name}. Keep it in the same folder as chatbot.py."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("The FAQ dataset must be a JSON object.")
    if not isinstance(data.get("greetings", []), list):
        raise ValueError("'greetings' must be a list.")
    if not isinstance(data.get("faqs", []), list):
        raise ValueError("'faqs' must be a list.")

    return data


def normalize(text):
    """Lowercase input and normalize whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def contains_phrase(text, phrase):
    """Match a phrase as whole words, allowing flexible whitespace."""
    words = re.escape(normalize(phrase)).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!\w){words}(?!\w)", text) is not None


def is_greeting(message, greetings):
    return any(contains_phrase(message, greeting) for greeting in greetings)


def find_faq(message, faqs):
    """Return the best matching FAQ using simple keyword/regex rules."""
    rules = [
        (
            re.compile(r"\b(hours?|opening|closing|business hours|operate|open|close)\b"),
            ("hours of operation", "hours of operation"),
        ),
        (
            re.compile(r"\b(submit|submission|turn in|upload)\b.*\b(project|github|repository|repo)\b|\b(project|github|repository|repo)\b.*\b(submit|submission|upload)\b"),
            ("internship project", "internship project"),
        ),
        (
            re.compile(r"\b(certificate|certification)\b|\bwhen\b.*\b(receive|get|issued)\b"),
            ("certificate", "certificate"),
        ),
    ]

    # Map FAQ records to their source dataset entries, using their question text.
    for pattern, keywords in rules:
        if pattern.search(message):
            for faq in faqs:
                question = normalize(faq.get("question", ""))
                if any(keyword in question for keyword in keywords):
                    return faq

    # Generic fallback: compare meaningful words in the user's message to each FAQ.
    stop_words = {
        "what", "when", "where", "how", "do", "i", "we", "you", "your",
        "are", "is", "the", "a", "an", "to", "my", "our", "of", "for",
        "can", "will", "please", "tell", "me", "about"
    }
    user_words = set(re.findall(r"\b[a-z]{3,}\b", message)) - stop_words
    best_faq, best_score = None, 0
    for faq in faqs:
        question_words = set(re.findall(r"\b[a-z]{3,}\b", normalize(faq.get("question", "")))) - stop_words
        score = len(user_words & question_words)
        if score > best_score:
            best_faq, best_score = faq, score

    # Require at least one meaningful keyword overlap to avoid unrelated answers.
    return best_faq if best_score >= 1 else None
