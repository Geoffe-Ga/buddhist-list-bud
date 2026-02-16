# Project Overview — Buddhist Dhammas Knowledge Graph

## Architecture

This project models Theravada Buddhist doctrine as a **fractal knowledge graph** stored in MongoDB. The key insight: Buddhist teachings are hierarchically interconnected — each concept can "zoom in" to reveal deeper layers of teaching.

### The Fractal Pattern

```
Four Noble Truths (ROOT LIST)
  └─ 4. There is a Path (DHAMMA)
      └─ Noble Eightfold Path (LIST — downstream from "There is a Path")
          └─ Right Concentration (DHAMMA)
              └─ Five Hindrances (LIST — downstream from "Right Concentration")
                  └─ Sensual Desire (DHAMMA)
```

Each transition from dhamma → list is a "fractal zoom in." Each transition from list → parent dhamma is a "fractal zoom out."

## Data Model

### Two Collections

**`lists`** — Named groups of teachings (containers):
- `name`, `pali_name`, `slug` — identity
- `children[]` — ObjectId refs to dhammas in this list
- `upstream_from[]` — which dhamma you zoomed into to reach this list
- `item_count` — how many children

**`dhammas`** — Individual teachings (items):
- `name`, `pali_name`, `slug` — identity
- `parent_list_id` — which list contains this dhamma
- `position_in_list` — ordering within the parent list
- `essay` — 150-300 word beginner-friendly explanation
- `downstream[]` — lists that this dhamma expands into (zoom in)
- `cross_references[]` — same concept in different lists

### Three Relationship Types

1. **Parent-Child (Containment)**: A dhamma belongs to a list. Bidirectional via `dhamma.parent_list_id` and `list.children[]`.

2. **Upstream-Downstream (Fractal Zoom)**: A dhamma expands into a downstream list. This is the fractal navigation pattern — clicking "Right Concentration" zooms you into "Five Hindrances."

3. **Cross-References**: The same Pali concept appearing in different lists. For example, "Upekkha" (equanimity) is both a Brahma Vihara and a Factor of Awakening.

**Critical Rule**: Children are NEVER downstream from their own parent list. Containment and zoom are distinct relationships.

## Why These Design Decisions?

### Separate Collections (lists vs dhammas)
Lists and dhammas have different schemas and different query patterns. Keeping them separate makes queries cleaner and indexes more efficient. The alternative (a single `nodes` collection with a `type` field) would require type-checking in every query.

### Slugs → ObjectIds (Two-Pass Insert)
During parsing, we can't reference documents that don't exist yet. Slugs act as stable temporary IDs. After inserting all documents, a final pass replaces slugs with real ObjectIds. This solves the circular reference problem elegantly.

### Separate Essay Generation
Essays are expensive (~$0.50-1.00 API cost) and slow (~10-15 min). Keeping them as separate markdown files means you can re-seed the database without regenerating essays, version-control essays independently, and review/edit essays before they enter the database.

### The `ref_type` Field
MongoDB ObjectIds don't carry type information. When a reference could point to either a list or a dhamma, we need `ref_type` to know which collection to query:
```javascript
{ ref_id: ObjectId("..."), ref_type: "list" }   // query db.lists
{ ref_id: ObjectId("..."), ref_type: "dhamma" }  // query db.dhammas
```

## Expected Scale

- ~15-20 lists
- ~150-200 dhammas
- ~500-1000 relationships
- Database size: < 5MB

## File Structure

```
buddhist-list-bud/
├── docker-compose.yml           # MongoDB 7.x container
├── requirements.txt             # Python dependencies
├── .env.example                 # API key template
├── .gitignore                   # Git exclusions
├── seed_db.py                   # Parse spreadsheet → MongoDB
├── generate_essays.py           # AI essay generation (Claude Sonnet)
├── validate_db.py               # Data integrity checks
├── query_examples.py            # Demo queries
├── check_setup.py               # Environment verification
├── QUICKSTART.md                # Setup instructions
├── PROJECT_OVERVIEW.md          # This file
├── buddhist_list_bud_content_v1.xlsx  # Source data
└── data/
    └── essays/                  # Generated markdown essays
```
