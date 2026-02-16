# Claude Code Prompt: Buddhist List Bud

## Copy everything below this line into Claude Code

---

# Role
You are a senior full-stack engineer pair-programming with a junior developer on an interview take-home project. Your job is to build a working, demoable application at every single stage — never leave the app in a broken state. Favor wiring up the full skeleton with stubs before filling in real logic. Explain your decisions as you go so the junior dev learns.

# Goal
Build a Buddhist Dharma navigation web app with:
- **React frontend** (Vite + React)
- **Python FastAPI backend**
- **MongoDB** (already running in Docker, pre-loaded with data)

The app lets users navigate interconnected Buddhist lists and dhammas through a directional UI with arrows on all four edges of the screen.

# Context

## Data Model (verify by exploring MongoDB first)
The MongoDB in the `buddhist-list-bud` project directory contains two object types:

- **Lists**: Collections of Buddhist observations (e.g., "The Four Noble Truths", "The Five Hindrances"). A List has child Dhammas.
- **Dhammas**: Individual items within a list (e.g., "Right Concentration"). A Dhamma belongs to a parent List and can be "upstream of" other Lists (creating cross-links between teachings).

### Relationships
- A **List** has ordered child **Dhammas** (one-to-many)
- A **Dhamma** can link downstream to other **Lists** (many-to-many cross-reference)
- Navigation is bidirectional: if Dhamma X links to List Y, then from List Y you can navigate back to Dhamma X

## UI Layout — Four-Edge Navigation

```
         ┌──────────────────────────────┐
         │    ▲ UP (prev dhamma item)    │  ← hidden when viewing a List
    ┌────┼──────────────────────────────┼────┐
    │ ◀  │                              │ ▶  │
    │    │                              │    │
    │ L  │      CONTENT AREA            │ R  │
    │ E  │                              │ I  │
    │ F  │   (List name + description   │ G  │
    │ T  │    or Dhamma details)        │ H  │
    │    │                              │ T  │
    │    │                              │    │
    └────┼──────────────────────────────┼────┘
         │   ▼ DOWN (next dhamma item)   │  ← hidden when viewing a List
         └──────────────────────────────┘
```

### Arrow Behaviors

| Edge | When Viewing a **List** | When Viewing a **Dhamma** |
|------|------------------------|--------------------------|
| **Up ▲** | Hidden | Previous sibling dhamma in same list |
| **Down ▼** | Hidden | Next sibling dhamma in same list |
| **Left ◀** | Upstream dhammas that link TO this list (can be multiple, stacked vertically) | Parent list(s) this dhamma belongs to |
| **Right ▶** | Child dhammas of this list (multiple, stacked vertically) | Downstream lists this dhamma connects to (can be multiple, stacked vertically) |

### Navigation Example
- **Five Hindrances (List)**: No up/down. Left arrow → "Right Concentration" dhamma (which links to this list). Right arrows → 5 individual hindrance dhammas.
- **Right Concentration (Dhamma in Noble Eightfold Path)**: Up → "Right Mindfulness". Down → (none, last item). Left → "Noble Eightfold Path" list. Right → "Five Hindrances" list, plus any other lists it connects to.

# Methodology: Tracer Code (Demoable at Every Stage)

**CRITICAL RULE**: The app must be runnable and demoable after completing each phase. Never leave it broken between phases. Wire the full path first with stubs, then replace stubs with real implementations one at a time.

## Phase 0 — Explore & Document the Data
**Deliverable**: A markdown file documenting the actual MongoDB schema

1. Connect to the MongoDB container running in `buddhist-list-bud`
2. List all databases and collections
3. Sample 3-5 documents from each collection
4. Document the actual field names, types, and relationship patterns
5. Identify: How are parent-child relationships stored? How are cross-links (dhamma→list) stored? Is there an `order` field for dhammas within a list?
6. Write findings to `docs/data-model.md`

**STOP after Phase 0. Show me the data model before proceeding. The rest of the phases depend on what we discover.**

## Phase 1 — Tracer Bullet: Full Vertical Slice with Hardcoded Data
**Deliverable**: React app with navigation UI, FastAPI serving a single endpoint, no DB yet

1. Scaffold React app (Vite) in `frontend/`
2. Scaffold FastAPI app in `backend/`
3. Create the four-edge navigation layout component with hardcoded data:
   - A fake "Four Noble Truths" list with 4 fake dhammas
   - Arrow buttons that console.log their targets
4. Single FastAPI endpoint: `GET /api/health` → `{"status": "ok"}`
5. Frontend fetches from health endpoint to prove the connection works
6. Both services start with simple scripts (`npm run dev` / `uvicorn`)

**Demo**: App loads, shows a centered content area with arrow buttons on all 4 edges. Health check proves frontend↔backend connection.

## Phase 2 — Backend API with Real MongoDB Data
**Deliverable**: FastAPI connected to MongoDB, serving real data through REST endpoints

1. Connect FastAPI to the Docker MongoDB instance
2. Implement endpoints (based on Phase 0 findings):
   - `GET /api/lists` — all lists
   - `GET /api/lists/{id}` — single list with its child dhamma IDs/names
   - `GET /api/dhammas/{id}` — single dhamma with parent list, sibling info, downstream links
   - `GET /api/navigate/{id}` — unified endpoint returning everything the UI needs for any object:
     - Current object (list or dhamma)
     - Up/down siblings (if dhamma)
     - Left connections (parents / upstream dhammas)
     - Right connections (children / downstream lists)
3. Test each endpoint with curl/httpie and verify against known data

**Demo**: Hit API endpoints in browser/curl, see real Buddhist teaching data flowing.

## Phase 3 — Wire Frontend to Real API
**Deliverable**: Full navigation working with real data

1. Replace hardcoded data with API calls to `/api/navigate/{id}`
2. Clicking any arrow navigates to that object and re-fetches
3. Left/right edges split into multiple stacked buttons when there are multiple connections
4. Up/down edges hide/show based on whether current view is a list or dhamma
5. Content area displays the name and any description/details of the current object
6. Add a sensible starting point (e.g., load a root list on first visit)

**Demo**: Click through the entire graph of Buddhist teachings using arrow navigation. Start at a list, drill into dhammas, follow cross-links to other lists, navigate back.

## Phase 4 — Polish & UX
**Deliverable**: Interview-ready application

1. Loading states on navigation
2. Breadcrumb or history trail so user knows where they've been
3. Visual labels on arrows showing where they lead (not just arrows — show "Right Concentration" or "Five Hindrances")
4. Responsive layout that works on different screen sizes
5. Clean typography and spacing for the Buddhist content
6. Error handling (404s, disconnected DB, etc.)
7. `docker-compose.yml` that runs all three services (Mongo + API + Frontend) — or at minimum clear README instructions
8. Brief README explaining the project, how to run it, and architectural decisions

**Demo**: Complete, polished app ready for interview presentation.

# Constraints
- **Always demoable**: If you finish Phase 2 at 2am and need to stop, the app works with Phase 2 complete. Never half-implement a phase.
- **Commit after each phase**: Each phase gets its own git commit with a descriptive message.
- **Keep it simple**: No auth, no state management library (React state + context is fine), no over-engineering.
- **Show your work**: Add comments explaining non-obvious decisions, especially around the data model and relationship traversal.
- **MongoDB driver**: Use `motor` (async MongoDB driver for Python) with FastAPI since FastAPI is async-native.
- **Error handling**: Every API endpoint should handle missing IDs gracefully, not crash.
- **CORS**: Configure FastAPI CORS middleware from Phase 1 so the frontend can connect.

# Format
For each phase:
1. State what you're about to build and why
2. Build it incrementally (file by file)
3. Verify it works (run the app, test endpoints)
4. Summarize what's now demoable

Start with Phase 0 now. Explore the MongoDB and show me what you find before moving to Phase 1.
