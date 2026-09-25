# STR Training Backend

Backend for the frontend engineer assessment. It powers a **training dashboard**:

1. The dashboard lists properties with each one's training status and accuracy.
2. The candidate picks a property and starts an underwriting (a draft prefilled from the listing).
3. They fill in purchase details, revenue forecast, taxes, optimization budget, operating expenses and comps, saving as they go.
4. On submit the backend derives the deal numbers, grades them against the analyst's reference underwriting for that property, stores the attempt, and returns the score with a per-metric breakdown plus the refreshed dashboard.

Everything lives in the Postgres `public` schema. No authentication.

## Stack

FastAPI · SQLAlchemy 2 (async, asyncpg) · Alembic · Pydantic v2 · uv

## Layout (MVC)

```
backend/
├── main.py                  # uvicorn entrypoint: `app = create_app()`
├── app/
│   ├── __init__.py          # create_app(): FastAPI app factory, CORS, router
│   ├── routes.py            # all HTTP routes; wires controller → service → repository
│   ├── core/                # config (env), database (engine/session/Base), logger
│   ├── models/              # SQLAlchemy models
│   │   ├── market.py        # markets (groups properties + their underwritings)
│   │   ├── property.py      # properties (mirrors zillow.scheduled_listings)
│   │   ├── underwriting.py  # underwritings, uw_details, uw_taxes (mirrors iron_bank)
│   │   ├── line_items.py    # uw_optimization_items, uw_operating_expenses, uw_comp_sets
│   │   └── training.py      # training_submissions (graded attempts)
│   ├── schemas/             # Pydantic request/response models
│   ├── repositories/        # DB access only
│   ├── services/            # business logic
│   │   ├── underwriting_calculator.py  # pure maths (OOP, PRR, CoC, taxes)
│   │   ├── scoring_service.py          # accuracy grading against the reference
│   │   ├── underwriting_service.py     # start / save / submit
│   │   ├── training_service.py         # dashboard + grading orchestration
│   │   ├── property_service.py
│   │   └── market_service.py
│   └── controllers/         # HTTP concerns: map errors to status codes
├── migrations/              # Alembic (async env); versions/0001_initial_schema.py
├── scripts/seed.py          # markets, sample properties + reference underwritings
└── tests/                   # pytest (calculator + scoring, no DB needed)
```

Request flow: `routes.py` → `controllers/` → `services/` → `repositories/` → `models/`.

## Run it

Only Docker is required:

```bash
cd backend
docker compose up -d --build    # Postgres + API; first start migrates and seeds
```

The API is on http://localhost:8000. The first start runs the migrations and seeds
the database; later starts skip the seed so attempts survive a restart.

```bash
docker compose exec api python -m scripts.seed --reset   # wipe attempts and reseed
docker compose logs -f api                               # follow the API logs
docker compose down                                      # stop, keep data (-v deletes it)
API_PORT=8001 DB_PORT=5435 docker compose up -d          # if 8000 or 5434 is taken
```

### Developing the backend

To run the API on the host with hot reload, start only the database:

```bash
cd backend
cp .env.example .env            # DATABASE_URL points at the compose DB on port 5434
docker compose up -d db         # Postgres 16 only
uv sync                         # install deps into .venv
uv run alembic upgrade head     # create tables
uv run python -m scripts.seed   # 4 markets, 6 properties + their reference underwritings
uv run uvicorn main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

Tests and lint:

```bash
uv run pytest
uv run ruff check .
```

Migrations after a model change:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/dashboard` | Properties with `status` (`not_started` / `in_progress` / `submitted`), `attempts`, `latest_accuracy`, `best_accuracy`, `active_underwriting_id`, plus a summary block |
| GET | `/api/markets` | All markets with a live `property_count` (`?is_active=` to filter) |
| GET | `/api/markets/{id}` | One market |
| GET | `/api/properties` | Plain property list (`?search=` on address/city/state, `?market_id=` to filter by market) |
| GET | `/api/properties/{zpid}` | One property |
| POST | `/api/underwritings` | `{ "zpid": "..." }` → creates a draft prefilled from the property (201) |
| GET | `/api/underwritings/{id}` | Draft, with detail, taxes, line items and derived numbers |
| PUT | `/api/underwritings/{id}` | Save a draft. Any subset of sections; derived numbers are recomputed when all required sections exist |
| POST | `/api/underwritings/{id}/submit` | Optional body = same shape as PUT. Finalises, grades, returns `{ submission, underwriting, dashboard }` |
| GET | `/api/submissions?zpid=` | Attempt history |
| GET | `/api/submissions/{id}` | One graded attempt |

Errors come back as `{"detail": "..."}` and every route documents the codes it can
raise (404 / 403 / 500), so a client generated from `openapi.json` sees them. The
`422` on write routes is FastAPI's own request-validation error.

### Save / submit payload

```json
{
  "bedrooms": 3, "bathrooms": "3.0", "sleep_count_low": 8, "sleep_count_high": 10,
  "purchase_details": {
    "purchase_price": "650000", "down_payment_pct": "0.20", "interest_rate": "0.07",
    "mortgage_years": 30, "closing_costs_pct": "0.03"
  },
  "forecasted_revenue": {
    "co_hosting_fee_pct": "0", "annual_re_appreciation_pct": "0.03",
    "scenarios": { "low": {"forecasted_revenue": "100000"},
                   "mid": {"forecasted_revenue": "120000"},
                   "high": {"forecasted_revenue": "140000"} }
  },
  "taxes": { "land_assumptions_pct": "0.20", "sla_multiplier_pct": "0.25",
             "bonus_amount_pct": "0.60", "tax_rate_pct": "0.37" },
  "optimization_items": [ {"category": "Furniture", "total_price": "50000"} ],
  "operating_expenses": [ {"expense_name": "Utilities", "monthly_amount": "500"} ],
  "comp_set": [ {"listing_url": "https://airbnb.com/rooms/1", "revenue": "118000", "bedrooms": 3, "sleeps": 9} ],
  "tags": { "turnkey": false, "luxury": false, "renovation_level": 2 },
  "deal_pitch": "…", "note": "…", "analyst_notes": "…"
}
```

Percentages are fractions (`0.20` = 20%). Submit requires `purchase_details`, `forecasted_revenue` and `taxes`; otherwise it returns 422 naming the missing sections.

## Scoring

Each property has one **reference** underwriting (`underwritings.is_reference = true`, seeded). Grading looks at a single number: the trainee's **mid-scenario forecasted revenue** (`mid_gross_revenue`) against the analyst's.

```
deviation = |candidate - reference| / reference

deviation <= 0.10  ->  best    ->  100
deviation <= 0.25  ->  medium  ->   70
otherwise          ->  low     ->   40
```

| Band | Trainee forecast is | Rating | Accuracy |
|---|---|---|---|
| Best | within ±10% of the reference | `best` | 100 |
| Medium | within ±25% | `medium` | 70 |
| Low | further out, or missing | `low` | 40 |

Both thresholds are inclusive. A missing forecast, or any guess against a zero reference, lands in `low` rather than raising.

Worked example — reference forecast $125,000, so best is $112,500–$137,500 and medium is $93,750–$156,250:

| Candidate | Deviation | Rating | Accuracy |
|---|---|---|---|
| $130,000 | 0.0400 | best | 100.00 |
| $150,000 | 0.2000 | medium | 70.00 |
| $200,000 | 0.6000 | low | 40.00 |

`rating` and `accuracy` are both stored on `training_submissions`, with the full `breakdown` (candidate, reference, deviation, both thresholds) as JSONB so the UI can explain the grade. The dashboard exposes `latest_rating` / `best_rating` next to the accuracies. Thresholds and band scores are module constants at the top of `app/services/scoring_service.py`.

## Data model notes

- `markets` groups properties that share one investment thesis. Both `properties.market_id` and `underwritings.market_id` are nullable FKs with `ON DELETE SET NULL`, so retiring a market never deletes deal history. A new underwriting inherits its market from the property it starts from.
- `properties` mirrors the main backend's `zillow.scheduled_listings` (preset FK dropped), plus `market_id`.
- `underwritings` and its children mirror `iron_bank.*`. The FK to `users` is dropped (columns kept as plain ints), `is_reference` added, and a partial unique index guarantees one reference per `zpid`.
- Reference underwritings are read-only through the API (403 on PUT).
- Re-running `scripts/seed.py` refreshes markets, properties and references without touching candidate attempts. `--reset` truncates every table (ids restart at 1, so the seeded markets are always 1-4) and reseeds from scratch. `--if-empty` does nothing once properties exist; the API container runs it on every start.
- The schema is kept as a single Alembic revision (`0001`); schema changes regenerate it rather than stacking migrations.
