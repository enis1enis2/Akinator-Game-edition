"""
Development helper: suggest new questions that would best distinguish
between entities in the database.

Uses entropy-based scoring to find questions that would split the remaining
probability mass most evenly if they were added to the question bank.
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


def compute_entropy_score(entities, question_scores):
    """
    question_scores: dict mapping entity_id -> float in [0,1]
    Higher score = more likely yes.
    """
    yes_mass = 0.0
    total_mass = 0.0
    for e in entities:
        prob = question_scores.get(e["id"], 0.5)
        yes_mass += prob
        total_mass += 1.0
    if total_mass <= 0:
        return 0.0
    fraction_yes = yes_mass / total_mass
    return 0.5 - abs(0.5 - fraction_yes)


def suggest_questions(data):
    print("=" * 70)
    print("QUESTION SUGGESTION ENGINE")
    print("=" * 70)

    entities = data["entities"]
    existing_q_texts = {q["text"].lower().strip() for q in data["questions"]}

    # Generate candidate question templates based on entity attributes
    templates = [
        ("Does this character have superhuman strength or power?", lambda e: e.get("probs", {}).get("q_strength_focus", 0.5)),
        ("Is this character known for their intelligence or tech skills?", lambda e: e.get("probs", {}).get("q_intelligence_focus", 0.5)),
        ("Does this character wear a distinctive costume?", lambda e: e.get("probs", {}).get("q_wears_cape_or_costume", 0.5)),
        ("Is this character primarily a villain?", lambda e: e.get("probs", {}).get("q_villain", 0.5)),
        ("Is this character from a recent release (post-2010)?", lambda e: e.get("probs", {}).get("q_recent_character", 0.5)),
        ("Does this character have a iconic color scheme?", lambda e: e.get("probs", {}).get("q_iconic_color", 0.5)),
        ("Is this character part of a team or group?", lambda e: e.get("probs", {}).get("q_part_of_team", 0.5)),
        ("Does this character have a love interest in their story?", lambda e: e.get("probs", {}).get("q_has_love_interest", 0.5)),
        ("Is this character silent or minimally voiced?", lambda e: e.get("probs", {}).get("q_silent_protagonist", 0.5)),
        ("Does this character have a sidekick or companion?", lambda e: e.get("probs", {}).get("q_has_sidekick", 0.5)),
    ]

    scores = []
    for text, scorer in templates:
        if text.lower() in existing_q_texts:
            continue
        question_scores = {}
        for e in entities:
            question_scores[e["id"]] = scorer(e)
        score = compute_entropy_score(entities, question_scores)
        scores.append((score, text))

    scores.sort(key=lambda x: x[0], reverse=True)

    print("\nSuggested new questions (by discrimination power):\n")
    for i, (score, text) in enumerate(scores[:10], 1):
        print(f"  {i:2d}. [score={score:.3f}] {text}")

    print(f"\nExisting questions: {len(data['questions'])}")
    print(f"Entities: {len(entities)}")


def find_gap_analysis(data):
    print("\n" + "=" * 70)
    print("GAP ANALYSIS")
    print("=" * 70)

    entities = data["entities"]
    questions = {q["id"]: q["text"] for q in data["questions"]}

    # Count how many entities have data for each question
    coverage = defaultdict(int)
    for e in entities:
        for qid in e.get("probs", {}):
            coverage[qid] += 1

    # Find questions with low coverage
    low_coverage = [(qid, questions.get(qid, qid), count) for qid, count in coverage.items() if count < 10]
    low_coverage.sort(key=lambda x: x[2])

    if low_coverage:
        print("\nQuestions with low entity coverage (< 10 entities):")
        for qid, text, count in low_coverage[:15]:
            print(f"  [{count:2d}] [{qid}] {text[:60]}")
    else:
        print("\nAll questions have reasonable coverage.")


def main():
    data = load_db()
    suggest_questions(data)
    find_gap_analysis(data)


if __name__ == "__main__":
    main()
