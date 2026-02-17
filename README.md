# Buddhist Dharma Navigator

A fractal knowledge graph of Theravada Buddhist doctrine, presented as an interactive web application. Navigate through interconnected teachings — from the Four Noble Truths down to individual meditation factors — using a directional interface that mirrors the nested structure of the Dharma itself.

**Live:** [dharma.aptitude.guru](https://dharma.aptitude.guru)

```
Four Noble Truths
  └─ There is a Path
      └─ Noble Eightfold Path
          └─ Right Concentration
              └─ Five Hindrances
                  └─ Sensual Desire
```

## Features

- **Directional navigation** — move up, down, left, and right through the teaching hierarchy
- **Search** — find any list or dhamma by English or Pali name
- **AI-generated essays** — each teaching includes a contextual essay generated via Claude
- **Responsive design** — works on desktop and mobile
- **22 lists, 118 dhammas** — covering core Theravada doctrine

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python 3.12 |
| Database | MongoDB (Atlas) |
| Hosting | Railway |

## Local Development

```bash
# Prerequisites: Node 20+, Python 3.12+, MongoDB running locally

# Backend
pip install -r requirements.txt
python seed_db.py                        # Seed local MongoDB

# Frontend
cd frontend && npm install && npm run dev

# Backend (separate terminal)
python -m uvicorn backend.app.main:app --reload
```

## Quality Checks

```bash
bash scripts/check-all.sh   # Runs all 9 checks: ruff, black, mypy, bandit, pytest, etc.
```

- 24 tests, 93.95% backend coverage
- Linting (ruff), formatting (black), type checking (mypy), security scanning (bandit)

## Data Pipeline

1. `data/buddhist_dhammas.xlsx` — source spreadsheet with lists, dhammas, and relationships
2. `seed_db.py` — parses the spreadsheet, resolves slug-based references to ObjectIds, seeds MongoDB, and applies editorial corrections
3. `generate_essays.py` — generates essays for each dhamma via Claude API (stored in `data/essays/`)

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, SPA serving
│   │   ├── db.py            # MongoDB connection (Motor)
│   │   ├── models.py        # Pydantic models
│   │   └── routes/          # API endpoints
│   └── tests/               # pytest test suite
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Search bar, header, layout
│   │   ├── components/       # NavigationLayout
│   │   ├── api/              # API client functions
│   │   └── types.ts          # TypeScript interfaces
│   └── index.html
├── data/                     # Source spreadsheet and essays
├── scripts/                  # Quality check scripts
├── seed_db.py                # Database seeder
├── Dockerfile                # Multi-stage build for Railway
└── requirements.txt          # Python dependencies
```

## License

MIT
