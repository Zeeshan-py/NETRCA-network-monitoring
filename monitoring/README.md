# Phase 5 network monitoring

Phase 5 observes the **running, fixed Mininet lab** without changing its
topology. The monitoring service is on demand. It does not collect continuously
or write to Supabase, and it does not need database credentials. The returned
Pydantic models (`MonitoringSnapshot` and `ProbeReading`) are the interface for
later data processing; this phase does not implement that pipeline.

`GET /api/v1/network/monitoring` returns a UTC-timestamped snapshot with the
network state, devices, interfaces, links, and a collection status of
`COMPLETE`, `PARTIAL`, or `UNAVAILABLE`. A stopped or disabled lab returns
`UNAVAILABLE` with no invented readings. Each interface reports its observed
state and available Linux cumulative counters: received/transmitted bytes,
packets, and errors. A missing counter is `null`, which is distinct from a
measured zero. Counter values are totals since interface creation, **not** a
throughput rate. Link state is derived from both endpoint interfaces; it is
`UNKNOWN` if an endpoint could not be inspected. A partial snapshot includes
safe error codes naming the affected interface.

`POST /api/v1/network/monitoring/probe` performs an explicit ICMP ping from
one known Mininet host to another. Request example:

```json
{"source":"h1","destination":"h2","count":2,"timeout_seconds":2}
```

Only `h1`, `h2`, and `server1` are accepted, and source and destination must
differ. `count` is 1–3 and `timeout_seconds` is 1–2. The response reports UTC
time, actual sent/received packets, packet-loss percentage, and average RTT in
milliseconds when replies provide it. Zero loss is reported only after a
successful parsed probe. A timed-out or unparseable probe has `null` loss and
latency plus a specific status/error code; 100% measured loss is
`UNREACHABLE`, with `null` latency. The existing Phase 3
`POST /api/v1/network/connectivity-test` remains available for all-host loss.

These are the smallest API extensions needed for current observations. The
API design's `/health/network` example presumes an aggregate score and
incident data that Phase 5 cannot truthfully provide. It is therefore not
implemented. Both monitoring routes retain the Phase 3 local-only rule; the
probe also requires `X-NetRCA-Local-Control: 1`. The app must stay bound to
loopback with one worker. Fixed `ip -j -s` and `ping` argument lists run in
Mininet namespaces without a shell. Each command has a timeout, a snapshot
inspects at most 16 interfaces, and the manager serializes observations with
network lifecycle operations. FastAPI uses synchronous route functions so
waiting on the manager does not block the asynchronous event loop. With a
short configured HTTP wait, a still-running operation returns HTTP 202.

From `backend/` on Windows, run offline tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_monitoring.py -q
```

In the Ubuntu WSL lab, run the real monitoring and full regression tests as
root, using the separate Linux venv:

```bash
sudo env NETRCA_RUN_MININET_TESTS=1 ~/netrca-venv/bin/python -m pytest tests/test_monitoring_integration.py -q
sudo env NETRCA_RUN_MININET_TESTS=1 ~/netrca-venv/bin/python -m pytest -q --tb=short
```

All commands assume the current directory is `backend/`. See
[PHASE5_REPORT.md](PHASE5_REPORT.md) for verified results and limitations.
