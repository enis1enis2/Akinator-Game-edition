# Tests

This directory contains the test suite for Guessly.

## Running Tests

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run specific test module
python run_tests.py tests/test_engine.py

# Run specific test class
python run_tests.py tests/test_engine.py::TestEngineAnswer

# Run with coverage
python run_tests.py --cov

# Run only fast tests
python run_tests.py -m "not slow"
```

## Test Structure

- **`conftest.py`** — Shared pytest fixtures
- **`test_engine.py`** — Core engine unit tests
- **`test_app.py`** — Flask API integration tests
- **`test_database.py`** — Database loading/saving tests
- **`test_prediction.py`** — Prediction accuracy and constant-answer entity tests

## Writing New Tests

1. Create a new file named `test_*.py` in this directory
2. Use the fixtures from `conftest.py` (e.g., `engine`, `database`, `db_path`)
3. Follow the existing naming conventions: `Test<Component>` classes, `test_<behavior>` methods
4. Run `python run_tests.py` to verify
