"""
Tests for database loading, saving, and integrity.
"""

from __future__ import annotations

import json

from engine import load_database, save_database


class TestDatabaseLoading:
    def test_load_database_returns_tuple(self, db_path):
        result = load_database(db_path)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_load_database_entities(self, db_path):
        entities, _ = load_database(db_path)
        assert len(entities) > 0
        for e in entities:
            assert isinstance(e.id, str)
            assert isinstance(e.name, str)
            assert isinstance(e.category, str)
            assert isinstance(e.probs, dict)

    def test_load_database_questions(self, db_path):
        _, questions = load_database(db_path)
        assert len(questions) > 0
        for q in questions.values():
            assert isinstance(q.id, str)
            assert isinstance(q.text, str)

    def test_all_prob_keys_are_valid_question_ids(self, db_path):
        entities, questions = load_database(db_path)
        valid_ids = set(questions.keys())
        for e in entities:
            for qid in e.probs:
                assert qid in valid_ids, f"Entity {e.id} has unknown question id: {qid}"

    def test_all_prob_values_in_range(self, db_path):
        entities, _ = load_database(db_path)
        for e in entities:
            for qid, prob in e.probs.items():
                assert 0.0 <= prob <= 1.0, (
                    f"Entity {e.id} has invalid prob {prob} for {qid}"
                )


class TestDatabaseSaving:
    def test_save_and_reload_roundtrip(self, db_path, tmp_path):
        entities, questions = load_database(db_path)
        out_path = tmp_path / "test_db.json"
        save_database(out_path, entities, questions)
        assert out_path.exists()

        entities2, questions2 = load_database(out_path)
        assert len(entities) == len(entities2)
        assert len(questions) == len(questions2)

    def test_save_preserves_probabilities(self, db_path, tmp_path):
        entities, questions = load_database(db_path)
        original_probs = dict(entities[0].probs)
        out_path = tmp_path / "test_db.json"
        save_database(out_path, entities, questions)
        entities2, _ = load_database(out_path)
        for qid, prob in original_probs.items():
            assert entities2[0].probs[qid] == prob

    def test_save_creates_valid_json(self, db_path, tmp_path):
        entities, questions = load_database(db_path)
        out_path = tmp_path / "test_db.json"
        save_database(out_path, entities, questions)
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "entities" in data
        assert "questions" in data


class TestDatabaseIntegrity:
    def test_no_duplicate_entity_ids(self, db_path):
        entities, _ = load_database(db_path)
        ids = [e.id for e in entities]
        assert len(ids) == len(set(ids))

    def test_no_duplicate_question_ids(self, db_path):
        _, questions = load_database(db_path)
        ids = list(questions.keys())
        assert len(ids) == len(set(ids))

    def test_all_entities_have_names(self, db_path):
        entities, _ = load_database(db_path)
        for e in entities:
            assert e.name.strip() != ""

    def test_all_questions_have_text(self, db_path):
        _, questions = load_database(db_path)
        for q in questions.values():
            assert q.text.strip() != ""
