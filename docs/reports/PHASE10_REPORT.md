# Phase 10 report — NetworkX graph analysis

## Scope and existing foundation

The repository's architecture, ERD, tech stack, API design, security, SRS, and
PRD documents were read before implementation. Phase 4 already represents
physical links in a NetworkX undirected graph, validates duplicate device/link
IDs, names, addresses and endpoint pairs, rejects self-links and unknown link
endpoints, and returns components, neighbors and unweighted shortest paths.
Its live Mininet projection uses deterministic UUIDv5 identifiers, while its
stored graph uses PostgreSQL UUIDs. Phase 10 adds metadata to that validated
graph and exposes structural measures and incident evidence context through
read-only services. No second topology source, schema change, dependency
change, network-control action, or live lab start was needed. NetworkX was
already required and installed at version 3.7 on Windows and Ubuntu WSL2.

Files added: `backend/app/topology/analysis.py`,
`backend/app/api/graph_analysis.py`, `backend/tests/test_graph_analysis.py`,
and this report. Files modified: `backend/app/topology/graph.py`,
`backend/app/topology/models.py`, `backend/app/main.py`,
`backend/app/correlation/store.py`, `topology/README.md`, and root `README.md`.
The incident detail query now includes the link ID of an anomaly's referenced
metric, if any; collection and correlation logic are unchanged. The original
`Instruction/` files and pre-existing `.gitignore` edit were left untouched.

## Rules and API

Validated devices become nodes with IDs, names, types, statuses and active
flags. Validated physical links become undirected edges with IDs, endpoints,
statuses, interfaces and available measurements. Graph construction sorts
records by ID and does not mutate them. Empty graphs have zero components;
isolated nodes form their own components. An invalid graph returns HTTP 409.
Structural paths include recorded `DOWN` links: a path is physical adjacency,
not a claim of operational reachability. For actual connectivity, use the
existing Phase 3 probe. No directed service dependencies are inferred.

All routes require loopback access and an allowed local origin, and return the
existing `success`/`data` envelope. The first four accept `source=live|stored`
with `live` as the default; a stopped lab returns the existing network error,
and unavailable stored data returns a sanitized 503.

| Route | Result |
| --- | --- |
| `GET /api/v1/topology/analysis?source=stored` | Physical graph nodes, links, connected flag and components |
| `GET /api/v1/topology/path?source=stored&source_id={uuid}&destination_id={uuid}` | Device and link IDs along a shortest path, hop count, or `connected:false` and `hops:null` |
| `GET /api/v1/topology/devices/{uuid}/neighbors?source=stored` | Immediate neighbor IDs, link IDs and recorded link status |
| `GET /api/v1/topology/importance?source=stored` | Articulation device IDs, bridge link IDs, degree and normalized betweenness |
| `GET /api/v1/incidents/{uuid}/topology-context` | Directly referenced stored IDs, one-hop context, evidence IDs and missing/unmapped IDs |

For example, a stored chain A–B–C yields a path response shaped as
`{"success":true,"data":{"directed":false,"semantics":"PHYSICAL_TOPOLOGY","source_id":"A-uuid","destination_id":"C-uuid","connected":true,"device_ids":["A-uuid","B-uuid","C-uuid"],"link_ids":["AB-uuid","BC-uuid"],"hops":2}}`.
The placeholders denote actual UUID fields, not literal valid response values.
An incident context response has `source:"stored"`, an `evidence` array with
original event/anomaly IDs and found flags, `referenced_device_ids`,
`referenced_link_ids`, `context_device_ids`, `context_link_ids`,
`missing_device_ids`, `missing_link_ids`, and `unmapped_service_ids`.
Unknown device IDs return 404 and malformed UUIDs or source names return 422.

Articulation devices and bridge links are those whose removal increases the
number of connected components. Degree counts direct neighbors. Normalized
betweenness describes a node's position on shortest paths and is skipped for
graphs above 128 nodes to bound request cost. These values are structural
importance, not impact, failure likelihood, or root cause. Incident context
uses only directly stored device/link references and the endpoints or immediate
neighbors supported by those links. It does not infer multi-hop dependencies.
Missing references are reported, and service references remain unmapped because
Phase 4 has no verified service-to-topology relationship. Runtime Mininet UUIDs
are never matched to stored incident evidence.

## Validation

- Windows: `cd backend; .\.venv\Scripts\python.exe -m pytest -q` — **77 passed, 13 skipped**, one Starlette/httpx deprecation warning.
- Ubuntu WSL2: `cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend" && /home/zeeshan/netrca-venv/bin/python -m pytest -q` — **77 passed, 13 skipped**, the same warning.
- Focused Windows compatibility check: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_graph_analysis.py tests/test_topology.py tests/test_anomaly.py tests/test_correlation.py -q` — **29 passed, 1 skipped**, one warning, after fixing a test fixture that omitted required link interface fields.
- `git diff --check` — passed. No file was staged, committed or pushed.

The 13 default skips are opt-in database and Mininet/fault integration tests,
plus an optional scikit-learn test where unavailable. No test was skipped to
conceal a failure. Phase 4 API and Phase 8–9 tests ran in the full suites and
passed. Phase 10's new API tests use explicit in-memory fixtures; stored graph
and incident routes were **not** independently exercised against the live
database in this phase. The database schema and migration history were inspected
read-only; no migration was applied. Real Mininet was not required for the
structural service, so no lab was started and no Phase 10 cleanup was needed.

## Limits and status

There is no automatic Mininet-to-database synchronization, no operational
reachability guarantee from a graph path, no service dependency graph, and no
RCA conclusion. The API's local-only gate remains a development control, not
production user authentication. The pre-existing `.gitignore` modification
remains unstaged. Phase 10 work is local and uncommitted; review is the next
step. There is no blocker requiring a migration or approval to complete this
read-only phase.
