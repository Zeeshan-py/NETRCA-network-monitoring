# NetRCA

NetRCA is an AI-assisted network root cause analysis and incident response project for a controlled Mininet simulation. The system is being developed in phases; the architecture and requirements are in [`Instruction/`](Instruction/).

## Current scope

Phase 1 provides a FastAPI application with a versioned API health endpoint and a Next.js application shell that checks that endpoint. Phase 2 adds the Supabase PostgreSQL schema, a guarded development seed, a server-side connection layer, and database validation. Phase 3 adds an opt-in Mininet lab topology, a lifecycle manager, connectivity checks, and local-only simulator API routes. Phase 4 adds validated device/link graph and PostgreSQL topology services. Phase 5 adds on-demand, read-only Mininet monitoring snapshots and bounded host-pair probes. Phase 6 adds controlled ingestion of observed metrics, structured logs and state events into PostgreSQL, with paginated history. Phase 7 adds opt-in, local-only fault injection with tracked restoration in the Mininet lab. Phase 8 adds explainable threshold, baseline and optional Isolation Forest detection on validated metrics. Phase 9 adds deterministic event/anomaly correlation into stored incidents. The health response describes the API process only. The UI contains no live network metrics or incident data.

```
backend/    FastAPI app, configuration, and pytest tests
frontend/   Next.js app, API client, styling, and Vitest tests
Instruction/ Original project specifications and design preview
supabase/  Supabase CLI configuration for the linked project
database/  Phase 2 database guide, local-only demo seed, and validation
network/   Phase 3 Mininet setup, usage, and test guide
topology/  Phase 4 topology engine guide and validation report
monitoring/ Phase 5 read-only monitoring guide and validation report
pipeline/  Phase 6 evidence pipeline guide and validation report
faults/    Phase 7 controlled fault injection guide and validation report
anomaly/   Phase 8 anomaly detection guide and validation report
correlation/ Phase 9 correlation guide, schema proposal, and validation report
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm
- Git for version control

Mininet needs Linux networking support. Ubuntu 26.04.1 LTS under WSL2 is installed on this workstation, and the Phase 3 lab passed real Mininet/Open vSwitch connectivity tests. See the [Phase 3 network guide](network/README.md) for setup and test results.

## Backend

In PowerShell, from the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Linux or WSL2, activate with `source .venv/bin/activate` and copy the example file with `cp .env.example .env`.

- API health: `http://localhost:8000/api/v1/health`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Run backend tests from `backend/` with `python -m pytest`.

## Frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. For a production build, run `npm run build`, then `npm start`. Run checks with `npm test`, `npm run typecheck`, and `npm run lint`.

## Configuration

The backend reads `backend/.env` or process environment variables. The frontend reads `frontend/.env.local`. The examples contain only local development values.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `NETRCA_CORS_ORIGINS` | Backend | Comma-separated browser origins allowed to call the API; set to the frontend origin |
| `NETRCA_LOG_LEVEL` | Backend | Application log level |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Browser-accessible API base URL, including `/api/v1` |
| `SUPABASE_URL` | Backend | Supabase project API URL for later database integration |
| `SUPABASE_PUBLISHABLE_KEY` | Backend | Publishable Data API key; not a database password |
| `DATABASE_URL` | Backend | PostgreSQL connection string, kept server-side |
| `NETRCA_PIPELINE_WRITES_ENABLED` | Backend | Opt in to local Phase 6 evidence writes; default `false` |
| `NETRCA_FAULT_INJECTION_ENABLED` | Backend | Opt in to local Phase 7 lab fault controls; default `false` |
| `NETRCA_ANOMALY_WRITES_ENABLED` | Backend | Opt in to Phase 8 anomaly persistence; local detection remains available |
| `NETRCA_CORRELATION_WRITES_ENABLED` | Backend | Opt in to Phase 9 incident writes; default `false` |
| `NETRCA_CORRELATION_WINDOW_SECONDS` | Backend | Maximum direct-correlation window; default 300 seconds |
| `NETRCA_CORRELATION_MAX_AGE_MINUTES` | Backend | Maximum age of selected evidence; default 1440 minutes |

If the frontend runs on a different origin, update `NETRCA_CORS_ORIGINS` accordingly. Restart the frontend after changing its environment file. Never put future Gemini keys or Supabase service credentials in a `NEXT_PUBLIC_` variable.

The Supabase CLI project configuration is in `supabase/config.toml`. To link a fresh checkout to the remote project, run `npx supabase login` and `npx supabase link --project-ref <project-ref>` from the repository root. CLI authentication is separate from the publishable API key. The backend does not run database queries on startup; use `python -m app.db.check` from `backend/` to verify the configured connection.

## Database setup

See [database/README.md](database/README.md) for migration, local setup, guarded demo seed, RLS, validation, and rollback instructions. The migration is `supabase/migrations/20261012000100_initial_schema.sql`; after reviewing the linked project and a dry run, apply it from the repository root with `npx supabase db push --linked --skip-vault`. Development fixture rows are never included in that push. The database validation suite can test migration behavior inside a rollback transaction and is documented in the database guide.

Phase 6 adds two [evidence pipeline migrations](pipeline/README.md) for observed interface/link metrics and deduplication indexes. They were applied to the linked project without loading development fixtures.

## Network simulation

Simulation is disabled by default. From `backend/`, `python -m app.network.cli environment` reports whether this interpreter can run Mininet. A supported Linux environment with Mininet, Open vSwitch and root privilege is required to start the lab. The [network guide](network/README.md) explains the real smoke test, single-worker local API, security gates and integration test. On Windows, the simulator reports unavailable; the existing API health endpoint remains API-only.

## Limitations

The Mininet lab was verified locally under Ubuntu WSL2; its simulation still requires explicit opt-in and root privileges. Monitoring, evidence collection, [controlled fault injection](faults/README.md), [anomaly detection](anomaly/README.md), and [incident correlation](correlation/README.md) are on demand. RCA, Gemini, and authentication are planned for later phases. An API connection indicator confirms only that the FastAPI health endpoint responded. It does not indicate database or network health.
# NETRCA-network-monitoring
