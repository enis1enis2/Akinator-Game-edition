"""
Development helper: validate the seed database for common issues.

Checks:
- Duplicate entity IDs
- Duplicate question IDs
- Entities with no probability data
- Probability values outside [0, 1]
- Question IDs referenced by entities that don't exist in the question bank
- Entities with too few traits (possible data quality issue)
- Average probability bias (entities that are too "yes-heavy" or "no-heavy")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database.json"


def load_db():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_duplicate_entity_ids(data):
    ids = [e["id"] for e in data["entities"]]
    duplicates = [eid for eid in set(ids) if ids.count(eid) > 1]
    if duplicates:
        print(f"[ERROR] Duplicate entity IDs: {duplicates}")
        return False
    print("[OK] No duplicate entity IDs")
    return True


def check_duplicate_question_ids(data):
    ids = [q["id"] for q in data["questions"]]
    duplicates = [qid for qid in set(ids) if ids.count(qid) > 1]
    if duplicates:
        print(f"[ERROR] Duplicate question IDs: {duplicates}")
        return False
    print("[OK] No duplicate question IDs")
    return True


def check_prob_ranges(data):
    valid = True
    for e in data["entities"]:
        for qid, prob in e.get("probs", {}).items():
            if not 0.0 <= prob <= 1.0:
                print(f"[ERROR] Entity {e['id']} has invalid probability {prob} for {qid}")
                valid = False
    if valid:
        print("[OK] All probability values in [0, 1]")
    return valid


def check_orphan_prob_keys(data):
    valid_ids = {q["id"] for q in data["questions"]}
    valid = True
    for e in data["entities"]:
        for qid in e.get("probs", {}):
            if qid not in valid_ids:
                print(f"[ERROR] Entity {e['id']} references unknown question ID: {qid}")
                valid = False
    if valid:
        print("[OK] All probability keys reference valid questions")
    return valid


def check_entity_coverage(data):
    warnings = []
    for e in data["entities"]:
        traits = len(e.get("probs", {}))
        if traits == 0:
            warnings.append(f"[WARN] Entity {e['id']} has no probability data")
        elif traits < 5:
            warnings.append(f"[WARN] Entity {e['id']} has only {traits} traits")
    if warnings:
        for w in warnings:
            print(w)
    else:
        print("[OK] All entities have reasonable trait coverage")
    return len(warnings) == 0


def check_probability_bias(data):
    warnings = []
    for e in data["entities"]:
        probs = list(e.get("probs", {}).values())
        if not probs:
            continue
        avg = sum(probs) / len(probs)
        if avg > 0.8:
            warnings.append(f"[WARN] Entity {e['id']} has high yes-bias: avg={avg:.2f}")
        elif avg < 0.2:
            warnings.append(f"[WARN] Entity {e['id']} has high no-bias: avg={avg:.2f}")
    if warnings:
        for w in warnings[:10]:  # Limit output
            print(w)
        if len(warnings) > 10:
            print(f"... and {len(warnings) - 10} more warnings")
    else:
        print("[OK] No extreme probability bias detected")
    return len(warnings) == 0


def main():
    print(f"Validating database: {DB_PATH}")
    print(f"Entities: {len(load_db()['entities'])}")
    print(f"Questions: {len(load_db()['questions'])}")
    print()

    data = load_db()
    results = [
        check_duplicate_entity_ids(data),
        check_duplicate_question_ids(data),
        check_prob_ranges(data),
        check_orphan_prob_keys(data),
        check_entity_coverage(data),
        check_probability_bias(data),
    ]

    print()
    if all(results):
        print("Validation passed.")
        sys.exit(0)
    else:
        print("Validation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
