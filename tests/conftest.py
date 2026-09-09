"""
Shared pytest fixtures for Guessly tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import Entity, GuesslyEngine, Question, load_database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database.json"


@pytest.fixture(scope="session")
def db_path() -> Path:
    return DB_PATH


@pytest.fixture(scope="session")
def database(db_path: Path):
    entities, questions = load_database(db_path)
    return entities, questions


@pytest.fixture(scope="function")
def engine(database) -> GuesslyEngine:
    entities, questions = database
    return GuesslyEngine(entities, questions)


@pytest.fixture(scope="session")
def sample_entity() -> Entity:
    return Entity(
        id="test_entity",
        name="Test Entity",
        category="test",
        probs={"q_fictional": 1.0, "q_human": 0.5, "q_male": 0.0},
    )


@pytest.fixture(scope="session")
def sample_question() -> Question:
    return Question(id="q_fictional", text="Is this character fictional?")
