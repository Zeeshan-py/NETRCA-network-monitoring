# Phase 4 topology engine

The topology engine represents PostgreSQL `devices` and `links` as a NetworkX
undirected graph. Device and link records use the UUIDs from the Phase 2 schema.
It detects duplicate device IDs/names/addresses, duplicate link IDs and
undirected endpoint pairs, self-links, and links to missing devices. Its
validation result lists connected components. A disconnected network is
reported as multiple components, rather than silently called invalid.
Validated graphs support neighbor and shortest-path queries. Physical link
endpoints do not imply upstream/downstream direction.

`TopologyStore` reads and creates devices and links in PostgreSQL using the
existing bounded transaction layer. Device names and IPs also have database
uniqueness constraints. Link creation uses a transaction-scoped advisory lock
and rejects an existing endpoint pair in either order. A snapshot stores the
currently persisted nodes and links in the existing `topology_snapshots` table;
creation validates the graph first. Snapshot reads support a bounded `limit`.

The existing `GET /api/v1/topology` still returns the live Phase 3 Mininet
view by default and still requires a running simulator. Add `?source=stored`
to retrieve the persisted graph and its components. `GET /api/v1/devices`,
`GET /api/v1/devices/{id}`, `GET /api/v1/links`, `GET /api/v1/links/{id}`,
and `GET /api/v1/topology/snapshots` read persisted records. `POST /devices`,
`POST /links`, and `POST /topology/snapshots` create them. All of these routes
are local-only. Writes additionally require `X-NetRCA-Local-Control: 1` and
`NETRCA_TOPOLOGY_WRITES_ENABLED=true`; the default is false. Responses use
the existing success/error envelope. This local gate is a development control,
not user authentication. Keep the API bound to loopback; do not expose these
routes through a public proxy.

The Phase 3 projection helper `from_mininet()` assigns deterministic UUIDv5
graph IDs to simulator names, preserves live link state and interfaces, and
marks devices `PRESENT`. It does **not** write rows to PostgreSQL or claim
that a present device is healthy. The runtime UUIDs are not persisted IDs.
There is no automatic synchronization between the Mininet lab and stored
topology, and no user-supplied topology is sent to Mininet.

From `backend/`, run offline tests with `python -m pytest tests/test_topology.py
-q`. The real database integration test is opt-in with
`NETRCA_RUN_TOPOLOGY_DB_TESTS=1 python -m pytest
tests/test_topology_database_integration.py -q`; its inserted records and
snapshot are rolled back. Run the existing real Mininet suite in Ubuntu with
`NETRCA_RUN_MININET_TESTS=1 python -m pytest -q`. See
[PHASE4_REPORT.md](PHASE4_REPORT.md) for the results on this workstation.

Phase 4 does not implement update/delete endpoints, frontend graph rendering,
automatic discovery or sync, monitoring, faults, RCA, or AI. Persistent writes
should remain disabled until the developer deliberately enables the local lab.

## Phase 10 structural analysis

Phase 10 reuses the validated Phase 4 undirected graph and its UUID identifiers.
`GET /api/v1/topology/analysis`, `/topology/path`,
`/topology/devices/{device_id}/neighbors`, and `/topology/importance` accept
`source=live|stored` (default `live`, matching the Phase 4 topology route).
The live source requires a running simulator and uses deterministic runtime
UUIDs; the stored source uses database UUIDs. They are separate identity spaces.
`GET /api/v1/incidents/{incident_id}/topology-context` uses **stored** topology
only, since incident evidence references persisted IDs. All routes are read-only
and local-only. See [PHASE10_REPORT.md](PHASE10_REPORT.md) for examples and tests.

Connectivity and shortest paths describe physical adjacency, including links
whose recorded status is `DOWN`; they are not traffic reachability or live
connectivity probes. A disconnected graph remains valid. Degree is the number
of immediate physical neighbors. Betweenness measures how often a device lies
on shortest paths; it is skipped above 128 devices. Articulation points and
bridges identify single nodes or links whose removal increases the number of
components. These are structural properties, not failure predictions or root
causes. Incident context maps directly referenced devices and links, then shows
one-hop neighbors of referenced devices and endpoints of referenced links. It
marks missing IDs and unmapped service IDs explicitly; it does not traverse
dependencies or infer causality.
