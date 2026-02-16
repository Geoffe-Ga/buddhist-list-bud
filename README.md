# Buddhist Dhammas — Fractal Knowledge Graph

A MongoDB database that models Theravada Buddhist doctrine as a fractal knowledge graph. Each teaching can "zoom in" to reveal deeper layers of interconnected concepts.

```
Four Noble Truths
  └─ There is a Path
      └─ Noble Eightfold Path
          └─ Right Concentration
              └─ Five Hindrances
                  └─ Sensual Desire
```

## Quick Start

```bash
docker compose up -d              # Start MongoDB
pip install -r requirements.txt   # Install dependencies
python seed_db.py                 # Seed the database
python query_examples.py          # Explore the graph
```

See [QUICKSTART.md](QUICKSTART.md) for the full setup guide and [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for architecture details.

## Data Model

Two MongoDB collections connected by three relationship types:

- **`lists`** — Named groups of teachings (e.g., Noble Eightfold Path)
- **`dhammas`** — Individual teachings (e.g., Right Concentration)

Relationships: **parent-child** (containment), **upstream-downstream** (fractal zoom), and **cross-references** (same concept in different contexts).

## Scripts

| Script | Purpose |
|--------|---------|
| `check_setup.py` | Verify prerequisites |
| `generate_essays.py` | Generate essays via Claude API (~$0.50-1.00) |
| `seed_db.py` | Parse spreadsheet and seed MongoDB |
| `validate_db.py` | Check data integrity |
| `query_examples.py` | Demonstrate query patterns |

## Development

This project was scaffolded with [Start Green Stay Green](https://github.com/Geoffe-Ga/start_green_stay_green) and includes quality tooling (pytest, ruff, black, mypy, bandit). See `scripts/` for quality check runners.

## License

MIT
