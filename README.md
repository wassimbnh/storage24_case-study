# Payment Status Trigger: Case Study

Detects invoices that just became overdue, creates a mock Stripe payment link routed to the right bank account, and shows the results in a UI.

| Folder | What it is |
| --- | --- |
| `server/` | Backend: Python, FastAPI and SQLite, managed with [uv](https://docs.astral.sh/uv/) |
| `client/` | Frontend: React and TypeScript (Vite) |
| `schema.sql` | Seeded schema, loaded into SQLite when the backend starts |

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/). It installs the Python version the backend needs (3.14+).
- [Node.js](https://nodejs.org/) 20+ with npm

## Install dependencies

```bash
# Backend: creates server/.venv and installs runtime and dev dependencies
cd server
uv sync

# Frontend
cd ../client
npm install
```

To add a backend dependency, run `uv add <package>` (or `uv add --dev <package>` for dev-only tools) from `server/`.

## Run the project

Start the backend and the frontend in two separate terminals.

### Backend

```bash
cd server
uv run uvicorn main:app --reload
```

- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs

The database is an in-memory SQLite instance that is rebuilt from `schema.sql` on every start. Restarting the server returns everything to the seeded state.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/sync` | Creates one tracking row for each history row that doesn't have one yet (`pending` or `skipped`). Running it again is safe. |
| `GET` | `/tracking` | Returns all tracking rows |
| `POST` | `/reset` | Deletes all tracking rows so the demo can be rerun. Seeded tables are not touched. |

### Frontend

```bash
cd client
npm run dev
```

The app runs on http://localhost:5173. Other scripts: `npm run build`, `npm run lint`, `npm run preview`.

## Run the tests

```bash
cd server
uv run pytest            # all tests
uv run pytest -v         # one line per test
uv run pytest test/test_sync.py   # a single file
```

The tests live in `server/test/`:

- `test_sync.py`: sync classification, idempotency and reset, run against a fresh seeded database
- `test_sync_endpoints.py`: the `/sync`, `/tracking` and `/reset` endpoints, through FastAPI's test client
