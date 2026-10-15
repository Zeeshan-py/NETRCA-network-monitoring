# NetRCA

NetRCA is an AI-assisted network root cause analysis and incident response project for a controlled Mininet simulation. The system is being developed in phases; the architecture and requirements are in [`Instruction/`](Instruction/).

## Current scope

Phase 1 provides the FastAPI health endpoint and Next.js shell. Phases 2–12 add PostgreSQL persistence, the controlled Mininet lab, monitoring, evidence collection, fault injection, anomaly detection, correlation, graph analysis, RCA, and impact analysis. Phase 13 adds an opt-in backend Gemini explanation that orders evidence-linked claims. Phase 14 hardens local-only API access, request limits, and safe errors. Phase 15 verifies the request path across Mininet and PostgreSQL with rollback fixtures. Phase 16 connects dashboard workflows to the local API. Phase 17 adds a read-only interactive graph using separate live and stored topology sources and navigation through validated stored evidence relationships. See the [Phase 16 report](frontend/PHASE16_REPORT.md) and [Phase 17 report](frontend/PHASE17_REPORT.md) for verification details and limitations.

```
backend/    FastAPI app, configuration, and pytest tests
frontend/   Next.js app, API client, styling, and Vitest tests
Instruction/ Original project specifications and design preview
supabase/  Supabase CLI configuration for the linked project
database/  Phase 2 database guide, local-only demo seed, and validation
network/   Phase 3 Mininet setup, usage, and test guide
topology/  Phase 4 topology engine and Phase 10 graph-analysis guides and reports
monitoring/ Phase 5 read-only monitoring guide and validation report
pipeline/  Phase 6 evidence pipeline guide and validation report
faults/    Phase 7 controlled fault injection guide and validation report
anomaly/   Phase 8 anomaly detection guide and validation report
correlation/ Phase 9 correlation guide, schema proposal, and validation report
rca/       Phase 11 RCA rules, approved schema proposal, and validation report
impact/    Phase 12 impact rules, approved schema proposal, and validation report
explanation/ Phase 13 Gemini explanation contract and report
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
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
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

## Local demonstration workflow

Use the frontend and API on the same workstation, bound to loopback. NetRCA
does not provide user authentication, so do not expose either development
server to a LAN, reverse proxy, or public network. The dashboard reads the
current simulator status/topology and database-backed monitoring, metrics,
logs, events, anomalies, and incidents. Health only means that FastAPI
responded; database and simulator states are reported separately.

1. Configure `frontend/.env.local` with
   `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`. Configure
   `backend/.env` with `NETRCA_CORS_ORIGINS=http://localhost:3000`. Keep
   `DATABASE_URL` and `GEMINI_API_KEY` only in the backend environment; never
   put credentials in a `NEXT_PUBLIC_*` variable or paste them into a terminal
   command. The frontend template already contains the local API URL.
2. Start the API in one terminal using the [Backend](#backend) command and the
   frontend in another using the [Frontend](#frontend) command. The default
   simulation and write flags are off. A status request alone does not start
   Mininet or write database records.
3. Open `http://localhost:3000`, select **Refresh**, and verify the API badge,
   simulator status, topology, monitoring snapshot, and stored lists
   independently. Empty lists mean no records were returned. A database or
   connectivity error remains visible in that section. List views expose
   previous/next controls and the count/page currently displayed.
4. For a safe fixture-only preview, use the existing
   `database/seed_local.py` only with a **disposable local PostgreSQL** and its
   required explicit loopback `NETRCA_LOCAL_DATABASE_URL`. Do not point the
   seed runner at the linked/cloud database. Seed rows are labeled demo
   fixtures and do not prove live Mininet or analysis execution. For an actual
   lab workflow, use the isolated Ubuntu/WSL2 Mininet instructions in
   [network/README.md](network/README.md), enable only the required backend
   flags locally, and collect snapshots through the guarded API. Never inject
   a fault into a real network.
5. In **Evidence**, submit only the displayed page to correlation; in
   **Incidents**, select a stored incident to inspect its original event and
   anomaly references, current RCA candidates, and impact/failure chain. RCA
   and impact buttons call the existing opt-in endpoints, which can reject the
   action while their backend write flags are off. The UI labels candidate
   scores as uncalibrated rule points and distinguishes observed from
   potential impact. It does not fabricate empty or missing results.
6. **Generate explanation** is a separate user action and may call the
   configured Gemini provider when the backend enables it. Page load and
   refresh never call Gemini. Phase 16 verification used a mocked frontend
   response and made no live Gemini request. To demonstrate this panel without
   an external call, use the existing test suite's mocked response; the runtime
   backend does not currently include a mock-provider setting.
7. To show an empty state, use a disposable database with no seeded records.
   To show API/network error states, stop the local API or deliberately use an
   unavailable local endpoint, then restore the normal configuration. Do not
   alter security controls to make a request succeed.
8. Stop the frontend and API with `Ctrl+C`. If the isolated Mininet lab was
   started, stop it with its guarded API or the owning backend shutdown path,
   then verify the lab is stopped using the documented Ubuntu checks.

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
| `NETRCA_RCA_WRITES_ENABLED` | Backend | Opt in to Phase 11 persisted analysis; default `false` |
| `NETRCA_RCA_TIMING_WINDOW_SECONDS` | Backend | Temporal support window for RCA; default 300 seconds |
| `NETRCA_IMPACT_WRITES_ENABLED` | Backend | Opt in to Phase 12 persisted impact analysis; default `false` |

If the frontend runs on a different origin, update `NETRCA_CORS_ORIGINS` accordingly. Restart the frontend after changing its environment file. Never put future Gemini keys or Supabase service credentials in a `NEXT_PUBLIC_` variable.

The Supabase CLI project configuration is in `supabase/config.toml`. To link a fresh checkout to the remote project, run `npx supabase login` and `npx supabase link --project-ref <project-ref>` from the repository root. CLI authentication is separate from the publishable API key. The backend does not run database queries on startup; use `python -m app.db.check` from `backend/` to verify the configured connection.

## Database setup

See [database/README.md](database/README.md) for migration, local setup, guarded demo seed, RLS, validation, and rollback instructions. The migration is `supabase/migrations/20261012000100_initial_schema.sql`; after reviewing the linked project and a dry run, apply it from the repository root with `npx supabase db push --linked --skip-vault`. Development fixture rows are never included in that push. The database validation suite can test migration behavior inside a rollback transaction and is documented in the database guide.

Phase 6 adds two [evidence pipeline migrations](pipeline/README.md) for observed interface/link metrics and deduplication indexes. Phase 11 adds the approved [RCA runs migration](rca/PHASE11_REPORT.md), and Phase 12 adds the approved [impact runs migration](impact/PHASE12_REPORT.md). These were applied to the linked project without loading development fixtures.

## Network simulation

Simulation is disabled by default. From `backend/`, `python -m app.network.cli environment` reports whether this interpreter can run Mininet. A supported Linux environment with Mininet, Open vSwitch and root privilege is required to start the lab. The [network guide](network/README.md) explains the real smoke test, single-worker local API, security gates and integration test. On Windows, the simulator reports unavailable; the existing API health endpoint remains API-only.

## Limitations

The Mininet lab was verified locally under Ubuntu WSL2; its simulation still requires explicit opt-in and root privileges. Monitoring, evidence collection, [controlled fault injection](faults/README.md), [anomaly detection](anomaly/README.md), [incident correlation](correlation/README.md), [rule-based RCA](rca/README.md), and [impact analysis](impact/README.md) are on demand. [Gemini explanations](explanation/README.md) require separate opt-in. Remediation and authentication are outside the current scope. An API connection indicator confirms only that the FastAPI health endpoint responded. It does not indicate database or network health.
# NETRCA-network-monitoring
