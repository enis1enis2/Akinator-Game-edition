#!/usr/bin/env python3
"""
Guessly Trainer — CLI tool to expand and refine the database.

Commands:
  python trainer.py list [--category <cat>]
  python trainer.py add-entity
  python trainer.py add-question
  python trainer.py learn <entity_name>
  python trainer.py stats
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from engine import load_database, save_database, Entity, Question

DB_PATH = Path(__file__).parent / "database.json"

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_data():
    entities, questions = load_database(DB_PATH)
    return entities, questions


def cmd_list(args: list[str]) -> int:
    entities, questions = load_data()
    cat_filter = None
    if args and args[0] == "--category":
        cat_filter = args[1].lower() if len(args) > 1 else None

    print(f"\n{BOLD}Questions ({len(questions)} total):{RESET}")
    for i, (qid, q) in enumerate(questions.items(), 1):
        print(f"  {i:3d}. [{qid}] {q.text}")

    filtered = entities
    if cat_filter:
        filtered = [e for e in entities if e.category.lower() == cat_filter]

    print(f"\n{BOLD}Entities ({len(entities)} total, {len(filtered)} shown):{RESET}")
    for e in filtered:
        print(f"  - {e.name} ({e.category}) [{len(e.probs)} traits]")
    return 0


def cmd_add_entity(_: list[str]) -> int:
    entities, questions = load_data()
    q_map = {q.id: q for q in questions}

    name = input("Entity name: ").strip()
    if not name:
        print("Name required.")
        return 1
    entity_id = name.lower().replace(" ", "_")
    if entity_id in [e.id for e in entities]:
        print(f"Entity '{name}' already exists (id={entity_id}).")
        return 1

    category = input("Category (video game / movie / anime / comic / tv / etc): ").strip() or "unknown"
    aliases = input("Aliases (comma separated, optional): ").strip()
    alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases else []
    notes = input("Notes (optional): ").strip()

    print(f"\nAvailable questions ({len(q_map)} total). Enter probabilities for each.")
    print("Use 1.0=yes, 0.85=probably, 0.5=unknown, 0.15=probably not, 0.0=no")
    print("Leave blank to skip (defaults to 0.5).\n")

    probs = {}
    for qid, q in q_map.items():
        val = input(f"  [{qid}] {q.text}: ").strip()
        if not val:
            continue
        try:
            v = float(val)
            if 0.0 <= v <= 1.0:
                probs[qid] = v
            else:
                print(f"    {RED}Ignored out of range.{RESET}")
        except ValueError:
            print(f"    {RED}Ignored invalid input.{RESET}")

    entity = Entity(id=entity_id, name=name, category=category, probs=probs, aliases=alias_list, notes=notes)
    entities.append(entity)
    save_database(DB_PATH, entities, questions)
    print(f"\n{GREEN}Added '{name}' with {len(probs)} traits.{RESET}")
    return 0


def cmd_add_question(_: list[str]) -> int:
    entities, questions = load_data()
    text = input("Question text: ").strip()
    if not text:
        print("Question text required.")
        return 1

    existing_ids = set(questions.keys())
    base_id = text.lower().replace(" ", "_").replace("?", "").replace("'", "")[:40]
    qid = base_id
    counter = 1
    while qid in existing_ids:
        qid = f"{base_id}_{counter}"
        counter += 1

    questions[qid] = Question(id=qid, text=text)
    save_database(DB_PATH, entities, questions)
    print(f"{GREEN}Added question [{qid}]: {text}{RESET}")
    return 0


def cmd_learn(args: list[str]) -> int:
    if not args:
        print("Usage: python trainer.py learn <entity_name> [--answers yes,no,...]")
        return 1

    entities, questions = load_data()
    name = " ".join(args).strip()
    entity_id = name.lower().replace(" ", "_")

    target = None
    for e in entities:
        if e.id == entity_id or e.name.lower() == name.lower():
            target = e
            break

    if target is None:
        print(f"Entity '{name}' not found. Use add-entity first.")
        return 1

    print(f"Learning for: {target.name}")
    print("Enter answers for each question in format: qid=yes|no|probably|probably_not|dont_know")
    print("Leave blank to skip.\n")

    q_map = {q.id: q for q in questions}
    for qid, q in q_map.items():
        raw = input(f"  [{qid}] {q.text}: ").strip()
        if not raw:
            continue
        ans = raw.lower()
        if ans in ("yes", "probably"):
            target.probs[qid] = min(1.0, target.probs.get(qid, 0.5) + 0.2)
        elif ans in ("no", "probably_not"):
            target.probs[qid] = max(0.0, target.probs.get(qid, 0.5) - 0.2)
        elif ans == "dont_know":
            pass
        else:
            print(f"    {RED}Invalid answer, skipped.{RESET}")

    save_database(DB_PATH, entities, questions)
    print(f"\n{GREEN}Updated probabilities for '{target.name}'.{RESET}")
    return 0


def cmd_stats(_: list[str]) -> int:
    entities, questions = load_data()
    print(f"\n{BOLD}Database Stats:{RESET}")
    print(f"  Entities: {len(entities)}")
    print(f"  Questions: {len(questions)}")

    cats = {}
    for e in entities:
        cats[e.category] = cats.get(e.category, 0) + 1
    print("\n  By category:")
    for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        print(f"    {cat}: {count}")

    coverage = []
    for e in entities:
        coverage.append(len(e.probs))
    avg = sum(coverage) / len(coverage) if coverage else 0
    print(f"\n  Avg traits per entity: {avg:.1f}")
    print(f"  Max traits: {max(coverage) if coverage else 0}")
    print(f"  Min traits: {min(coverage) if coverage else 0}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 0

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "list": cmd_list,
        "add-entity": cmd_add_entity,
        "add-question": cmd_add_question,
        "learn": cmd_learn,
        "stats": cmd_stats,
    }

    fn = commands.get(cmd)
    if fn is None:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1

    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
