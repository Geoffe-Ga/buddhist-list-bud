# Quick Start Guide

Get the Buddhist Dhammas knowledge graph running in 5 minutes.

## Prerequisites

- Docker Desktop (for MongoDB)
- Python 3.8+
- An Anthropic API key (only needed for essay generation)

## Setup

```bash
# 1. Check your environment
python check_setup.py

# 2. Start MongoDB
docker compose up -d

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. (Optional) Generate essays — costs ~$0.50-1.00
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python generate_essays.py

# 5. Seed the database
python seed_db.py

# 6. Validate everything
python validate_db.py

# 7. Explore!
python query_examples.py
```

## What Each Script Does

| Script | Purpose | Safe to re-run? |
|--------|---------|-----------------|
| `check_setup.py` | Verifies prerequisites | Yes (read-only) |
| `generate_essays.py` | Creates essay files via Claude API | Yes (skips existing) |
| `seed_db.py` | Parses spreadsheet, seeds MongoDB | Yes (drops + recreates) |
| `validate_db.py` | Checks data integrity | Yes (read-only) |
| `query_examples.py` | Demonstrates query patterns | Yes (read-only) |

## After Spreadsheet Changes

```bash
python seed_db.py        # Re-parse and re-seed
python validate_db.py    # Verify integrity
```

## Troubleshooting

**MongoDB won't connect**: Make sure Docker is running and the container is up:
```bash
docker compose ps
docker compose logs mongodb
```

**Missing Python packages**: Install them:
```bash
pip install -r requirements.txt
```

**Essays not loading**: Run `generate_essays.py` first, then re-run `seed_db.py`.
