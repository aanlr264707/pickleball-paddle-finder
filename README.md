# Pickleball Paddle Finder

A full-stack recommender that ranks **494 lab-measured pickleball paddles** against how you want a paddle to play.
Pick your must-haves (budget, tournament approval, shape, type, feel), set targets for swing weight, power, spin and
seven other measurements, and every paddle gets a **Match %**.

**Stack:** Python · Flask · pandas · PostgreSQL · SQLAlchemy · React · TypeScript · Recharts · Docker · GitHub Actions · Postman

![Find page: play-style presets, must-haves and ball-on-court-line targets](docs/screenshots/finder.png)

## Features

- **Questionnaire with live targets.** Each measurement is a court line. Drag the ball to the value you want, or tap
  Low / Medium / High (the dataset's 20th / 50th / 80th percentile), and say how much it matters (1 to 5).
- **Play-style presets:** Power banger, Control / dinker, Spin player, Arm-friendly, Fast hands.
- **Ranked results** with Match %, how close each target came, and the weakest fit greyed out.
- **Browse** all paddles with full-text search, filters, sorting on any measurement (missing values sort last) and
  pagination. All of it runs in SQL, and the state lives in the URL so searches are shareable.
- **Paddle pages** that show where every measurement sits among all 494 paddles, plus "Plays like": the six most
  similar paddles, found with the same scoring engine.
- **Compare** up to four paddles side by side, each on its own lane so equal values never hide each other.
- **Insights** computed with pandas: ball speed by paddle type, which specs correlate with power, price versus
  power, and brand counts. Every chart has an accessible table view.
- **The original terminal app** still works on the same engine (`python -m paddle_finder.cli`).

| Results | Paddle page |
|---|---|
| ![Ranked results with Match %](docs/screenshots/results.png) | ![Paddle percentiles and similar paddles](docs/screenshots/paddle.png) |
| **Compare** | **Insights** |
| ![Side-by-side comparison](docs/screenshots/compare.png) | ![Charts built from pandas analytics](docs/screenshots/insights.png) |

## Architecture

```mermaid
flowchart LR
    CSV[(Raw CSV<br/>spreadsheet export)] -->|pandas ETL:<br/>clean, dedupe, type| DB[(PostgreSQL<br/>paddles table)]
    DB -->|SQL: filter, search,<br/>sort, paginate| API[Flask REST API]
    DB -->|loaded once at startup| Cache[In-memory catalog<br/>+ stats + pandas insights]
    Cache --> Engine[Scoring engine<br/>pure Python]
    Engine --> API
    API -->|JSON| Web[React + TypeScript SPA]
    CLI[Terminal app] --> Engine
```

- **`backend/paddle_finder/core`**: the recommendation engine. Pure Python with no dependencies, and every
  function asserts its preconditions.
- **`backend/paddle_finder/data`**: the pandas ETL, the SQLAlchemy Core schema and the SQL queries. The same code runs on
  PostgreSQL (Docker, production) and SQLite (zero-setup local runs and tests).
- **`backend/paddle_finder/api`**: Flask app factory, request validation (every error names the field that
  caused it), serializers, and analytics.
- **`frontend`**: React 19 + TypeScript (strict), React Router, Recharts (lazy-loaded), plain CSS.

A recommendation request is filtered **in SQL** (`WHERE price <= :budget AND approval LIKE '%USAP%' ...`). The matching
ids are then scored by the engine against the cached catalog. A test checks that the SQL filter returns exactly
the same paddles as the Python filter on both databases.

## How Match % works

For each target, a paddle scores:

```
similarity = max(0, 1 - |value - target| / spread)
```

where `spread` is the distance between the metric's 10th and 90th percentile, so a single outlier paddle can't flatten
everyone's score. Match % is the importance-weighted average of the similarities. A paddle missing a measurement gets
a neutral 0.5 for that metric.

"Plays like" uses the same formula, with the chosen paddle's own measurements as the targets.

## Data cleaning (pandas)

The source is a hand-maintained spreadsheet, so `backend/paddle_finder/data/etl.py` cleans it before anything trusts it:

- `"$169.99"` and `"59%"` become numbers. Blank or non-numeric cells become missing values instead of crashing.
- Stray whitespace (`"Elongated "`) is stripped.
- The same brand typed different ways (`GRUVN` / `Gruvn`, `Element6` / `Element 6`) is merged into one spelling,
  and the most common spelling wins.
- Physically impossible values are removed (one row lists a 5.75 in grip *size*, which is really a grip length).
- Links that aren't URLs (one says "Coming Soon") are blanked, so the app never shows a broken link.
- Rows without a name and duplicate paddles are dropped. Each paddle gets a stable id.

## Run it

### Option 1: Docker (whole stack, one command)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Web app | http://localhost:8080 |
| API | http://localhost:5001/api/health |
| PostgreSQL | `localhost:5433` (user / password / db: `paddle` / `paddle` / `paddles`) |

The API container seeds the database from the CSV on first start.

### Option 2: Local development (no Docker)

Needs Python 3.10+ and Node 20.19+ (or 22+).

```bash
# Terminal 1: API on http://localhost:5001 (uses SQLite and seeds itself on first run)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app paddle_finder.api run --debug --port 5001

# Terminal 2: web app on http://localhost:5173 (proxies /api to :5001)
cd frontend
npm install
npm run dev
```

To use PostgreSQL instead of SQLite, set `DATABASE_URL` before starting the API (see `.env.example`):

```bash
export DATABASE_URL=postgresql://paddle:paddle@localhost:5432/paddles
python -m paddle_finder.data.seed        # load or reload the CSV
```

The API uses port 5001 because macOS reserves 5000 for AirPlay. `make help` lists shortcuts for all of the above.

### Terminal app

```bash
cd backend && python -m paddle_finder.cli
```

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Status, database engine and paddle count |
| `GET` | `/api/metrics` | Every measurement with min / max / average / percentiles |
| `GET` | `/api/options` | Menu values: brands, shapes, paddle types, impact feels |
| `GET` | `/api/presets` | Play-style presets |
| `POST` | `/api/recommendations` | Filter + score. Body: `{filters, preferences}` or `{preset}` |
| `GET` | `/api/paddles` | Search, filter, sort, paginate (`q`, `brand`, `paddle_type`, `shape`, `tournament_only`, `max_price`, `sort`, `order`, `page`, `per_page`) |
| `GET` | `/api/paddles/{id}` | One paddle with the percentile of every measurement |
| `GET` | `/api/paddles/{id}/similar` | Paddles that play most like this one |
| `GET` | `/api/compare?ids=1,2,3` | Two to four paddles side by side |
| `GET` | `/api/insights` | pandas analytics for the Insights page |

Example:

```bash
curl -X POST http://localhost:5001/api/recommendations \
  -H 'Content-Type: application/json' \
  -d '{"filters": {"max_price": 200, "tournament_only": true},
       "preferences": [{"metric": "power", "target": "high", "importance": 5},
                       {"metric": "swing_weight", "target": 112, "importance": 3}],
       "limit": 5}'
```

Errors always have the same shape, and name the field at fault:

```json
{"error": {"status": 400, "message": "must be a whole number from 1 to 5", "field": "preferences[0].importance"}}
```

A **Postman collection** with 13 requests and 29 contract assertions is in `postman/`. Import it into Postman or run it
headless:

```bash
npx newman run postman/paddle-finder.postman_collection.json --env-var baseUrl=http://localhost:5001
```

## Tests and CI

```bash
cd backend && pytest                      # 55 tests (engine, ETL, SQL, API, CLI): SQLite by default
TEST_DATABASE_URL=postgresql://paddle:paddle@localhost:5432/paddles_test pytest   # same suite on PostgreSQL
cd frontend && npm test                   # vitest unit tests
```

GitHub Actions (`.github/workflows/ci.yml`) runs on every push:

1. **Backend:** ruff lint, then pytest on SQLite and on a PostgreSQL 16 service container, with coverage.
2. **Frontend:** TypeScript type-check, vitest, production build.
3. **API contract:** starts the API and runs the Postman collection with Newman.
4. **Docker:** builds both images.

## Project structure

```
.
├── backend/
│   ├── paddle_finder/
│   │   ├── core/        scoring engine, models, stats, presets (pure Python)
│   │   ├── data/        pandas ETL, SQL schema, SQL queries, seed command
│   │   ├── api/         Flask app factory, routes, validation, insights
│   │   └── cli/         interactive terminal app
│   ├── tests/           pytest suite
│   ├── wsgi.py          gunicorn entry point
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/         typed API client
│   │   ├── components/  rail, target rail, result row...
│   │   ├── pages/       Find, Browse, Paddle, Compare, Insights
│   │   └── lib/         formatting, data hooks, compare state
│   ├── nginx.conf
│   └── Dockerfile
├── data/paddle_database.csv
├── postman/             API collection with tests
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Background

This started as a pure-Python command-line recommender. The original scoring engine, with its dataclasses, custom sort
keys and asserted preconditions, is still the core of the app. Everything else was built around it: the pandas pipeline,
the SQL layer, the REST API and the web UI.

## Data credit

Paddle measurements come from the Pickleball Effect paddle database. The data
belongs to its authors and is included for non-commercial, educational use. The
code in this repository is MIT-licensed (see `LICENSE`).
