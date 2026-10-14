# Phase 11 explainable root-cause candidate analysis

The Phase 11 engine analyzes **stored, validated incident evidence**. An
incident's `incident_events` and `incident_anomalies` identify original Phase 6
events and Phase 8 anomalies. An anomaly's metric can identify a stored device
or link. The engine reuses Phase 9's evidence validators and Phase 10's stored
physical-link graph. It does not use live Mininet UUIDs or infer an incident log
membership from time and device proximity. Results are candidates, never a
confirmed root cause or calibrated probability.

`POST /api/v1/incidents/{incident_id}/root-cause/analyze` requires loopback,
an allowed local origin, `X-NetRCA-Local-Control: 1`, and
`NETRCA_RCA_WRITES_ENABLED=true`. The default flag is false. The POST has no
request body: it reads the incident's current stored memberships. It returns a
persisted `CANDIDATES` or `INCONCLUSIVE` run. `GET
/api/v1/incidents/{incident_id}/root-causes` returns the most recently analyzed
run, including ranked candidates and original evidence references. It is
local-only but read-only. UUIDs and errors use the existing API conventions.
No run returns 404 `RCA_NOT_FOUND`; no incident returns 404
`INCIDENT_NOT_FOUND`; unavailable storage returns sanitized 503.

The integer `score` has kind `UNCALIBRATED_RULE_POINTS`. A direct
`LINK_FAILURE`, `INTERFACE_FAILURE`, or `DEVICE_UNAVAILABLE` event, or a
validated `LINK_STATE`/`INTERFACE_STATE` zero-valued anomaly, seeds a candidate
with **4 points**. Independent direct observations on the same component add
**2 each, capped at 4**. Related symptoms occurring within the configured
window after the direct failure add **1 each, capped at 2**. A graph bridge or
articulation point adds **1** only with a later related symptom. A symptom
preceding the failure subtracts **2**; a `RESOLVED` failure event subtracts
**3**. Scores have a floor of zero. A candidate needs at least 4 points for
the run to have status `CANDIDATES`; otherwise it is `INCONCLUSIVE`.

Each rule lists the exact stored source IDs and timestamps that contributed.
Duplicate event/anomaly IDs and multiple anomaly rows for one metric do not
add points twice. The response lists contradictory references and limitations,
including invalid evidence, missing timestamps, missing topology targets, or
unavailable topology. Ties sort by cause type and target UUID. Graph centrality
alone can never seed a candidate. Physical adjacency provides support, not
directed dependency or causation.

The approved `public.rca_runs` table stores the typed result JSON and a hash
of the validated inputs, relevant stored topology, rule version, and window.
Repeated identical runs reuse one row under transaction-scoped advisory locks
and update its last-analysis time. A changed input creates a separate run. An
inconclusive result is stored without inventing a `root_causes` row or writing
an unsupported confidence value. See [PHASE11_REPORT.md](PHASE11_REPORT.md)
for live schema checks, test commands, results, and limits.
