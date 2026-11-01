# Phase 4 implementation report — 2026-10-13

## Scope and design

Read the original `Instruction/` architecture, ERD, tech stack, API design,
security, SRS, and PRD before changes. Inspected the Phase 1–3 repository,
Phase 2 schema/connection layer, Phase 3 implementation, and both network
guides. No file under `Instruction/` was modified. Reused the existing
FastAPI envelope, local-only simulator gate, PostgreSQL transaction helper,
Mininet runtime topology view, and Phase 2 tables. No new migration was
needed.

Added `backend/app/topology/` models, a NetworkX graph, and a PostgreSQL
store. Graph validation checks stable UUIDs, unique device names/addresses,
endpoint existence, self-links, and duplicate physical links in either
direction. Connected components are reported; neighbors and shortest paths
are available for validated graphs. The store creates/retrieves devices,
links, and topology snapshots. The snapshot contains validated persisted
nodes and links; it does not represent the current Mininet state.

Extended `GET /api/v1/topology` with `source=stored`, preserving its live
default. Added local-only device, link, and snapshot read/create routes.
Writes require the local control header and an explicit configuration opt-in,
which defaults to disabled. Input is validated before storage; database
errors remain sanitized. The Mininet projection provides stable runtime
UUIDv5 identifiers without writing to the database or inventing health.

## Verification

| Check | Result |
| --- | --- |
| Windows `python -m pytest tests/test_topology.py -q --tb=short` | 6 passed |
| Windows opt-in real PostgreSQL topology test | 1 passed; created rows and snapshot rolled back |
| Ubuntu `NETRCA_RUN_MININET_TESTS=1 python -m pytest -q --tb=short` | 32 passed, 1 skipped (database opt-in test), one Starlette deprecation warning |
| Post-test OVS bridges and Linux interfaces | No OVS bridges; only `lo` and `eth0` |

The database test verified real schema access, create/get for UUID devices and
links, an IP address, reverse duplicate detection, invalid endpoint rejection,
snapshot creation/retrieval, and rollback. The Ubuntu suite ran both real
Phase 3 Mininet integration tests. The Windows unit/API tests cover graph
validation, components, relationships, stable simulator projection, API
creation/retrieval, local access gates, and error cases.

## Limits and next step

There is no automatic Mininet-to-database synchronization. The simulator
remains fixed and explicitly opt-in. The stored graph and live graph are
different sources with different IDs; callers must choose the source. CRUD
update/delete, filtering/pagination beyond snapshot limit, authenticated
multi-user access, frontend visualization, and topology history beyond
snapshots are deferred. No Phase 5 monitoring, anomaly detection, RCA,
Gemini, or fault injection was added.

Next step: review this local Phase 4 implementation and decide whether to
approve a commit. Do not start Phase 5 without explicit approval.
