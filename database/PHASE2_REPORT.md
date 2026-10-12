# Phase 2 implementation report — 2026-10-12

## Documentation and initial state

Read the project request and all relevant original files in `Instruction/`:
`ERD.md`, `ARCHITECTURE.md`, `TECHSTACK.md`, `APIDESIGN.md`, `SECURITY.md`,
`SRS.md`, `PRD.md`, `NetRCA_Preview.html`, and
`NetRCA_AI_Initial_Project_Proposal.docx`. The ERD is the starting schema
contract. No original instruction file was changed.

Before implementation, the repository had only `supabase/config.toml` and a
linked CLI project for database setup. It had no migrations, public tables,
seed or database access code. The Phase 1 FastAPI health API, frontend shell,
tests, `.gitignore`, and root README existed as uncommitted files except the
README, which was modified relative to the earlier README-only commit. The
existing ignored `backend/.env` provided a real connection; values were not
copied into tracked files or this report. The remote PostgreSQL version was
17.11, its public schema was empty, and it had no migration history table.

## Schema and migrations

One CLI migration, `supabase/migrations/20261012000100_initial_schema.sql`,
creates all 17 ERD tables: `devices`, `links`, `services`, `device_services`,
`metrics`, `logs`, `events`, `anomalies`, `incidents`, `incident_events`,
`root_causes`, `root_cause_evidence`, `impact_records`, `recommendations`,
`ai_analyses`, `fault_injections`, and `topology_snapshots`.

All use UUID primary keys. Relational references have restrictive foreign
keys, including a composite incident/cause key for recommendations. Uniqueness
covers names/IPs, hosting pairs, incident-event pairs, timeline positions and
duplicate evidence sources. Checks enforce state/severity vocabularies,
required resources, time order, confidence and anomaly score ranges, metric
ranges, service ports and self-link exclusion. TIMESTAMPTZ and JSONB follow the
ERD. Resource/time indexes support latest measurements, log/event timelines,
incident filtering, fault history and topology history. The database guide
explains index choices and the small set of documented ERD/SRS differences.

The migration is dependency ordered and tracked by Supabase CLI. The dry run
listed exactly `20261012000100_initial_schema.sql`, with zero seeds and roles.
`npx supabase db push --linked --skip-vault --yes` applied it successfully to
the linked project. `npx supabase migration list --linked` then showed the
same version locally and remotely. The remote schema contains exactly 17
NetRCA public tables and zero NetRCA data rows after application. No seed
was applied remotely.

## RLS and access

RLS is enabled on all 17 tables. No policies have been created because Phase 1
has no authenticated role model. PUBLIC, anon, and authenticated table
privileges are revoked; a privileged backend DB role can access the tables.
The integration suite verified RLS still filters populated rows if a SELECT
grant is accidentally added in a rollback transaction. The anonymous Data API
request for `devices` returned HTTP 401 after deployment. Authenticated client
authorization and `ADMIN`/`NETWORK_OPERATOR`/`VIEWER` policies are deferred
until trusted identity and role membership are implemented.

## Development seed and configuration

`database/seeds/development_seed.sql` contains 27 linked, stable-ID fixture
rows for an R1 uplink failure. It includes router/switch/server topology,
measurements, log/events, a sample anomaly/incident, ordered timeline, cause,
five evidence types, service impact, recommendation, snapshot, fault record,
and explicitly static AI text. All represent demo data. `seed_local.py`
requires an explicit loopback DSN and refuses remote addresses. Supabase CLI
automatic seeding is disabled. The backend connection layer uses `DATABASE_URL`
only on explicit calls and does not alter the Phase 1 health response.
`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` remain available for future
Data API work. Only variable names are documented; no credential values.

## Validation and regressions

Executed against the real Supabase PostgreSQL server:

- Read-only preflight: connected to PostgreSQL 17.11, with zero public tables.
- Initial migration plus fixture integration suite in a rollback transaction:
  **43 passed**. It checked ERD columns, keys, indexes, RLS/ACL behavior,
  invalid values, relationship integrity, seed repeatability and chronology.
  The DDL and fixtures from this test run were rolled back before CLI push.
- CLI dry run: one migration pending, no seeds; CLI push: succeeded.
- Remote read-only inspection after push: **17 tables, 17 RLS-enabled,
  zero policies, zero data rows, one matching migration history row**.
- Anonymous publishable-key Data API read of `devices`: **HTTP 401**.
- Backend tests: **10 passed** (including 6 database configuration/access
  tests); frontend tests: **3 passed**.
- Frontend typecheck and lint: **passed**.
- Explicit backend diagnostic `python -m app.db.check`: **Database connection: UP**.
- Staging audit: 52 paths reviewed; actual configured publishable key and
  database URL found in **zero staged blobs**. `backend/.env` and Supabase's
  local link file are ignored.

No running Docker daemon was available, so local Supabase `start/reset` was
not exercised. The remote rollback transaction provided actual PostgreSQL
syntax and behavior validation instead. The migration was not run twice
against an already migrated schema. `git diff --check` found no whitespace
errors in Phase 2 files. `git diff --cached --check` reports one existing
Markdown line with intentional two-space line break in the original,
unchanged `Instruction/PRD.md`; the instruction file was preserved.

## Limitations and next step

ERD polymorphic evidence `source_id` cannot be a single foreign key. Seeded
references are validated, but arbitrary future evidence writes and deletion
of their source rows need an application service or a future schema change.
Do not expose evidence mutation endpoints until that is implemented. The
current backend DB role bypasses RLS; endpoint authorization is required
before application data APIs. Local Docker-based reset remains unverified.

Phase 3 has not been started. It requires explicit approval before work begins.

## Acceptance criteria

| Criterion | Status |
| --- | --- |
| Instructions read before implementation; Phase 1 inspected/preserved | Passed |
| 17 ERD entities and relationships | Passed, with documented polymorphic limitation |
| Constraints, history-preserving FKs and query indexes | Passed |
| Versioned Supabase CLI migration | Passed, applied remotely |
| RLS denies anon/authenticated; future RBAC documented | Passed |
| Development fixture isolated from production | Passed |
| Secret-free tracked configuration | Passed; staged blobs audited |
| Actual PostgreSQL validation | Passed, 43 tests |
| Existing backend and frontend regression suites | Passed, 10 and 3 |
| Local Docker reset | Blocked by stopped Docker daemon |
| Phase 3 remains untouched | Passed |

## Files changed for Phase 2

- `supabase/migrations/20261012000100_initial_schema.sql`: schema and access rules.
- `supabase/config.toml`: disable automatic seed loading.
- `database/seeds/development_seed.sql`, `database/seed_local.py`: demo fixture and guarded runner.
- `database/tests/test_schema.py`: actual PostgreSQL integration validation.
- `backend/app/core/config.py`, `backend/app/db/*`, `backend/requirements.txt`,
  `backend/tests/test_database.py`: server-side DB configuration, access and tests.
- `database/README.md`, `database/PHASE2_REPORT.md`, `README.md`: setup and findings.
