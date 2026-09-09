"""
Guessly engine — a 20-questions style guessing game core.

How it works:
- Each entity has a probability vector over a shared question bank:
  P(answer=yes | entity) for every question.
- We maintain a running probability distribution over all candidate
  entities, initialized uniformly.
- After each answer, we do a Bayesian-style update: entities whose
  stored probability for that question matches the player's answer
  get boosted; mismatches get suppressed.
- The next question asked is the one with the highest expected
  information gain (closest to splitting the remaining probability
  mass in half) among questions not yet asked.
- We stop and guess once the top candidate's probability crosses a
  confidence threshold, or after a max number of questions.

No ML libraries required — this is a self-contained scoring engine.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

# Answer values and how they map onto the [0, 1] "yes-ness" scale.
# "probably"/"probably not" are soft signals; "dont_know" contributes
# no information and is simply skipped in the update step.
ANSWER_WEIGHTS = {
    "yes": 1.0,
    "probably": 0.75,
    "dont_know": None,  # handled specially: no update
    "probably_not": 0.25,
    "no": 0.0,
}

VALID_ANSWERS = tuple(ANSWER_WEIGHTS.keys())

DEFAULT_CONFIDENCE_THRESHOLD = 0.55
DEFAULT_MAX_QUESTIONS = 25
MIN_QUESTIONS_BEFORE_GUESS = 6
LIKELIHOOD_SHARPNESS = 2.5
UNKNOWN_PENALTY = 0.85
MARGIN_RATIO = 1.4


@dataclass
class Entity:
    id: str
    name: str
    category: str
    # question_id -> probability in [0,1] that the true answer is "yes"
    probs: dict[str, float]
    aliases: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Question:
    id: str
    text: str


class GuesslyEngine:
    def __init__(self, entities: list[Entity], questions: dict[str, Question]):
        self.entities = {e.id: e for e in entities}
        self.questions = questions
        self.reset()

    # ---------- session lifecycle ----------

    def reset(self) -> None:
        n = len(self.entities)
        self.belief: dict[str, float] = {eid: 1.0 / n for eid in self.entities}
        self.asked: list[str] = []
        self.history: list[tuple[str, str]] = []  # (question_id, answer)
        self.eliminated: set[str] = set()

    def load_state(
        self, belief: dict[str, float], asked: list[str], history: list[tuple[str, str]]
    ) -> None:
        self.belief = dict(belief)
        self.asked = list(asked)
        self.history = list(history)
        self.eliminated = set()

    # ---------- question selection ----------

    def _entropy_score(self, qid: str) -> float:
        """
        Expected information gain proxy: how close does this question
        come to splitting the *remaining probability mass* in half?
        Score is highest (closest to 0 distance from 0.5) for the most
        discriminating question among live candidates.
        """
        yes_mass = 0.0
        total_mass = 0.0
        for eid, p in self.belief.items():
            if eid in self.eliminated:
                continue
            ent_prob = self.entities[eid].probs.get(qid)
            if ent_prob is None:
                continue
            yes_mass += p * ent_prob
            total_mass += p
        if total_mass <= 0:
            return -1.0
        fraction_yes = yes_mass / total_mass
        # Closer to 0.5 => higher score. Distance in [0, 0.5].
        return 0.5 - abs(0.5 - fraction_yes)

    def next_question(self) -> Question | None:
        candidates = [qid for qid in self.questions if qid not in self.asked]
        if not candidates:
            return None
        live_candidates = [
            qid
            for qid in candidates
            if any(
                eid not in self.eliminated
                and self.entities[eid].probs.get(qid) is not None
                for eid in self.belief
            )
        ]
        if not live_candidates:
            return None
        scored = sorted(live_candidates, key=self._entropy_score, reverse=True)
        top_n = scored[:5] if len(scored) >= 5 else scored
        top_scores = [self._entropy_score(q) for q in top_n]
        best = max(top_scores)
        near_best = [q for q, s in zip(top_n, top_scores) if s >= best - 0.02]
        chosen = random.choice(near_best)
        return self.questions[chosen]

    def _likelihood(self, ent_prob: float | None, weight: float) -> float:
        """
        Compute how likely this entity is to produce the given answer.
        Uses a sharper-than-linear curve to better discriminate between
        strong matches and weak matches.
        """
        if ent_prob is None:
            return UNKNOWN_PENALTY
        distance = abs(ent_prob - weight)
        return max(0.02, 1.0 - LIKELIHOOD_SHARPNESS * distance * distance)

    def answer(self, question_id: str, answer: str) -> None:
        if answer not in VALID_ANSWERS:
            raise ValueError(f"Invalid answer: {answer}")
        self.asked.append(question_id)
        self.history.append((question_id, answer))

        weight = ANSWER_WEIGHTS[answer]
        if weight is None:  # dont_know: treat as neutral uncertainty
            weight = 0.5

        updated = {}
        total = 0.0
        for eid, p in self.belief.items():
            if eid in self.eliminated:
                updated[eid] = 0.0
                continue
            ent_prob = self.entities[eid].probs.get(question_id)
            likelihood = self._likelihood(ent_prob, weight)
            new_p = p * likelihood
            updated[eid] = new_p
            total += new_p

        if total <= 0:
            return  # avoid dividing by zero; keep old belief
        self.belief = {eid: v / total for eid, v in updated.items()}

    def eliminate(self, entity_id: str) -> None:
        """Remove an entity from consideration (used after a wrong guess)."""
        self.eliminated.add(entity_id)
        self.belief.pop(entity_id, None)
        total = sum(self.belief.values())
        if total > 0:
            self.belief = {k: v / total for k, v in self.belief.items()}

    # ---------- guessing ----------

    def top_candidates(self, n: int = 3) -> list[tuple[Entity, float]]:
        ranked = sorted(self.belief.items(), key=lambda kv: kv[1], reverse=True)
        return [
            (self.entities[eid], p) for eid, p in ranked[:n] if eid in self.entities
        ]

    def should_guess(
        self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ) -> bool:
        if len(self.asked) < MIN_QUESTIONS_BEFORE_GUESS:
            return False
        top = self.top_candidates(2)
        if not top or len(top) < 2:
            return False
        best_prob = top[0][1]
        second_prob = top[1][1]
        # Require both absolute confidence and a clear margin over the runner-up.
        return (
            best_prob >= confidence_threshold
            and best_prob >= second_prob * MARGIN_RATIO
        )

    def is_exhausted(self, max_questions: int = DEFAULT_MAX_QUESTIONS) -> bool:
        return (
            len(self.asked) >= max_questions
            or not any(qid not in self.asked for qid in self.questions)
            or not any(eid not in self.eliminated for eid in self.belief)
        )


# ---------- data loading ----------


def load_database(path: str | Path) -> tuple[list[Entity], dict[str, Question]]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    questions = {
        q["id"]: Question(id=q["id"], text=q["text"]) for q in data["questions"]
    }
    entities = [
        Entity(
            id=e["id"],
            name=e["name"],
            category=e.get("category", "unknown"),
            probs=e["probs"],
            aliases=e.get("aliases", []),
            notes=e.get("notes", ""),
        )
        for e in data["entities"]
    ]
    return entities, questions


def save_database(
    path: str | Path, entities: list[Entity], questions: dict[str, Question]
) -> None:
    path = Path(path)
    data = {
        "questions": [{"id": q.id, "text": q.text} for q in questions.values()],
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "category": e.category,
                "aliases": e.aliases,
                "notes": e.notes,
                "probs": e.probs,
            }
            for e in entities
        ],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
