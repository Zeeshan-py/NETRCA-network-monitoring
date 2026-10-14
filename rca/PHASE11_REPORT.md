# Phase 11 report — explainable root-cause analysis

## Architecture and changes

The `Instruction/` architecture, ERD, tech stack, API design, security, SRS,
PRD, preview, and proposal documents were inspected. Phase 6 validated events
and metrics, Phase 8 persisted metric anomalies, Phase 9 incident memberships,
and Phase 10 stored physical-link graph analysis are reused. Phase 11 adds a
pure deterministic candidate engine, a transactional PostgreSQL store, and
local-only FastAPI routes. No network simulation, AI, impact, recommendation,
remediation, frontend, or confirmed-root-cause behavior was added.

Files added: `supabase/migrations/20261014000100_phase11_rca_runs.sql`,
`backend/app/rca/{__init__,models,engine,store}.py`, `backend/app/api/rca.py`,
`backend/tests/test_rca.py`, `backend/tests/test_rca_database_integration.py`,
`rca/README.md`, and this report. Files modified: `backend/app/main.py`,
`backend/app/core/config.py`, `backend/.env.example`, root `README.md`, and
`rca/PHASE11_SCHEMA_PROPOSAL.md` (approval/application status only). The
pre-existing `.gitignore` edit and all original `Instruction/` files were
preserved.

## Approved migration and live verification

The configured database target and local Supabase link both identify project
`oeizpptglvtnljkheatq`, without printing credentials. Before application,
the target reported database/user `postgres`, PostgreSQL 17.11, the three
required roles, `CREATE` privilege, four expected migration versions, and no
`public.rca_runs`. The migration file matched the approved proposal SQL
exactly. Executing it in a transaction succeeded; rollback removed the table.
The cached Supabase CLI 2.120.0 listed only `20261014000100` as pending and
`migration up --linked` applied exactly that version. A post-application list
showed all five local/remote versions matched. No `db push`, unrelated
migration, or schema reset was run.

Read-only live checks passed for eight required columns and nullability; the
incident foreign key, primary key, unique fingerprint key, and check
constraints; all three expected indexes; RLS enabled; zero policies; no
`anon`/`authenticated` SELECT or INSERT access; and service-role SELECT/INSERT
access. A later read-only check found zero `phase11-%` fixture devices and
zero `rca_runs` after the rollback tests. The RCA engine leaves
`root_causes`, `root_cause_evidence`, `incidents.confidence`, impact,
recommendations, and AI tables untouched.

## Evidence and ranking

The store reads incident memberships, validates original events and anomaly
metrics through Phase 6/8/9 validators, and loads stored topology in a bounded
transaction. Invalid evidence is skipped and reported. A transaction-scoped
lock serializes Phase 11 writers and uses Phase 9's lock first so correlation
cannot alter memberships during an RCA read. At most 100 events and 100
anomalies are processed per run; larger incidents return HTTP 409. The
fingerprint includes validated observations, topology IDs/statuses, rule
version, timing window, and limitations. A unique key reuses identical runs;
later analyses update `last_analyzed_at` with wall-clock time. Distinct inputs
create historical runs. Inconclusive runs persist normally.

The [rule list and exact integer contributions](README.md) are authoritative.
Candidates require direct failure/state-down evidence. Following symptoms and
graph cuts only add support; earlier symptoms and `RESOLVED` events provide
contradictory evidence. Scores are uncalibrated rule points, **not** confidence
probabilities. The engine returns the original event/anomaly IDs, metric IDs
where present, timestamps, topology IDs, rule names, limitations, and stable
candidate ordering. `INCONCLUSIVE` is explicit for no direct evidence or when
contradictions weaken all candidates. Neither the highest score nor a graph
articulation point marks a root cause as confirmed.

## API

| Route | Behavior |
| --- | --- |
| `POST /api/v1/incidents/{uuid}/root-cause/analyze` | Local-only persisted analysis; also requires `X-NetRCA-Local-Control: 1` and `NETRCA_RCA_WRITES_ENABLED=true` |
| `GET /api/v1/incidents/{uuid}/root-causes` | Local-only latest run, including ranked candidates and evidence references |

Both use the existing `success`/`data` or sanitized `error` envelope. A
representative response fragment is:

```json
{
  "success": true,
  "data": {
    "status": "CANDIDATES",
    "result": {
      "status": "CANDIDATES",
      "candidates": [{
        "cause_type": "LINK_FAILURE",
        "target_kind": "LINK",
        "target_id": "00000000-0000-0000-0000-000000000005",
        "score": 6,
        "score_kind": "UNCALIBRATED_RULE_POINTS",
        "supporting_evidence": [{
          "source_type": "EVENT",
          "source_id": "00000000-0000-0000-0000-000000000007",
          "timestamp": "2026-10-14T12:00:00Z",
          "metric_id": null,
          "reason": "DIRECT_FAILURE"
        }]
      }]
    }
  }
}
```

The example is a fragment of the typed response; it omits run ID, timestamps,
fingerprint, other candidate fields, and limitations. An inconclusive run uses
`"status":"INCONCLUSIVE"` with an empty or weak-candidate array and explicit
limitations. Missing incident or run returns 404; malformed IDs return 422;
disabled writes or nonlocal access returns 403; unavailable PostgreSQL returns
503 without server details.

## Tests and operational checks

- Windows full offline: `cd backend; .\.venv\Scripts\python.exe -m pytest -q` — **84 passed, 17 skipped**, one existing Starlette/httpx deprecation warning.
- Ubuntu WSL2 full offline: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q` — **84 passed, 17 skipped**, the same warning.
- Windows real PostgreSQL: `cd backend; $env:NETRCA_RUN_RCA_DB_TESTS='1'; .\.venv\Scripts\python.exe -m pytest tests/test_rca_database_integration.py -q` — **4 passed**.
- Ubuntu WSL2 real PostgreSQL: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && NETRCA_RUN_RCA_DB_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest tests/test_rca_database_integration.py -q` — **4 passed**.
- `git diff --check` — passed. The pre-existing `.gitignore` change was excluded from Phase 11 staging.

The PostgreSQL tests use real inserts and explicit rollback. They cover
candidate and inconclusive persistence, repeat-run idempotency, latest-run
ordering, evidence provenance, a real constraint failure followed by rollback,
and contention on the RCA advisory lock. An initial Windows integration run
had **1 failure, 2 passed**: a new row's transaction-start timestamp sorted
behind a repeated row's wall-clock timestamp. The insert was corrected to use
`clock_timestamp()` and the final Windows and Ubuntu integration runs passed.
The 17 default skips include four new opt-in Phase 11 database tests; the
others are existing opt-in database/Mininet/fault tests and an optional
scikit-learn path where unavailable. Phase 8, 9, and 10 tests passed in both
full suites. Mininet was not started, and no fault or network-state change was
made; no lab cleanup was necessary.

## Limits and final status

There is no incident-log membership, historical topology snapshot bound to
an incident, directed service dependency, calibrated probability, or
independent causality proof. Current stored graph status can differ from the
state when evidence was observed. A direct failure alone may yield a plausible
candidate; an investigator must review it. The local-only control gate is a
development safeguard, not production authentication. Schema-level foreign
keys cannot validate polymorphic evidence IDs in result JSON; the application
validates source records before persistence. No Phase 11 data is written to
confirmed root-cause, impact, recommendation, or AI tables.

The approved migration is applied and verified. The user separately authorized
the Phase 11 commit and push to `main`; the pre-existing `.gitignore` edit
remains unrelated and excluded. No additional schema change or approval is
required.
