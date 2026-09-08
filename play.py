#!/usr/bin/env python3
"""
Guessly CLI — Terminal 20-questions guessing game.

Run: python play.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from engine import GuesslyEngine, load_database, Entity, Question, VALID_ANSWERS, DEFAULT_MAX_QUESTIONS, DEFAULT_CONFIDENCE_THRESHOLD

DB_PATH = Path(__file__).parent / "database.json"

# ANSI colors for terminal
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def prompt(text: str) -> str:
    return input(f"{CYAN}{text}{RESET} ").strip().lower()


def main() -> int:
    entities, questions = load_database(DB_PATH)
    engine = GuesslyEngine(entities, questions)

    print(f"\n{BOLD}{GREEN}========================================{RESET}")
    print(f"{BOLD}{GREEN}            GUESSLY v1.0                {RESET}")
    print(f"{BOLD}{GREEN}   Think of a game/pop-culture figure  {RESET}")
    print(f"{BOLD}{GREEN}========================================{RESET}\n")

    while True:
        engine.reset()
        print(f"\n{YELLOW}Think of a character from video games, movies, anime, or comics...{RESET}")
        print(f"{YELLOW}I will try to guess who it is in up to {DEFAULT_MAX_QUESTIONS} questions.{RESET}\n")

        while not engine.is_exhausted():
            q = engine.next_question()
            if q is None:
                break

            if engine.should_guess():
                break

            print(f"{BOLD}Q:{RESET} {q.text}")
            ans = prompt("([y]es / [p]robably / [d]on't know / [p]robably [n]ot / [n]o)")
            if ans not in VALID_ANSWERS:
                print(f"{RED}Invalid answer. Use yes, probably, dont_know, probably_not, no.{RESET}")
                continue
            engine.answer(q.id, ans)

        # Time to guess or give up
        top = engine.top_candidates(3)
        if not top:
            print(f"\n{RED}I have no candidates left. You win this round!{RESET}")
        else:
            best_entity, confidence = top[0]
            if confidence >= DEFAULT_CONFIDENCE_THRESHOLD:
                print(f"\n{BOLD}{GREEN}Is your character: {best_entity.name}?{RESET}")
                print(f"Confidence: {confidence * 100:.1f}%")
                resp = prompt("([y]es / [n]o)").strip()
                if resp in ("y", "yes", "yep", "yeah"):
                    print(f"{GREEN}I knew it! System victory.{RESET}")
                else:
                    print(f"{RED}You defeated me this time.{RESET}")
                    teach = prompt("Want to teach me who it was? ([y]es / [n]o)").strip()
                    if teach in ("y", "yes", "yeah", "yep"):
                        name = input("Enter the character name: ").strip()
                        if name:
                            learn_from_feedback(engine, name, DB_PATH)
            else:
                print(f"\n{RED}I give up! My best guess was {best_entity.name} ({confidence * 100:.1f}%).{RESET}")
                name = input("Who was your character? ").strip()
                if name:
                    learn_from_feedback(engine, name, DB_PATH)

        again = prompt("\nPlay again? ([y]es / [n]o)").strip()
        if again not in ("y", "yes", "yeah", "yep"):
            print(f"\n{GREEN}Thanks for playing!{RESET}\n")
            break

    return 0


def learn_from_feedback(engine: GuesslyEngine, name: str, db_path: Path) -> None:
    from engine import save_database
    entity_id = name.lower().replace(" ", "_")
    if entity_id in engine.entities:
        target = engine.entities[entity_id]
    else:
        target = Entity(id=entity_id, name=name, category="crowdsourced", probs={})
        engine.entities[entity_id] = target

    for qid, ans in engine.history:
        if ans in ("yes", "probably"):
            target.probs[qid] = min(1.0, target.probs.get(qid, 0.5) + 0.2)
        elif ans in ("no", "probably_not"):
            target.probs[qid] = max(0.0, target.probs.get(qid, 0.5) - 0.2)

    save_database(db_path, list(engine.entities.values()), engine.questions)
    print(f"{GREEN}Learned/updated '{name}'. Database saved.{RESET}")


if __name__ == "__main__":
    sys.exit(main())
