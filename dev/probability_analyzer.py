"""
Development helper: analyze probability distributions in the database.

Reports:
- Per-entity: min/max/avg probability, trait count
- Per-question: how many entities answer yes/no/neutral
- Top entities by yes-bias and no-bias
- Question discrimination power (ability to split entities)
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database.json"


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def analyze_entities(data):
    print("=" * 60)
    print("ENTITY ANALYSIS")
    print("=" * 60)

    stats = []
    for e in data["entities"]:
        probs = list(e.get("probs", {}).values())
        if not probs:
            continue
        avg = sum(probs) / len(probs)
        stats.append((avg, e["id"], e["name"], len(probs), min(probs), max(probs)))

    stats.sort(key=lambda x: x[0], reverse=True)

    print("\nTop 10 most yes-biased entities:")
    for avg, eid, name, count, mn, mx in stats[:10]:
        print(f"  {name:30s} avg={avg:.2f} min={mn:.2f} max={mx:.2f} traits={count}")

    print("\nTop 10 most no-biased entities:")
    for avg, eid, name, count, mn, mx in stats[-10:]:
        print(f"  {name:30s} avg={avg:.2f} min={mn:.2f} max={mx:.2f} traits={count}")

    print(f"\nTotal entities analyzed: {len(stats)}")


def analyze_questions(data):
    print("\n" + "=" * 60)
    print("QUESTION ANALYSIS")
    print("=" * 60)

    q_map = {q["id"]: q["text"] for q in data["questions"]}

    for qid, text in q_map.items():
        yes_count = 0
        no_count = 0
        neutral_count = 0
        for e in data["entities"]:
            prob = e.get("probs", {}).get(qid)
            if prob is None:
                neutral_count += 1
            elif prob >= 0.7:
                yes_count += 1
            elif prob <= 0.3:
                no_count += 1
            else:
                neutral_count += 1

        total = yes_count + no_count + neutral_count
        if total == 0:
            continue
        discrimination = max(yes_count, no_count) / total
        print(f"  {text[:50]:50s} yes={yes_count:3d} no={no_count:3d} neutral={neutral_count:3d} disc={discrimination:.2f}")


def analyze_coverage(data):
    print("\n" + "=" * 60)
    print("COVERAGE ANALYSIS")
    print("=" * 60)

    trait_counts = [len(e.get("probs", {})) for e in data["entities"]]
    if not trait_counts:
        print("No entities found")
        return

    print(f"Average traits per entity: {sum(trait_counts) / len(trait_counts):.1f}")
    print(f"Max traits: {max(trait_counts)}")
    print(f"Min traits: {min(trait_counts)}")

    # Find questions that are rarely used
    q_usage = defaultdict(int)
    for e in data["entities"]:
        for qid in e.get("probs", {}):
            q_usage[qid] += 1

    q_map = {q["id"]: q["text"] for q in data["questions"]}
    rarely_used = [(qid, q_map.get(qid, qid), count) for qid, count in q_usage.items() if count < 5]
    rarely_used.sort(key=lambda x: x[2])

    print("\nRarely used questions (< 5 entities):")
    for qid, text, count in rarely_used[:10]:
        print(f"  [{qid}] {text[:50]} - used by {count} entities")


def main():
    data = load_db()
    analyze_entities(data)
    analyze_questions(data)
    analyze_coverage(data)


if __name__ == "__main__":
    main()
