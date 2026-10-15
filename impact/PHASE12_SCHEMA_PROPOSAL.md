# Phase 12 impact analysis persistence proposal — approved and applied

## Verified gap

The linked project is `oeizpptglvtnljkheatq`; its database reports PostgreSQL
17.11 and migration versions through `20261014000100`. Read-only catalog checks
confirm `public.impact_records` requires a non-null severity and at least one
device, link, or service foreign key. It has no RCA-run identifier, uniqueness
key for repeated analyses, or complete failure-chain result field. Its optional
`metadata` cannot safely represent an analysis with no mappable component:
creating a row would require inventing both a target and severity. Updating
`rca_runs.result` would mutate the prior RCA finding and mix independent rule
versions. Neither approach preserves honest inconclusive results.

The smallest additive solution is one analysis-run table. Its mandatory
`rca_run_id` foreign key provides the incident through `rca_runs.incident_id`
without a redundant incident column that could contradict it. The validated
result JSON will retain original evidence IDs, candidate ID, affected entity
IDs, classification and explanation for every chain edge, explicit unknowns,
and a frozen topology input summary. `topology_fingerprint` identifies the
exact stored device/link/service mapping used. No historical topology snapshot
is assigned unless one is demonstrably the source of that RCA run; Phase 11
currently reads the stored graph, not a snapshot. Existing `impact_records`
remain untouched.

## Exact proposed migration

Proposed filename: `supabase/migrations/20261014000101_phase12_impact_runs.sql`.
The following is the approved SQL, applied without changes.

```sql
CREATE TABLE public.impact_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rca_run_id uuid NOT NULL REFERENCES public.rca_runs(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    analysis_version text NOT NULL
        CHECK (btrim(analysis_version) <> '' AND length(analysis_version) <= 64),
    input_fingerprint text NOT NULL
        CHECK (input_fingerprint ~ '^[0-9a-f]{64}$'),
    topology_fingerprint text NOT NULL
        CHECK (topology_fingerprint ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN ('ASSESSED', 'INCONCLUSIVE')),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_analyzed_at timestamptz NOT NULL DEFAULT now(),
    CHECK (last_analyzed_at >= created_at),
    UNIQUE (rca_run_id, analysis_version, input_fingerprint)
);
CREATE INDEX impact_runs_rca_latest_idx
    ON public.impact_runs (rca_run_id, last_analyzed_at DESC, id DESC);
ALTER TABLE public.impact_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.impact_runs FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.impact_runs TO service_role;
```

## Application and verification

The target project, migration history, roles, privileges, and table absence
were rechecked. The saved migration exactly matched this SQL block. It
executed inside a transaction that was rolled back; a later query confirmed
the table was absent. `supabase migration list --linked` showed only this
version pending, and `supabase migration up --linked` applied it. Live catalog
checks confirmed the table, foreign key, constraints, indexes, RLS, lack of
client grants/policies, and service-role access. No `db push` was used.

Phase 12 implements the deterministic impact engine, a transactional
idempotent store keyed to the RCA run, and the existing local-only guarded
`POST /api/v1/incidents/{id}/impact/analyze` plus read-only impact and
failure-chain routes. An inconclusive RCA run may yield an `INCONCLUSIVE`
impact run; a candidate alone never proves downstream or user impact. See
[PHASE12_REPORT.md](PHASE12_REPORT.md) for validation and limitations.
