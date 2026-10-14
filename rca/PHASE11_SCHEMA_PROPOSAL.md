# Phase 11 RCA persistence proposal — approved and applied

The user approved this exact additive schema on 2026-10-14. It was saved as
`supabase/migrations/20261014000100_phase11_rca_runs.sql`, validated inside a
rolled-back transaction, and applied to the verified linked database through
`supabase migration up --linked`. See [PHASE11_REPORT.md](PHASE11_REPORT.md).

## Verified relationships and gap

Phase 9 joins `incident_events` to validated Phase 6 events and
`incident_anomalies` to Phase 8 anomalies. Anomalies may reference an original
metric and/or event; metrics identify a stored device or link. Phase 10's graph
uses stored device/link UUIDs for incident context. Logs have device/service
identities but **no direct incident membership**, so they cannot be silently
treated as incident evidence. Runtime Mininet UUIDs are not database UUIDs.

The initial migration and read-only checks of the linked PostgreSQL database
agree: `root_causes.confidence` is `NOT NULL` with a 0–1 check;
`root_cause_evidence` requires a `root_cause_id`; `incidents` has only nullable
`root_cause_summary` and `confidence`, not an RCA run record. There is no
`rca_runs` table. All four existing migrations through `20261013000102` are
recorded. The five inspected RCA/impact/AI tables have RLS enabled, no policies,
no `anon` or `authenticated` SELECT privilege, and a service-role INSERT grant.
The inspected incident, root-cause, and evidence tables currently contain zero
rows. No database write or migration was performed during the inspection.

A deterministic rule score is an **uncalibrated ranking value**, not a
probability. Storing it as `root_causes.confidence`, or inventing a zero-value
root-cause row for an inconclusive result, would misrepresent the finding.
Storing nothing for inconclusive runs would make “latest result” unreliable,
especially after an earlier candidate result. The smallest safe additive
change is one table for immutable analysis content and an updated last-run time.
Candidate evidence IDs and timestamps remain in the typed `result` JSON object
after application-layer validation. This follows the existing polymorphic
evidence-reference pattern; it does not add fake foreign keys to unrelated
evidence tables. `root_causes` and `root_cause_evidence` would remain untouched.

## Exact proposed SQL

```sql
CREATE TABLE public.rca_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id uuid NOT NULL REFERENCES public.incidents(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    analysis_version text NOT NULL
        CHECK (btrim(analysis_version) <> '' AND length(analysis_version) <= 64),
    input_fingerprint text NOT NULL
        CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN ('CANDIDATES', 'INCONCLUSIVE')),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_analyzed_at timestamptz NOT NULL DEFAULT now(),
    CHECK (last_analyzed_at >= created_at),
    UNIQUE (incident_id, analysis_version, input_fingerprint)
);
CREATE INDEX rca_runs_incident_latest_idx
    ON public.rca_runs (incident_id, last_analyzed_at DESC, id DESC);
ALTER TABLE public.rca_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rca_runs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.rca_runs TO service_role;
```

The application would fingerprint canonical **validated stored** incident
evidence plus relevant stored topology and an analysis-version identifier.
Repeated identical analysis would reuse its row under a transaction-scoped
advisory lock and update only `last_analyzed_at`; a changed evidence/topology
input would create a new historical run. The result JSON would include status,
ranked candidate IDs/types, integer rule scores with named contributions,
supporting and contradictory original evidence IDs/timestamps, and explicit
limitations. It would contain no fabricated calibrated confidence, impact,
AI result, or confirmed root-cause field. Application code would validate every
polymorphic source ID against the original stored row before persistence.

## Proposed execution and rollback checks after approval

1. Reverify target project/database identity, migration history, role grants,
   and absence of `public.rca_runs` without printing credentials.
2. Save **only** this SQL as the next migration and execute it in a transaction
   that is rolled back; verify the table disappears after rollback.
3. Apply only that migration through the repository's migration workflow (no
   `db push`). Inspect columns, constraints, index, RLS, policies, and grants.
4. Implement the deterministic engine, transactional store, local-only guarded
   POST and read-only GET routes, then run unit, API, Windows, Ubuntu WSL2, and
   opt-in real PostgreSQL rollback/concurrency tests.

Dropping an applied table is not an automatic safe rollback after data exists.
If post-application verification fails, stop and report it rather than deleting
the table or touching unrelated schema. No other schema change was approved or
applied. The later user instruction separately authorized implementation,
commit, and push to `main`.
