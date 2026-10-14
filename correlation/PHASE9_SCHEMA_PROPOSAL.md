# Phase 9 reviewed schema proposal

**Status update (2026-10-14):** The owner approved this exact additive schema. It was saved as `supabase/migrations/20261013000102_phase9_incident_anomalies.sql`, validated in a rolled-back transaction, and applied to the verified linked project with `npx supabase migration up --linked`. The paragraphs below preserve the pre-approval rationale and SQL for review; see `PHASE9_REPORT.md` for live verification.

Phase 9 implementation is paused before schema changes. Read-only `information_schema.columns` and `pg_constraint` queries confirmed the relevant columns and constraints in the reachable linked PostgreSQL database, including that `public.incident_anomalies` is absent. The existing `public.incident_events` table retains event IDs, sequence numbers, and relationship reasons. Phase 8 persists metric-based findings in `public.anomalies` with `metric_id` and usually no `event_id`. No existing table has both `incident_id` and `anomaly_id`. Putting incident IDs in anomaly metadata or inventing an event for each anomaly would lose relational integrity or change the meaning of the original evidence. `root_cause_evidence` cannot be used because it requires a root-cause record, which belongs to Phase 11.

The smallest additive migration is one join table. It preserves the original tables and does not create root causes, impact records, or synthetic events. Proposed SQL for review only; it has **not** been applied locally or remotely:

```sql
CREATE TABLE public.incident_anomalies (
    incident_id uuid NOT NULL REFERENCES public.incidents(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    anomaly_id uuid NOT NULL REFERENCES public.anomalies(id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    relationship_type text NOT NULL CHECK (btrim(relationship_type) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (incident_id, anomaly_id),
    UNIQUE (anomaly_id)
);
CREATE INDEX incident_anomalies_incident_idx
    ON public.incident_anomalies (incident_id, created_at);
ALTER TABLE public.incident_anomalies ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.incident_anomalies FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.incident_anomalies TO service_role;
```

The primary key prevents repeated membership; the unique anomaly key prevents the same finding being silently assigned to two incidents. Before any eventual deployment, inspect the linked database's applied migrations and roles, review a dry run, and test the migration in a rollback transaction. Do not run `db push` until specifically approved.

## Planned implementation after approval

1. Add a pure Python correlation engine over validated stored Phase 6 events and Phase 8 anomalies. Use only explicit shared device, link, service, event-to-anomaly, metric-to-anomaly, or known link-endpoint relationships, bounded by a configurable time window. Time alone never establishes a relationship. Skip missing/invalid timestamps, stale or unknown evidence, and duplicate IDs; do not infer multi-hop dependencies.
2. Add a transactional repository that serializes correlation runs, reuses a related `DETECTED` or `INVESTIGATING` incident, stores reasons in `incident_events.relationship_type` and `incident_anomalies.relationship_type`, and handles repeated runs without duplicate incidents or memberships. Incident severity is the highest valid evidence severity; a new incident begins as `DETECTED`. Do not populate root-cause, confidence, impact, or AI fields.
3. Add local-only `POST /api/v1/events/correlate` behind `X-NetRCA-Local-Control: 1` and an opt-in write flag. Add paginated `GET /api/v1/incidents` and `GET /api/v1/incidents/{id}` with original evidence references. Follow existing API response and sanitized database-error conventions.
4. Add focused deterministic unit/API tests and opt-in PostgreSQL integration tests that execute real transactions and roll back. Run Windows and Ubuntu WSL2 suites, `git diff --check`, and update the Phase 9 report. Mininet is not needed for stored-evidence correlation and will not be started solely for these tests.

This proposal is not evidence that incident persistence or grouping works. The configured database connection check was reachable during inspection, but no Phase 9 write or integration test has run.
