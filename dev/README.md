# Development Tools

This directory contains helper scripts for developing and maintaining the Guessly database and engine.

## Tools

### `seed_validator.py`

Validates the `database.json` seed file for common issues:

- Duplicate entity/question IDs
- Invalid probability values
- Orphan probability keys
- Low entity coverage
- Probability bias

**Usage:**

```bash
python dev/seed_validator.py
```

### `probability_analyzer.py`

Analyzes probability distributions in the database:

- Per-entity yes/no bias
- Question discrimination power
- Coverage statistics
- Rarely used questions

**Usage:**

```bash
python dev/probability_analyzer.py
```

### `entity_importer.py`

Bulk import entities from a JSON file into `database.json`.

**Input format:**

```json
[
  {
    "name": "Character Name",
    "category": "video game",
    "probs": {"q_fictional": 1.0, "q_human": 1.0},
    "aliases": ["alias1"],
    "notes": "Optional notes"
  }
]
```

**Usage:**

```bash
python dev/entity_importer.py path/to/entities.json
python dev/entity_importer.py path/to/entities.json --dry-run
```

### `question_suggester.py`

Suggests new questions that would best distinguish between entities based on entropy analysis.

**Usage:**

```bash
python dev/question_suggester.py
```

## Adding New Entities

1. Use `dev/entity_importer.py` for bulk imports
2. Or use `python trainer.py add-entity` for interactive addition
3. Run `python dev/seed_validator.py` to check for issues
4. Run `python build_database.py` to regenerate `database.json`
5. Run `python build_gh_pages.py` to rebuild the static site
