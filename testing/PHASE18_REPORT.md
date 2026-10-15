# Phase 18 — Realistic Demo Dataset and End-to-End UI Verification

## Executive verdict: PASS WITH FINDINGS

The empty stored topology observed in Phase 17 is an expected empty state caused
by missing stored records, not a frontend graph defect. The read-only production
contracts agree: `GET /topology/analysis?source=stored` reads `public.devices`
and `public.links`, and a direct check of the configured database found zero
records in every dashboard-backed evidence, incident, RCA, and impact table.
The frontend correctly represented that result as an empty disconnected graph.

Phase 18 extends the repository's existing guarded local seed instead of adding
a second demo mechanism. The fixture now supplies a disconnected host, an
incident-anomaly membership, and schema-valid static RCA and impact runs so a
disposable local database can exercise the current topology, incident, RCA, and
impact views. All values are explicitly synthetic and labelled `DEMO` or carry
demo metadata. They do not represent live Mininet collection, anomaly detection,
correlation, deterministic analysis execution, or Gemini output.

## Empty-topology diagnosis

| Finding | Classification | Evidence |
| --- | --- | --- |
| Stored topology was empty | Missing demo data | The configured database contained zero `devices` and zero `links`; `GET /api/v1/topology/analysis?source=stored` returned HTTP 200 with zero devices and links. |
| Graph response/client contract | Expected empty state | The backend returns a valid undirected `PHYSICAL_TOPOLOGY` summary; the Phase 17 client accepts it and displays an empty graph state. |
| Live topology when Mininet is disabled | Backend/configuration limitation | The live source remains unavailable until the isolated Mininet lab is explicitly enabled; no attempt was made to start it. |
| Stored UI data mismatch | Unverified with populated runtime data | The populated browser flow needs the approved local seed environment described below. |

No frontend or backend integration defect was demonstrated. Current API health,
stored graph, network status, metrics, anomalies, and incidents requests all
returned HTTP 200 against the actual local API; the stored records were empty.

## Demo data and isolation

The supported seed runner remains `database/seed_local.py`. It refuses any DSN
that is not explicitly loopback and does not read the backend cloud DSN. The
updated `database/seeds/development_seed.sql` is idempotent through stable UUIDs
and `ON CONFLICT DO NOTHING`. It now includes:

- four devices, including a deliberately isolated host;
- two physical links, one down and one up;
- metrics, log, events, anomaly, incident, and explicit incident memberships;
- static, evidence-linked `rca_runs` and `impact_runs` records;
- topology snapshot, legacy root-cause/impact rows, recommendation, fault fixture,
  and a clearly fake AI-analysis record.

The local seed was not applied persistently during this phase. The configured
database is the linked remote Supabase database, while
`NETRCA_LOCAL_DATABASE_URL` is unset and Docker's daemon is unavailable. Phase
18 therefore did not write persistent demo records to the remote database.

The seed SQL was instead executed inside a rollback-only transaction against the
existing schema. Both the RCA and impact records validated through their current
Pydantic models (`CANDIDATES` and `ASSESSED`), and the temporary isolated-host
row count was zero after rollback. The database schema/seed suite also ran inside
rollback-only transactions and passed.

To perform the remaining populated browser check, start a disposable local
PostgreSQL/Supabase environment, apply the existing migrations locally, set only
the loopback `NETRCA_LOCAL_DATABASE_URL`, run `database/seed_local.py`, and point
the local backend at that disposable database. Do not use the linked/cloud DSN.

## Workflow coverage

Verified with actual API/read-only or rollback-only database operations:

1. Stored topology retrieval and empty-state handling.
2. Schema-valid topology, evidence, incident membership, RCA-run, and impact-run
   fixture construction.
3. Database rollback and absence of temporary data after validation.
4. Frontend contract/component coverage for graph, source switching, evidence
   navigation, incident context, loading, error, and empty states.

Not verified against a populated browser because no disposable local database was
configured:

- rendered node/link selection and disconnected host using a live seeded API;
- populated incident detail navigation in the browser;
- presentation of seeded RCA/impact results in the browser;
- provider-backed Gemini behavior (intentionally not invoked);
- a real Mininet workflow (intentionally not started).

The Phase 15 end-to-end rollback fixture remains the longest existing full-chain
test. It uses real Mininet only in an isolated root Ubuntu lab and a deterministic
provider stub. It was not run in this Windows session because the required WSL
lab was stopped and Phase 18 did not require starting Mininet.

## Tests and commands

| Command | Result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest ../database/tests -q` with `NETRCA_RUN_DATABASE_TESTS=1` | 44 passed; rollback-only live-schema and seed validation. |
| Rollback-only seed model validation | Passed; static `RcaRun` and `ImpactRun` validated, then the transaction rolled back with zero isolated-host rows remaining. |
| `backend/.venv/Scripts/python.exe -m pytest -q` | 106 passed, 25 skipped, 1 pre-existing FastAPI/TestClient deprecation warning. |
| `frontend/npm test -- --run --reporter=dot` | 6 files and 30 tests passed. |
| `frontend/npm run lint` | Passed. |
| `frontend/npm run typecheck` | Passed. |
| `frontend/npm run build` | Passed; `/` and `/_not-found` generated. |
| Read-only local API smoke | Passed: health, stored topology, network status, metrics, anomalies, and incidents returned HTTP 200. |

Skipped: persistent local seed/browser verification because the required
loopback-only local DSN is unset; Mininet E2E because the isolated WSL lab was
not started; live Gemini by explicit Phase 18 restriction. No skipped test is
reported as passed.

## Files changed

- `database/seeds/development_seed.sql` — extends the existing local-only fixture
  with a disconnected component and static current analysis records.
- `database/README.md` — documents the expanded fixture and its non-live limits.
- `database/tests/test_schema.py` — asserts the new seed records required by the
  current dashboard are present.
- `testing/PHASE18_REPORT.md` — this verification report.

No migration, API endpoint, frontend product feature, authentication control,
Gemini configuration, fault control, or Mininet configuration changed.

## Final state

`git diff --check` was run after the Phase 18 report update. No Phase 18 files
are staged, committed, or pushed. The pre-existing `.gitignore` modification and
the local Next.js-generated `frontend/AGENTS.md` file remain preserved and
unstaged.
