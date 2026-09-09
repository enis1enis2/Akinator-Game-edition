"""
Tests for the Flask web application and API.
"""

from __future__ import annotations

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestFlaskRoutes:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Guessly" in resp.data

    def test_reset_returns_json(self, client):
        resp = client.post("/api/reset")
        assert resp.status_code == 200
        assert resp.content_type == "application/json"

    def test_reset_returns_valid_state(self, client):
        resp = client.post("/api/reset")
        data = resp.get_json()
        assert "status" in data
        assert data["status"] in ("guess", "question", "give_up")

    def test_answer_valid_json(self, client):
        client.post("/api/reset")
        resp = client.post(
            "/api/answer", json={"question_id": "q_fictional", "answer": "yes"}
        )
        assert resp.status_code == 200

    def test_answer_all_valid_answers(self, client):
        answers = ["yes", "probably", "dont_know", "probably_not", "no"]
        for answer in answers:
            client.post("/api/reset")
            resp = client.post(
                "/api/answer", json={"question_id": "q_fictional", "answer": answer}
            )
            assert resp.status_code == 200

    def test_answer_invalid_answer_returns_400(self, client):
        client.post("/api/reset")
        resp = client.post(
            "/api/answer", json={"question_id": "q_fictional", "answer": "invalid"}
        )
        assert resp.status_code == 400

    def test_answer_missing_fields_returns_400(self, client):
        client.post("/api/reset")
        resp = client.post("/api/answer", json={})
        assert resp.status_code == 400

    def test_answer_malformed_json_returns_400(self, client):
        client.post("/api/reset")
        resp = client.post(
            "/api/answer", data="not json", content_type="application/json"
        )
        assert resp.status_code == 400

    def test_learn_valid_name(self, client):
        resp = client.post("/api/learn", json={"name": "TestCharacter"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data

    def test_learn_empty_name_returns_400(self, client):
        resp = client.post("/api/learn", json={"name": ""})
        assert resp.status_code == 400

    def test_learn_malformed_json_returns_400(self, client):
        resp = client.post(
            "/api/learn", data="not json", content_type="application/json"
        )
        assert resp.status_code == 400


class TestFlaskErrorHandlers:
    def test_404_returns_json(self, client):
        resp = client.get("/nonexistent")
        assert resp.status_code == 404
        assert resp.content_type == "application/json"

    def test_405_returns_json(self, client):
        resp = client.get("/api/reset")
        assert resp.status_code == 405
        assert resp.content_type == "application/json"
