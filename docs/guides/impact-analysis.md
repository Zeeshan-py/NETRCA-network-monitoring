# Phase 12 impact and failure-chain rules

Phase 12 reads the latest Phase 11 RCA run for an incident, validates its
original Phase 6/8 evidence and RCA input fingerprint again, then loads the
current stored device/link graph and `device_services` mappings in one
transaction. Runtime Mininet identifiers are never equated to database IDs.
The impact run references the RCA run by foreign key; the incident is obtained
through that run. The result stores original evidence IDs/timestamps, a
topology input summary, and a topology fingerprint. No incident, RCA,
`impact_records`, recommendation, AI, or network-control record is updated.

`OBSERVED` means an incident event or anomaly directly reports the selected
component's failure, passes source validation, matches its RCA evidence ID
and timestamp, and maps to the stored topology. It does **not** confirm the
RCA candidate as the cause. `POTENTIAL` means only a verified one-hop physical
endpoint/adjacency or device-service mapping exists. It does **not** assert
outage, propagation direction, service unavailability, or customer impact.
The edge `step` orders structural exposure outward from the candidate; it is
not a measured chronology. Every chain edge cites its root evidence and
explains the physical or hosting relationship. Counts include both observed
and potential entities; clients must inspect `classification`.

For an evidenced link failure, the link is observed and its two endpoints are
potentially exposed. For an evidenced device failure, its incident links and
one-hop neighbors are potentially exposed. Mapped services on exposed devices
are potentially affected when their device-service association is `UP` or
`DEGRADED`; a `DOWN` association is not treated as active hosting. No second
hop or directed dependency is inferred. An additional directly evidenced
failure in a disconnected component is reported as observed without a
fabricated edge to the leading candidate. A tie for the leading RCA score,
missing current direct evidence,
an unmappable target, invalid topology, or an inconclusive RCA produces an
explicit `INCONCLUSIVE` impact run with no invented entities or severity.
No calibrated probability or impact severity is assigned. User/application
impact stays `UNKNOWN_UNVERIFIED` because no incident-scoped application or
user observations or directed dependency graph exists.

`POST /api/v1/incidents/{id}/impact/analyze` requires loopback access, the
existing origin check, `X-NetRCA-Local-Control: 1`, and
`NETRCA_IMPACT_WRITES_ENABLED=true`. The flag defaults to false.
`GET /api/v1/incidents/{id}/impact` and
`GET /api/v1/incidents/{id}/failure-chain` return the latest impact run for
the latest RCA run, both with the standard `success`/`data` envelope.
Missing incident or RCA returns 404, stale RCA inputs return 409, and an
unavailable database returns a sanitized 503. Invalid UUIDs return 422.
The failure-chain route returns the full run so the chain remains attached
to its evidence, classifications, and limitations.

Repeated identical analysis reuses one row under transaction-scoped advisory
locks in Phase 9, 11, 12 order. Changed validated evidence or topology
requires a new RCA run or creates a new impact fingerprint. The current
stored graph is a point-in-time input, not a historical incident snapshot.
