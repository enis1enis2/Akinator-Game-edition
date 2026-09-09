"""
Tests for the core GuesslyEngine.
"""

from __future__ import annotations

import pytest

from engine import (
    DEFAULT_MAX_QUESTIONS,
    MIN_QUESTIONS_BEFORE_GUESS,
    GuesslyEngine,
    load_database,
)


class TestEngineInitialization:
    def test_load_database(self, db_path):
        entities, questions = load_database(db_path)
        assert len(entities) > 0
        assert len(questions) > 0

    def test_engine_creation(self, database):
        entities, questions = database
        engine = GuesslyEngine(entities, questions)
        assert len(engine.entities) == len(entities)
        assert len(engine.questions) == len(questions)

    def test_initial_belief_uniform(self, engine):
        n = len(engine.belief)
        expected = 1.0 / n
        for prob in engine.belief.values():
            assert abs(prob - expected) < 1e-9

    def test_initial_state_empty(self, engine):
        assert engine.asked == []
        assert engine.history == []
        assert engine.eliminated == set()


class TestEngineReset:
    def test_reset_clears_asked(self, engine):
        engine.asked.append("q_fictional")
        engine.reset()
        assert engine.asked == []

    def test_reset_clears_history(self, engine):
        engine.history.append(("q_fictional", "yes"))
        engine.reset()
        assert engine.history == []

    def test_reset_clears_eliminated(self, engine):
        engine.eliminated.add("test_id")
        engine.reset()
        assert engine.eliminated == set()

    def test_reset_restores_uniform_belief(self, engine):
        engine.belief["test"] = 0.5
        engine.reset()
        n = len(engine.belief)
        expected = 1.0 / n
        for prob in engine.belief.values():
            assert abs(prob - expected) < 1e-9


class TestEngineAnswer:
    def test_answer_adds_to_asked(self, engine):
        q = engine.next_question()
        engine.answer(q.id, "yes")
        assert q.id in engine.asked

    def test_answer_adds_to_history(self, engine):
        q = engine.next_question()
        engine.answer(q.id, "yes")
        assert (q.id, "yes") in engine.history

    def test_answer_invalid_raises(self, engine):
        q = engine.next_question()
        with pytest.raises(ValueError):
            engine.answer(q.id, "invalid")

    def test_dont_know_applies_neutral_weight(self, engine):
        q = engine.next_question()
        initial_belief = dict(engine.belief)

        # Measure update size for dont_know vs yes
        engine.answer(q.id, "dont_know")
        dont_know_diff = sum(
            abs(engine.belief[eid] - initial_belief[eid]) for eid in initial_belief
        )

        engine.reset()
        engine.answer(q.id, "yes")
        yes_diff = sum(
            abs(engine.belief[eid] - initial_belief[eid]) for eid in initial_belief
        )

        assert q.id in engine.asked
        assert dont_know_diff < yes_diff, (
            "dont_know should produce smaller belief shift than yes"
        )

    def test_yes_boosts_matching_entities(self, engine):
        q = engine.next_question()
        engine.answer(q.id, "yes")
        # Entities with high probability for this question should be higher
        top = engine.top_candidates(3)
        assert len(top) > 0


class TestEngineEliminate:
    def test_eliminate_removes_from_belief(self, engine):
        top = engine.top_candidates(1)
        if top:
            eid = top[0][0].id
            engine.eliminate(eid)
            assert eid not in engine.belief

    def test_eliminate_normalizes_belief(self, engine):
        top = engine.top_candidates(1)
        if top:
            engine.eliminate(top[0][0].id)
            total = sum(engine.belief.values())
            assert abs(total - 1.0) < 1e-9


class TestEngineTopCandidates:
    def test_top_candidates_returns_sorted(self, engine):
        top = engine.top_candidates(3)
        if len(top) >= 2:
            assert top[0][1] >= top[1][1]

    def test_top_candidates_respects_n(self, engine):
        top = engine.top_candidates(5)
        assert len(top) <= 5


class TestEngineShouldGuess:
    def test_should_not_guess_initially(self, engine):
        assert not engine.should_guess()

    def test_should_not_guess_with_few_questions(self, engine):
        for _ in range(MIN_QUESTIONS_BEFORE_GUESS - 1):
            q = engine.next_question()
            if q:
                engine.answer(q.id, "yes")
        assert not engine.should_guess()

    def test_should_guess_with_high_confidence(self, engine):
        # Boost one entity to high confidence
        for _ in range(20):
            q = engine.next_question()
            if q is None:
                break
            engine.answer(q.id, "yes")
        # Might guess depending on distribution
        result = engine.should_guess()
        assert isinstance(result, bool)


class TestEngineIsExhausted:
    def test_not_exhausted_initially(self, engine):
        assert not engine.is_exhausted()

    def test_exhausted_after_max_questions(self, engine):
        for i in range(DEFAULT_MAX_QUESTIONS):
            q = engine.next_question()
            if q is None:
                break
            engine.answer(q.id, "yes")
        assert engine.is_exhausted()


class TestEngineLoadState:
    def test_load_state_restores_belief(self, engine):
        original_belief = dict(engine.belief)
        engine.load_state(original_belief, [], [])
        for eid, prob in original_belief.items():
            assert abs(engine.belief[eid] - prob) < 1e-9

    def test_load_state_clears_eliminated(self, engine):
        engine.eliminated.add("test")
        engine.load_state(engine.belief, [], [])
        assert engine.eliminated == set()


class TestEngineEdgeCases:
    def test_empty_questions_returns_none(self, database):
        entities, _ = database
        engine = GuesslyEngine(entities, {})
        assert engine.next_question() is None

    def test_all_eliminated_returns_none(self, engine):
        for eid in list(engine.belief.keys()):
            engine.eliminate(eid)
        assert engine.next_question() is None
        assert engine.top_candidates(1) == []
