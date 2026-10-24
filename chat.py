
# !/usr/bin/env python3
"""chatbot.py - A rule-based customer support / product assistant.

How it works
  1. Input is normalized (lowercase, punctuation stripped, whitespace collapsed).
  2. Regex rules catch exit commands, greetings, thanks and business-hours questions.
  3. Everything else is matched against the FAQ dataset (JSON) by keyword overlap,
     which yields a confidence score between 0 and 1.
  4. High confidence -> answer. Medium -> "Did you mean ...?". Low -> graceful fallback.

Conversation state:  GREETING -> ACTIVE (intent identification + resolution) -> EXIT

Usage:
    python chatbot_standalone.py       # uses the FAQ data embedded in this file
    python chatbot_standalone.py my_faq.json   # optional: load a JSON file instead

Dataset format:
    {"greetings": ["hello", ...],
     "faqs": [{"question": "...", "answer": "..."}, ...]}
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

BOT_NAME = "Aria"
IST = timezone(timedelta(hours=5, minutes=30))
OPEN_HOUR, CLOSE_HOUR = 9, 18  # Mon-Fri, 9:00 AM - 6:00 PM IST
# The FAQ dataset, embedded directly in the program (no JSON file needed).
FAQ_DATA = {
    "greetings": ["hello", "hi", "hey", "good morning", "good afternoon"],
    "faqs": [
        {
            "question": "What are your hours of operation?",
            "answer": "We operate Monday through Friday from 9:00 AM to 6:00 PM IST.",
        },
        {
            "question": "How do I submit my internship project?",
            "answer": "You can submit your public GitHub repository link through your Student Workspace.",
        },
        {
            "question": "When will I receive my certificate?",
            "answer": "Certificates are reviewed and issued within 3-5 business days after your code review.",
        },
    ],
}

ANSWER_THRESHOLD = 0.50  # confident enough to answer directly
SUGGEST_THRESHOLD = 0.25  # not sure: offer a "Did you mean...?"

EXIT_RE = re.compile(r"^(bye|goodbye|exit|quit|q|see you|cya)\b")
THANKS_RE = re.compile(r"\b(thanks|thank you|thx|cheers)\b")
HOURS_RE = re.compile(
    r"\b(hours?|timings?|open|opens|opening|close|closes|closing|closed|"
    r"working days?|business hours|schedule|available)\b"
)
OPEN_NOW_RE = re.compile(r"\b(now|today|currently|right now|tonight|open yet)\b")
HELP_RE = re.compile(r"\b(help|what can you do|options|menu)\b")

STOPWORDS = {
    "a", "an", "the", "is", "are", "am", "was", "do", "does", "did", "i", "me",
    "my", "we", "you", "your", "can", "could", "would", "should", "to", "of",
    "in", "on", "for", "and", "or", "it", "this", "that", "please", "what",
    "how", "where", "will", "be", "get", "about", "tell", "want", "need",
    "know", "there", "any",
}

# Map different wordings to one canonical keyword so "send" matches "submit", etc.
SYNONYMS = {
    "send": "submit", "upload": "submit", "turn": "submit", "submission": "submit",
    "hand": "submit", "cert": "certificate", "certificates": "certificate",
    "got": "receive", "recieve": "receive", "obtain": "receive",
    "timing": "hour", "time": "hour", "open": "hour", "operate": "hour",
    "operation": "hour", "schedule": "hour",
    "github": "repository", "repo": "repository", "link": "repository",
    "long": "when", "soon": "when", "issued": "receive", "issue": "receive",
}


class State(Enum):
    GREETING = "greeting"
    ACTIVE = "active"
    EXIT = "exit"


# ---------------------------------------------------------------- text helpers
def normalize(text: str) -> str:
    """Lowercase, replace punctuation with spaces, collapse whitespace."""
    text = re.sub(r"[^\w\s]", " ", text.lower().strip())
    return re.sub(r"\s+", " ", text).strip()


def stem(word: str) -> str:
    """Very light stemming so 'hours'/'hour', 'submitting'/'submit' line up."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def keywords(text: str) -> set:
    words = (stem(w) for w in normalize(text).split() if w not in STOPWORDS)
    return {SYNONYMS.get(w, w) for w in words if len(w) > 1}


# ------------------------------------------------------------------- the bot
class FAQBot:
    def __init__(self, data: dict):
        self.greetings = {normalize(g) for g in data.get("greetings", [])} or {"hello", "hi", "hey"}
        self.faqs = [
            {"question": f["question"], "answer": f["answer"], "kw": keywords(f["question"])}
            for f in data.get("faqs", [])
            if "question" in f and "answer" in f
        ]
        self.state = State.GREETING
        self.pending_suggestion = None  # FAQ offered via "Did you mean...?"

    @staticmethod
    def _load(path: Path) -> dict:
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            print(f"[warning] Dataset not found: {path}. Starting with no FAQs.", file=sys.stderr)
        except json.JSONDecodeError as exc:
            print(f"[warning] Invalid JSON in {path}: {exc}. Starting with no FAQs.", file=sys.stderr)
        return {}

    # ---- matching
    def best_match(self, text: str):
        """Return (faq, confidence) for the best FAQ, or (None, 0.0)."""
        user_kw = keywords(text)
        if not user_kw:
            return None, 0.0
        best, best_score = None, 0.0
        for faq in self.faqs:
            if not faq["kw"]:
                continue
            overlap = len(user_kw & faq["kw"])
            if overlap == 0:
                continue
            coverage = overlap / len(faq["kw"])  # how much of the FAQ the user hit
            precision = overlap / len(user_kw)  # how much of the user's text was on-topic
            score = 0.6 * coverage + 0.4 * precision
            if score > best_score:
                best, best_score = faq, score
        return best, best_score

    def hours_reply(self, text: str) -> str:
        base = next((f["answer"] for f in self.faqs if "hour" in f["kw"]),
                    f"We operate Monday through Friday, {OPEN_HOUR}:00 AM to {CLOSE_HOUR - 12}:00 PM IST.")
        if not OPEN_NOW_RE.search(text):
            return base
        now = datetime.now(IST)
        is_open = now.weekday() < 5 and OPEN_HOUR <= now.hour < CLOSE_HOUR
        status = "We're open right now." if is_open else "We're currently closed."
        return f"{status} {base}"

    def menu(self) -> str:
        lines = ["I can help with questions like:"]
        lines += [f"  - {f['question']}" for f in self.faqs]
        return "\n".join(lines)

    # ---- main entry point
    def respond(self, raw: str) -> str:
        text = normalize(raw)

        if not text:
            return "I didn't catch that. Could you type your question?"

        if EXIT_RE.match(text):
            self.state = State.EXIT
            return "Thanks for chatting. Goodbye!"

        # Answer to a previous "Did you mean ...?"
        if self.pending_suggestion and re.match(r"^(yes|yeah|yep|yup|sure|ok|okay|correct)\b", text):
            answer = self.pending_suggestion["answer"]
            self.pending_suggestion = None
            return answer
        if self.pending_suggestion and re.match(r"^(no|nope|nah)\b", text):
            self.pending_suggestion = None
            return "Sorry about that. Could you rephrase your question? Type 'help' to see what I can answer."
        self.pending_suggestion = None

        # Greeting (only as a whole short message, so "hi, what are your hours" still gets answered)
        if text in self.greetings:
            first_time = self.state is State.GREETING
            self.state = State.ACTIVE
            return (f"Hello! I'm {BOT_NAME}, your support assistant. How can I help you today?"
                    if first_time else "Hi again! What would you like to know?")

        self.state = State.ACTIVE  # any real question moves us out of GREETING

        if THANKS_RE.search(text) and len(text.split()) <= 4:
            return "You're welcome! Anything else I can help with?"

        if HELP_RE.search(text) and len(text.split()) <= 5:
            return self.menu()

        # Intent: business hours (regex rule, runs before generic FAQ matching)
        if HOURS_RE.search(text):
            return self.hours_reply(text)

        # Intent: FAQ lookup with confidence scoring
        faq, score = self.best_match(text)
        if faq and score >= ANSWER_THRESHOLD:
            return faq["answer"]
        if faq and score >= SUGGEST_THRESHOLD:
            self.pending_suggestion = faq
            return f"I'm not completely sure. Did you mean: \"{faq['question']}\" (yes/no)?"

        return ("Sorry, I don't have an answer for that yet. "
                "Try rephrasing, or type 'help' to see what I can answer.")


def main() -> None:
    # Uses the embedded FAQ_DATA; pass a JSON file path to override it.
    data = FAQ_DATA if len(sys.argv) < 2 else FAQBot._load(Path(sys.argv[1]))
    bot = FAQBot(data)
    print(f"{BOT_NAME}: Hi! Ask me a question. (type 'bye', 'exit' or 'quit' to leave)")
    while bot.state is not State.EXIT:
        try:
            user = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{BOT_NAME}: Goodbye!")
            break
        print(f"{BOT_NAME}: {bot.respond(user)}")


if __name__ == "__main__":
    main()

