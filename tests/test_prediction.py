"""
Tests for constant-answer entities and prediction accuracy.
"""

from __future__ import annotations

import pytest

from engine import GuesslyEngine, load_database


class TestConstantAnswerEntities:
    @pytest.mark.parametrize(
        "answer,expected_id",
        [
            ("yes", "the_guy_that_always_press_yes"),
            ("probably", "the_guy_that_always_press_probably"),
            ("dont_know", "the_guy_that_always_press_dont_know"),
            ("probably_not", "the_guy_that_always_press_probably_not"),
            ("no", "the_guy_that_always_press_no"),
        ],
    )
    def test_constant_answer_matching(self, db_path, answer, expected_id):
        entities, questions = load_database(db_path)
        engine = GuesslyEngine(entities, questions)
        engine.reset()

        for _ in range(20):
            q = engine.next_question()
            if q is None:
                break
            engine.answer(q.id, answer)

        top = engine.top_candidates(1)
        assert len(top) > 0
        assert top[0][0].id == expected_id


class TestPredictionAccuracy:
    def test_yes_does_not_match_no_entity(self, db_path):
        entities, questions = load_database(db_path)
        engine = GuesslyEngine(entities, questions)
        engine.reset()

        for _ in range(20):
            q = engine.next_question()
            if q is None:
                break
            engine.answer(q.id, "yes")

        top = engine.top_candidates(1)
        assert top[0][0].id != "the_guy_that_always_press_no"

    def test_no_does_not_match_yes_entity(self, db_path):
        entities, questions = load_database(db_path)
        engine = GuesslyEngine(entities, questions)
        engine.reset()

        for _ in range(20):
            q = engine.next_question()
            if q is None:
                break
            engine.answer(q.id, "no")

        top = engine.top_candidates(1)
        assert top[0][0].id != "the_guy_that_always_press_yes"
