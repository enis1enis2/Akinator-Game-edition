# Guessly — 20-Questions Game Engine

[![Bandit](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/bandit.yml/badge.svg)](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/bandit.yml)
[![Semgrep](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/semgrep.yml/badge.svg)](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/semgrep.yml)
[![OSV](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/osv-scanner.yml/badge.svg)](https://github.com/enis1enis2/Akinator-Game-edition/actions/workflows/osv-scanner.yml)

Akinator-style guessing game built around an entropy-based 20-questions engine. Think of a character from video games, movies, anime, or comics — the engine asks yes/no/probably questions and guesses who you’re thinking of.

No ML, no LLM, no GPU required. Just a probabilistic decision engine over a shared question bank, with a trainer tool and optional GitHub-backed crowd-learning.

## Play

### CLI

```bash
python play.py
```

### Web UI

```bash
python app.py
# Open http://127.0.0.1:5000
```

### GitHub Pages

Open `docs/index.html` directly, or serve the `docs/` folder via GitHub Pages. Connect GitHub once via OAuth Device Flow and learned entities auto-sync back to the repo.

## How It Works

- Each entity has a probability vector over a shared question bank.
- After each answer, the engine does a Bayesian-style belief update.
- The next question is chosen by expected information gain (entropy reduction).
- It stops and guesses once confidence crosses a threshold.
- When it fails, you can teach it the correct character and it updates from the session history.

## Tech Stack

- **Engine**: pure Python (`engine.py`) — stdlib only
- **CLI**: `play.py` — stdlib only
- **Trainer**: `trainer.py` — stdlib only
- **Web server**: Flask (`app.py`)
- **Static site**: vanilla JS port in `docs/index.html`
- **Database**: JSON (`database.json`) — 117 entities, 73 questions
- **Security scans**: Bandit, Semgrep, OSV Scanner

## Project Structure

```text
├── app.py                 # Flask web server
├── build_database.py      # Seed DB generator
├── build_gh_pages.py      # Static site builder
├── database.json          # Seed database
├── docs/
│   ├── github_config.json # Public GitHub sync config
│   └── index.html         # GitHub Pages build
├── engine.py              # Core guessing engine
├── play.py                # CLI game loop
├── questions.json         # Question bank
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Flask template
└── trainer.py             # DB expansion / learning tool
```

## Trainer

```bash
# List entities/questions
python trainer.py list

# Add a new entity interactively
python trainer.py add-entity

# Add a new question
python trainer.py add-question

# Refine an existing entity from manual answers
python trainer.py learn "Entity Name"

# Stats
python trainer.py stats
```

## Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/your-idea`)
3. Add entities/questions via `trainer.py` or edit `build_database.py`
4. Run `python build_database.py` to regenerate `database.json`
5. Run `python build_gh_pages.py` to rebuild `docs/index.html`
6. Commit, push, and open a PR

## CI / Security

- **CodeQL** — enabled on Python
- **Bandit** — Python security linter
- **Semgrep** — Python + JS security patterns
- **OSV Scanner** — dependency vulnerability checks
- **Dependabot** — GitHub Actions updates

## License

MIT
