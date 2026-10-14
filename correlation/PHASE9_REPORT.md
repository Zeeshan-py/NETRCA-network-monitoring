# Phase 9 report — event correlation and incident grouping

## Scope and architecture

The original `Instruction/` documents and existing Phase 3–8 implementations were inspected before changes. Phase 9 adds a pure deterministic correlation engine, a PostgreSQL incident repository, and local-only FastAPI routes. It consumes validated stored Phase 6 events and Phase 8 metric anomalies; it does not alter collection, anomaly detection, Mininet, graph analysis, RCA, Gemini, remediation, or frontend behavior. Details and API examples are in [README.md](README.md).

Files added: `supabase/migrations/20261013000102_phase9_incident_anomalies.sql`, `backend/app/correlation/{__init__,models,engine,store}.py`, `backend/app/api/incidents.py`, `backend/tests/test_correlation.py`, `backend/tests/test_correlation_database_integration.py`, `correlation/README.md`, and this report. The earlier untracked `correlation/PHASE9_SCHEMA_PROPOSAL.md` was retained and updated with approval status. Files modified: `backend/app/main.py`, `backend/app/core/config.py`, `backend/.env.example`, and root `README.md`. The pre-existing `.gitignore` modification was not changed or staged by Phase 9. No `Instruction/` file was modified.

## Approved migration and live verification

The approved additive SQL was saved unchanged as `20261013000102_phase9_incident_anomalies.sql`. Before application, the configured DSN and local Supabase link both identified project `oeizpptglvtnljkheatq` without printing secrets. The target reported database/user `postgres`, PostgreSQL 17.11, required roles and `CREATE` privilege, and migration history `20261012000100`, `20261013000100`, `20261013000101`. `incident_anomalies` was absent. Executing the exact migration in a transaction succeeded; rollback removed it. `npx supabase migration list --linked` showed only `20261013000102` pending. `npx supabase migration up --linked` applied exactly that file, returned success, and recorded `20261013000102` in migration history. No `db push`, schema reset, seed, or unrelated migration was used.

Read-only live checks passed for the four required columns and defaults; incident/anomaly foreign keys; composite primary key; unique anomaly key; nonempty relationship check; all three expected indexes; RLS enabled; zero policies; no PUBLIC, `anon`, or `authenticated` access; and `service_role` SELECT/INSERT/UPDATE/DELETE. A post-application `npx supabase migration list --linked` showed all four local versions matching remote. The production-target table is now present. A read-only check found zero remaining `phase9-%` test devices after rollback.

## Correlation and incident behavior

The engine requires a bounded time window plus a direct, stored identity: shared device, link, service, source event, source metric, or a known link and its endpoint device. Different explicit services do not group. It never groups on time alone or walks topology paths. Phase 6/8 validation is reused; malformed, stale, future, or missing evidence is rejected or skipped. Duplicate IDs are deduplicated. A group spans at most the configured window. Reasons are stored in `incident_events.relationship_type` or `incident_anomalies.relationship_type` and returned in responses.

A new incident is `DETECTED`. Related evidence can attach to an existing `DETECTED` or `INVESTIGATING` incident. Reprocessing returns existing memberships without new writes. A group matching multiple incidents is skipped instead of silently merging them. Existing closed/resolved incidents are not reopened. Severity is the maximum of existing and new evidence (`LOW < MEDIUM < HIGH < CRITICAL`), and start time can move earlier. A transaction-scoped PostgreSQL advisory lock serializes Phase 9 writers. Root-cause, confidence, impact, AI, and end-time fields are untouched.

The routes are `POST /api/v1/events/correlate` (loopback, allowed local origin, `X-NetRCA-Local-Control: 1`, and `NETRCA_CORRELATION_WRITES_ENABLED=true`), `GET /api/v1/incidents` (page, limit, status, severity), and `GET /api/v1/incidents/{incident_id}` (original evidence IDs and relationship reasons). Responses use the existing `success`/`data`/`pagination` envelope; unavailable storage returns a sanitized HTTP 503.

## Validation

- Windows offline: `cd backend; .\.venv\Scripts\python.exe -m pytest -q` — **70 passed, 13 skipped**, one existing Starlette deprecation warning.
- Ubuntu WSL2 offline: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q` — **70 passed, 13 skipped**, the same warning.
- Windows real PostgreSQL: `NETRCA_RUN_CORRELATION_DB_TESTS=1 .\.venv\Scripts\python.exe -m pytest -q tests/test_correlation_database_integration.py` — **3 passed**. The first test ingested a real Phase 6 event/metric, persisted a Phase 8 anomaly, grouped and reused an incident, verified idempotency/severity/separation, and rolled back. The second provoked a real FK failure and verified rollback. The third verified the transaction advisory lock excludes a second connection until rollback. The linked database was intermittently slow; one combined run and one diagnostic run were interrupted during a database wait and are not counted as passes.
- Ubuntu WSL2 real PostgreSQL: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_CORRELATION_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest -q tests/test_correlation_database_integration.py` — **3 passed**.
- Mininet tests were not run: Phase 9 operates on stored evidence and does not require a live lab. No Phase 9 Mininet bridge or interface was created.
- Migration preflight rollback and live schema/security assertions: passed. `git diff --check` and `git diff --cached --check` both passed. The unrelated `.gitignore` change remained unstaged, and `git status --short -- Instruction` showed no instruction-document changes.

The 13 default skips are opt-in database/Mininet/fault integration checks and an unavailable optional scikit-learn path where applicable; the three Phase 9 PostgreSQL tests were run separately with their opt-in flag. No failing test was skipped to claim success.

## Limits

Correlation is a conservative grouping rule, not causal inference. It currently accepts explicit stored IDs, not a background scan. Phase 6 does not yet ingest service-only events; the service rule is available only when such validated stored evidence exists. Original `incident_events` permits an event in multiple incidents by schema design; the repository detects ambiguous existing membership and refuses to assign it silently. The approved anomaly table enforces one incident per anomaly. The current local-only control header is not production authentication. Stale Phase 8 findings cannot be grouped unless their original metric observation falls within the configured maximum age. The API does not automatically resolve or close incidents.
