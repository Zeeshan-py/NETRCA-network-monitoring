# Phase 6 evidence pipeline

Phase 6 stores observations from the existing on-demand Phase 5 collector in
PostgreSQL. It does not poll in the background. The Phase 5 monitoring routes
remain read-only. The controlled collection routes below require a running
Mininet lab, matching active device names in `public.devices`, and database
access. They do not create topology records. Link state is stored only when
exactly one stored link matches its endpoint devices and interface names; an
unmapped link is counted in the response, not assigned to another link.

## Data flow and schema

`POST /api/v1/pipeline/collect` obtains a Phase 5 snapshot, validates it, and
atomically inserts available readings into `public.metrics`. State values are
`1` for UP and `0` for DOWN. `INTERFACE_STATE` belongs to a device and names
an interface in metadata; `LINK_STATE` belongs to a link. `RX_BYTES`,
`TX_BYTES`, `RX_PACKETS`, `TX_PACKETS`, `RX_ERRORS`, and `TX_ERRORS` are
cumulative counters, never throughput rates. Missing/UNKNOWN readings produce
no metric; a measured zero is stored as zero. All rows preserve the Phase 5
UTC observation timestamp and the `mininet_snapshot` source. A partial
snapshot creates one active `COLLECTION_FAILURE` event until a complete
snapshot resolves it. A verified UP-to-DOWN interface/link transition creates
an `INTERFACE_FAILURE`/`LINK_FAILURE` event. Initial DOWN state alone is not a
transition. A subsequent UP transition resolves that event.

`POST /api/v1/pipeline/probe` accepts the same bounded JSON as the Phase 5
host-pair probe:

```json
{"source":"h1","destination":"h2","count":2,"timeout_seconds":2}
```

It stores measured `LATENCY` (ms), `PACKET_LOSS` (%), and route `AVAILABILITY`
(%: 100 reachable, 0 unreachable) against the source device, with the target
name in metadata. A timed-out or unavailable probe stores no invented metric;
it creates an active `PROBE_TIMEOUT` or `PROBE_FAILED` event. Repeated active
failures are deduplicated. A successful probe resolves the active failure.
This is route availability for a specific source/target pair, not a device
uptime percentage.

`public.logs` accepts structured records only. Phase 6 has no Mininet log
reader, so it does not manufacture system logs. Its current log source is a
bounded, operator-submitted record. The schema requires a device or service;
it has no direct incident reference. Supported log severities are `INFO`,
`WARNING`, `ERROR`, and `CRITICAL` (the actual PostgreSQL constraint does not
permit `DEBUG`). Event severities are `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
Event source, interface/target, observation key, and dedup key are stored in
existing JSONB metadata. The two Phase 6 migrations extend the metric type
check and add indexes for observation and active-event keys; no new table or
public database privilege was added.

Metric and log observation keys are unique for all time. Resubmitting the
same content with the same key returns a duplicate count; changing the
content under that key returns a conflict. Active event keys are unique until
their event is resolved, allowing a later occurrence. Collection operations
are serialized within the existing Mininet manager; database insertion uses a
transaction and a PostgreSQL advisory lock for state transitions. These keys
deduplicate observations only; Phase 9 event correlation is not implemented.

## Local API and configuration

The read endpoints are `GET /api/v1/metrics`, `GET /api/v1/logs`, and
`GET /api/v1/events`. All accept `page` (1–10000), `limit` (1–100, default 50),
`device_id`, and timezone-aware `from`/`to` timestamps. Metrics and events
also accept `link_id`; metrics accept `metric_type`, logs `severity`, and
events `event_type`. Results are newest first, with `pagination` containing
page, limit, total, and pages. Empty history is returned as an empty list;
unavailable storage returns HTTP 503.

`POST /api/v1/metrics` accepts `{"items":[...]}` with 1–100 normalized
measurements. `POST /api/v1/logs` and `POST /api/v1/events` accept one
structured record. These operator APIs require explicit resource UUIDs,
timestamp, source, and observation/dedup key. Operator metric source is
`manual`; operator log/event source is `operator`. Internal Mininet source
labels cannot be submitted through these routes. This preserves provenance:
operator data remains distinguishable from collected data. Message length is
bounded; multiline text and obvious secret-bearing text are rejected. Raw
command output has no ingestion route.

Every route is loopback-only. All POST routes require
`X-NetRCA-Local-Control: 1` and `NETRCA_PIPELINE_WRITES_ENABLED=true`; writes
are disabled by default. Keep the API bound to `127.0.0.1` with one worker.
`DATABASE_URL` is required only when reading or writing history, and remains
server-side. A missing URL yields HTTP 503 without preventing API startup or
Phase 5 read-only monitoring. `NETRCA_SIMULATION_ENABLED=true` is separately
required to start Mininet. The backend DB role is privileged; the local API
guard is therefore essential. No anonymous Supabase table access was added.

Apply reviewed migrations from the repository root with `npx supabase db push
--linked --skip-vault --dry-run`, then `npx supabase db push --linked
--skip-vault --yes`. The Phase 6 versions are `20261013000100` and
`20261013000101`. Never copy database credentials into source or frontend
configuration.

Run offline tests from `backend/` with `python -m pytest tests/test_pipeline.py`.
Real database tests use `NETRCA_RUN_PIPELINE_DB_TESTS=1`; the combined Windows
PostgreSQL and Ubuntu WSL Mininet test uses
`NETRCA_RUN_PIPELINE_LAB_TESTS=1`. Both database tests roll back their rows.
Existing real Linux Mininet tests use `NETRCA_RUN_MININET_TESTS=1` inside
Ubuntu. See [PHASE6_REPORT.md](PHASE6_REPORT.md) for exact results and limits.
