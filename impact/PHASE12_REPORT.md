# Phase 12 report — impact and failure chain

## Implementation

Phase 12 adds a deterministic engine, transactional PostgreSQL store, typed
models, and local-only API routes. The engine maps one uniquely leading RCA
candidate only when its direct event/anomaly reference still matches validated
incident evidence and the stored topology. It builds branching, ordered
one-hop physical/hosting chains. Directly evidenced components are labeled
`OBSERVED`; endpoints, adjacent links/devices, and hosted services are
`POTENTIAL`. No path beyond one hop, directed service dependency, confirmed
causality, impact severity, customer count, or application outage is invented.
Inconclusive inputs persist as `INCONCLUSIVE` with empty impact entities.
Exact rules and API behavior are in [README.md](README.md).

Files created: `supabase/migrations/20261014000101_phase12_impact_runs.sql`,
`backend/app/impact/{__init__,models,engine,store}.py`,
`backend/app/api/impact.py`, `backend/tests/test_impact.py`,
`backend/tests/test_impact_database_integration.py`, and the files in
`impact/`. Files modified: `backend/app/main.py`, `backend/app/core/config.py`,
`backend/.env.example`, and root `README.md`. Original `Instruction/`
documents and the pre-existing `.gitignore` edit were preserved.

## Approved migration and live verification

The configured PostgreSQL connection and Supabase local link both identify
project `oeizpptglvtnljkheatq`. Before applying, PostgreSQL reported 17.11,
`postgres` database/user, `CREATE` privilege, required roles, five prior
migrations, and no `public.impact_runs`. The saved migration matched the exact
approved proposal. Executing it in a transaction succeeded; rollback removed
the table. `supabase migration list --linked` showed only
`20261014000101` pending; `supabase migration up --linked` applied only it.
Post-application history includes that version. Live catalog checks confirmed
nine expected columns, the RCA-run foreign key, primary/unique/check
constraints, three indexes, RLS enabled, zero policies, no `anon` or
`authenticated` SELECT/INSERT/UPDATE/DELETE access, and `service_role`
access for all four operations. No `db push` or other schema change was used.

## API example

`POST /api/v1/incidents/{uuid}/impact/analyze` (local control header and
write flag), `GET /api/v1/incidents/{uuid}/impact`, and
`GET /api/v1/incidents/{uuid}/failure-chain` return a typed run envelope.
A representative `data.result` fragment is:

```json
{
  "status": "ASSESSED",
  "candidate_target_kind": "LINK",
  "entities": [{"kind": "LINK", "classification": "OBSERVED", "evidence": [{"source_type": "EVENT", "reason": "DIRECT_FAILURE"}]}],
  "chain": [{"step": 1, "relationship": "LINK_ENDPOINT", "classification": "POTENTIAL"}],
  "user_application_impact": "UNKNOWN_UNVERIFIED"
}
```

The fragment omits required UUIDs and other fields for brevity; it is not a
literal complete response. The POST is denied without local access, header,
and the opt-in write flag. The GET routes read the latest run associated with
the latest RCA run. Errors use the existing sanitized envelope.

## Validation and limits

- Windows: `cd backend; .\.venv\Scripts\python.exe -m pytest -q` —
  **90 passed, 20 skipped**, one existing Starlette/httpx deprecation warning.
- Ubuntu WSL2: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q` —
  **90 passed, 20 skipped**, the same warning.
- Windows real PostgreSQL: `cd backend; $env:NETRCA_RUN_IMPACT_DB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest tests/test_impact_database_integration.py -q` — **3 passed**.
- Ubuntu WSL2 real PostgreSQL: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_IMPACT_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest tests/test_impact_database_integration.py -q` — **3 passed**.

The integration tests use actual PostgreSQL inserts and rollback for assessed
and inconclusive runs, repeated-run idempotency, stale topology rejection,
and a constraint failure. Every fixture was explicitly rolled back. The 20
default skips are opt-in database/Mininet/fault tests and an optional ML test;
three are the new Phase 12 database tests. No Mininet test was needed or run,
so no lab cleanup was necessary. Stored graph status may differ from incident
time, and a potential service exposure is not a measured service outage. No
incident-scoped recovery evidence or directed dependency data is available to
calculate a defensible impact duration or user/application outage. A post-test
read-only check found zero remaining Phase 12 fixture devices/incidents and
zero rows in `impact_runs`. `git diff --check` and the staged equivalent passed;
the pre-existing `.gitignore` change was excluded from staging and commit.
