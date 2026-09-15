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
│   │   └── property_service.py
│   └── controllers/         # HTTP concerns: map errors to status codes
├── migrations/              # Alembic (async env); versions/0001_initial_schema.py
├── scripts/seed.py          # sample properties + reference underwritings
└── tests/                   # pytest (calculator + scoring, no DB needed)
```

Request flow: `routes.py` → `controllers/` → `services/` → `repositories/` → `models/`.

## Run it

```bash
cd backend
cp .env.example .env            # DATABASE_URL points at the compose DB on port 5434
docker compose up -d            # Postgres 16
uv sync                         # install deps into .venv
uv run alembic upgrade head     # create tables
uv run python -m scripts.seed   # 6 properties + their reference underwritings
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
| GET | `/api/properties` | Plain property list (`?search=` on address/city/state) |
| GET | `/api/properties/{zpid}` | One property |
| POST | `/api/underwritings` | `{ "zpid": "..." }` → creates a draft prefilled from the property (201) |
| GET | `/api/underwritings/{id}` | Draft, with detail, taxes, line items and derived numbers |
| PUT | `/api/underwritings/{id}` | Save a draft. Any subset of sections; derived numbers are recomputed when all required sections exist |
| POST | `/api/underwritings/{id}/submit` | Optional body = same shape as PUT. Finalises, grades, returns `{ submission, underwriting, dashboard }` |
| GET | `/api/submissions?zpid=` | Attempt history |
| GET | `/api/submissions/{id}` | One graded attempt |

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

Each property has one **reference** underwriting (`underwritings.is_reference = true`, seeded). A submission is compared to it on six derived metrics. A value within tolerance earns full points; credit decays linearly to zero at three times the tolerance.

| Metric | Points | Tolerance |
|---|---|---|
| `purchase_price` | 15 | ±5% |
| `mid_gross_revenue` | 25 | ±15% |
| `operating_expense_total` (monthly) | 15 | ±20% |
| `optimization_total` | 10 | ±25% |
| `total_oop` | 15 | ±15% |
| `m_cash_on_cash` | 20 | ±3 percentage points (absolute) |

`accuracy` is the total out of 100 and is stored on `training_submissions` alongside the full `breakdown` (candidate value, reference value, deviation, points per metric). Rules live in `app/services/scoring_service.py`.

## Data model notes

- `properties` mirrors the main backend's `zillow.scheduled_listings` (preset FK dropped).
- `underwritings` and its children mirror `iron_bank.*`. FKs to `markets`/`users` are dropped (columns kept as plain ints), `is_reference` added, and a partial unique index guarantees one reference per `zpid`.
- Reference underwritings are read-only through the API (403 on PUT).
- Re-running `scripts/seed.py` refreshes properties and references without touching candidate attempts.
