# NetRCA database foundation (Phase 2)

Supabase PostgreSQL is the persistent store. The initial schema implements all 17
entities from `Instruction/ERD.md`. FastAPI uses Psycopg 3 for direct server-side
SQL. No ORM, application CRUD routes, collectors, RCA algorithms, or AI calls are
introduced by this phase. The existing API health response remains API-only.

## Files and migration workflow

- `supabase/migrations/20261012000100_initial_schema.sql`: the single initial migration,
  including tables, constraints, indexes, update triggers and access restrictions.
- `database/seeds/development_seed.sql`: 27 explicitly simulated fixture rows.
- `database/seed_local.py`: opt-in, loopback-only seed runner.
- `database/tests/test_schema.py`: integration validation with transaction rollback.
- `backend/app/db/connection.py`: bounded, parameterized-query-compatible transactions.
- `backend/app/db/check.py`: explicit connection diagnostic.

Supabase CLI is the only migration system. Its timestamped migration history makes
each file apply once. Do not rerun the SQL manually or edit an already applied
migration; add a new timestamped migration for subsequent changes. No seed file is
registered in `supabase/config.toml`, and automatic seeding is disabled.

## Tools and configuration

Use Python 3.11+, the backend requirements, Node/npm, and Supabase CLI. Docker must
be running for local Supabase. PostgreSQL major version 17 is configured to match
the linked project. CLI authentication is separate from database credentials.

`backend/.env` is ignored by Git. Settings load it relative to the backend folder
regardless of the shell working directory; process environment variables override
the file. Configuration names:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Server-only PostgreSQL DSN; required only when making DB calls |
| `SUPABASE_URL` | Project API URL, retained for Data API verification/future integration |
| `SUPABASE_PUBLISHABLE_KEY` | Data API publishable key; cannot bypass RLS or authenticate the CLI |
| `NETRCA_LOCAL_DATABASE_URL` | Explicit loopback DSN used only by the seed runner |
| `NETRCA_RUN_DATABASE_TESTS` | Set to `1` to enable integration tests |
| `NETRCA_TEST_INITIAL_MIGRATION` | Set to `1` only when testing the initial migration against an empty schema |

No service-role key is required by the direct SQL backend. Obtain DSNs from the
Supabase dashboard, percent-encode special password characters, and keep them out
of shell history, source control, frontend code, and diagnostic output. A session
pooler DSN supports IPv4 development. Backend connections require TLS, use a
10-second connect/query timeout and 5-second lock timeout, and disable prepared
statements so transaction pooler connections can also be used. Connection and SQL
errors are translated to a generic `DatabaseUnavailable` exception. Connections
open only when requested; successful transactions commit, failed ones roll back.

From `backend/`:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m app.db.check
```

The check actually executes `SELECT 1`. A missing/failed connection exits nonzero
and never returns fabricated success. It does not imply schema readiness.

## Local setup and reset

From the repository root, with Docker running:

```powershell
npx supabase start
npx supabase db push --local --skip-vault
```

For a **disposable local database only**, `npx supabase db reset --local` destroys
local data and reapplies migrations. Never add `--linked` or a remote `--db-url` to
reset commands. Automatic seed loading is disabled. Export the local DSN as
`NETRCA_LOCAL_DATABASE_URL` through your local secret configuration, then run:

```powershell
backend/.venv/Scripts/python.exe database/seed_local.py
```

The runner never reads the cloud DSN from `backend/.env`; it requires an explicit
loopback host and pins the actual connection address to loopback. Do not point a
local tunnel at production. The SQL itself is a fixture file: do not manually run
it in a production SQL editor. Stable UUIDs and `ON CONFLICT (id) DO NOTHING` make
reruns preserve existing fixture rows, rather than overwrite changes. A conflicting
name/IP with a different ID fails and rolls back; resolve it in the disposable
database instead of silently overwriting records.

The seed contains a router, switch, server, two links, HTTP service and hosting
relationship, baseline latency and post-failure packet loss, a log, ordered failure
and timeout events, an anomaly fixture, incident, cause, five evidence records,
service impact, advisory recommendation, topology snapshot, fault record, and an
explicitly fake AI explanation. All are labeled DEMO or carry demo metadata. No
Mininet, ML, RCA or Gemini execution is claimed.

## Linked Supabase setup

From the repository root:

```powershell
npx supabase login
npx supabase link --project-ref <your-project-ref>
npx supabase migration list --linked
npx supabase db push --linked --dry-run --skip-vault
npx supabase db push --linked --skip-vault
```

Review pending migrations and confirm the target project before the final push.
Supply the database password through the CLI's secure prompt or secret environment
configuration, never a committed script. Do not pass `--include-seed`. The CLI
records successful migrations in `supabase_migrations.schema_migrations`.

For rollback, prefer a corrective forward migration. Restoring a backup is the
recovery path once real observations exist; there is deliberately no destructive
cloud down-script. Rebuilding with `db reset --local` is the supported clean-slate
development workflow. Test rollback transactions are not a substitute for backups.

## Access control

All 17 tables have RLS enabled, no client policies, and explicit revocation of all
table privileges from `PUBLIC`, `anon`, and `authenticated`. Thus both anonymous
and signed-in browser contexts are denied reads and writes. RLS still denies rows
if a SELECT grant is accidentally added. Internal trigger function execution is
also revoked from public/client roles and its search path is fixed.

The privileged PostgreSQL owner used by the configured backend DSN bypasses RLS;
the service_role role has explicit CRUD privileges and Supabase's BYPASSRLS
behavior. Neither is an end-user authorization mechanism. Never expose either
credential or unrestricted SQL endpoints to a browser. Production deployment
still needs a dedicated least-privilege backend role and server-side authentication.
Future `ADMIN`, `NETWORK_OPERATOR`, and `VIEWER` access must be introduced in a new
migration after trusted role membership/JWT validation exists, with role tests.
This phase deliberately does not invent authorization tables or permissive policies.

## ERD decisions and integrity

- All ERD fields and all 17 requested entities are retained, including entities
  that the ERD's older MVP section calls optional.
- Incident states follow ERD/PRD (`DETECTED`, `INVESTIGATING`,
  `ROOT_CAUSE_IDENTIFIED`, `RESOLVED`, `CLOSED`), not the SRS's `OPEN` spelling.
  Resolved/closed incidents require an end time; end times cannot precede starts.
- `logs.service_id` is the one extra relational column, resolving SRS service-log
  requirements without storing service identity in metadata. Logs require a device
  or service. Log severity follows ERD/PRD; SRS's optional `DEBUG` is not included.
- UUIDs default to `gen_random_uuid()`. Observation times are mandatory inputs;
  creation/update times default to transaction time. Four `updated_at` columns
  are refreshed by a trigger on every update.
- All foreign keys use `RESTRICT` for delete/update; referenced history cannot
  disappear through cascading deletion. Retire devices with `is_active=false`.
  There are no retention/purge jobs in this phase.
- Device names and non-null IPs are unique; self-links are rejected. Parallel
  links remain valid. Device-service pairs and incident-event pairs are unique;
  incident timeline positions are unique and positive. Recommendations use a
  composite FK so a cause must belong to the recommendation's incident.
- Metrics require a device and/or link. Percentage metrics (packet loss, CPU,
  memory, availability) use 0–100; other metrics are nonnegative finite numbers.
  ERROR_RATE is nonnegative with its scale declared by `unit`. Confidence and
  anomaly scores use 0–1. A future Isolation Forest adapter must normalize its
  raw signed score before storage. No inference is implemented here.
- Events may be global (all targets nullable). Event severity uses incident
  severity. Because ERD does not enumerate event statuses, the initial contract
  is `DETECTED`, `ACKNOWLEDGED`, `RESOLVED`. Event/cause/service types stay extensible
  nonempty text; the ERD event list lacks recovery types needed by the SRS.
- Anomalies require a resource/observation reference; impacts and faults require
  at least one target. Multiple target columns can describe a related resource
  context; semantic consistency across supplied targets belongs to future services.
- Evidence retains the ERD's polymorphic `(source_type, source_id)` design.
  **It is not a foreign key.** Source existence and protected source deletion must
  be enforced by future evidence/retention services in the same transaction.
  The validation suite checks every seeded source. This is an explicit limitation
  of the ERD, not a claim that arbitrary polymorphic IDs are database-validated.
  `TOPOLOGY` references `topology_snapshots`. Do not add evidence write/delete
  endpoints until this application validation is implemented.
- JSONB holds flexible metadata/context/topology only. Topology must be an object;
  graph-shape validation belongs to future topology services. Network topology
  state, deterministic analysis and generated text remain separate tables.

Indexes cover ERD time-series patterns plus link/service histories, incident
timelines, evidence sources, recommendations, fault histories and snapshots.
Existing unique index prefixes already cover incident/cause/evidence junction
lookups; duplicate single-column indexes are avoided. No blanket JSONB indexing
or partitioning is added before workloads justify it.

## Validation

Tests connect using `DATABASE_URL` and require a privileged development/test role.
Run only against a controlled project: the suite writes demo fixtures **inside a
transaction that is always rolled back**, including on assertion failure. It never
commits seed records. Prefer local Supabase when available. On an empty schema,
this command validates migration syntax and behavior without persisting DDL:

```powershell
$env:NETRCA_RUN_DATABASE_TESTS = '1'
$env:NETRCA_TEST_INITIAL_MIGRATION = '1'
backend/.venv/Scripts/python.exe -m pytest database/tests -q
Remove-Item Env:NETRCA_TEST_INITIAL_MIGRATION
```

After migrations are applied, run the same suite without
`NETRCA_TEST_INITIAL_MIGRATION`. Tests verify all ERD columns, timestamp types,
primary keys, foreign key actions, indexes, RLS/ACL denial, seed idempotency,
timeline/evidence consistency, invalid values, cross-incident references and
history-preserving deletion. Test grants and fixture changes roll back too.

Regression commands:

```powershell
cd backend
.venv/Scripts/python.exe -m pytest -q
cd ../frontend
npm test
```

The integration suite is skipped unless explicitly opted in. See
`database/PHASE2_REPORT.md` for actual execution results and remaining limitations.
