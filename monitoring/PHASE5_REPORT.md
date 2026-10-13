# Phase 5 implementation report — 2026-10-13

The original `Instruction/` architecture, ERD, tech stack, API design,
security, SRS, and PRD were read before implementation. The Phase 1–4 code,
network/topology guides and reports, routes, tests, and Git status were
inspected. The only pre-existing worktree change was an unrelated `.gitignore`
edit, which remains untouched. No original instruction document changed.

Added `backend/app/monitoring/` with typed snapshot/probe results and a
read-only collector. The collector inspects Mininet's known hosts and switches,
their interfaces, and both ends of each live link. It reads Linux interface
state and cumulative byte/packet/error counters through bounded `ip -j -s`
commands. A failed interface read produces a partial snapshot with `null`
counters and a safe error code. The explicit host-pair ping provides measured
packet loss and average RTT; 100% loss, a timeout, and missing results remain
distinct. Every result is UTC timestamped.

The `NetworkManager` serializes observations with start/stop/reset and probes
without marking a running lab failed merely because a monitoring operation
fails. The existing Mininet adapter and Phase 3 topology behavior remain in
place. Added local-only `GET /api/v1/network/monitoring` and control-header
protected `POST /api/v1/network/monitoring/probe`. Input accepts only known
host names and tightly bounded ping parameters. Both use the existing API
envelope and error codes. No database table, migration, credentials, automatic
sync, fault injection, remediation, or background monitoring was added.

| Test/check | Actual result |
| --- | --- |
| Windows `python -m pytest tests/test_monitoring.py -q --tb=short` | 6 passed, one existing Starlette deprecation warning |
| Ubuntu `NETRCA_RUN_MININET_TESTS=1 python -m pytest tests/test_monitoring_integration.py -q --tb=short` | 1 passed; complete five-device, four-link snapshot with counters and successful host-pair RTT/loss probe |
| Ubuntu `NETRCA_RUN_MININET_TESTS=1 python -m pytest -q --tb=short` | 39 passed, 1 skipped (opt-in Phase 4 database test), one existing Starlette deprecation warning |
| Post-test OVS bridges and Linux interfaces | No OVS bridges; only `lo` and `eth0` |

The full Ubuntu suite includes the existing real Phase 3 Mininet integration
tests and Phase 4 topology unit/API tests. It does not rerun the Phase 4
database test, which requires its separate opt-in. No Phase 6 work or later
features were started.

Limitations: this is an on-demand snapshot, not continuous monitoring;
counters are cumulative and not throughput; latency reflects an active ICMP
host-pair probe, not link latency; network health scores and incident counts
are unavailable; historical metrics are not persisted. A lab that is not
running cannot provide live readings. Next step is review of this local,
uncommitted Phase 5 change. Do not push or begin Phase 6 without approval.
