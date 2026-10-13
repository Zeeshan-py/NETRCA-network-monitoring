# Phase 7 controlled fault injection

Fault injection controls only the running, fixed NetRCA Mininet topology in Ubuntu WSL2. It is disabled by default. Set `NETRCA_SIMULATION_ENABLED=true` and `NETRCA_FAULT_INJECTION_ENABLED=true` in the backend's local environment, run one backend worker on `127.0.0.1`, and start the lab using the [network guide](../network/README.md). Root access is required for the Mininet lab. Keep the API bound to loopback; every control request also needs `X-NetRCA-Local-Control: 1`. Reads require a loopback client as well. An unapproved browser origin is rejected.

The supported fault types are `INTERFACE_FAILURE`, `LINK_FAILURE`, `PACKET_LOSS`, and `HIGH_LATENCY`. Interface failure targets one live lab port. Link failure targets one of the four fixed lab links and takes both endpoints down. Packet loss (1–100%) and latency (1–250 ms) target a lab host port only. A duration of 1–300 seconds is required or defaults to 30 seconds. Only one fault can be active at a time. Bandwidth restriction is omitted because no safe capture-and-restore method was established for arbitrary pre-existing queueing configurations.

The backend verifies the exact set of lab nodes and links, the port's membership in that Mininet instance, its admin state or qdisc, and the result of each mutation. It refuses a down interface or an existing non-`noqueue` qdisc. Commands use fixed argument arrays, no shell, and per-command timeouts. The service never runs broad Mininet cleanup. Interface and link restoration uses captured `UP` flags; shaping restoration removes only the `netem` qdisc it placed. Failed restoration leaves the record active for manual retry. The expiry timer retries up to 10 times at one-second intervals; after that, the fault remains visible and recoverable.

Requests use `/api/v1` and JSON. Examples:

```json
{"fault_type":"INTERFACE_FAILURE","device":"h1","interface":"h1-eth0","duration_seconds":30}
{"fault_type":"LINK_FAILURE","source":"h1","destination":"s1","duration_seconds":30}
{"fault_type":"PACKET_LOSS","device":"h1","interface":"h1-eth0","packet_loss_percent":25,"duration_seconds":30}
{"fault_type":"HIGH_LATENCY","device":"h1","interface":"h1-eth0","latency_ms":50,"duration_seconds":30}
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/faults/types` | Supported types |
| POST | `/faults/inject` | Apply one fault; 201 on success |
| GET | `/faults` | Local in-process records, paginated |
| GET | `/faults/{id}` | One local record |
| POST | `/faults/{id}/recover` | Restore; repeat calls return the terminal record |
| POST | `/faults/{id}/cancel` | Restore and mark cancelled |
| POST | `/faults/reset` | Restore the active fault, if any |

`GET /faults?source=stored` and `GET /faults/{id}?source=stored` read persisted history. Responses use the existing `success` and `data`/`error` envelope. Invalid request bodies return 422, unknown lab targets 400, unsafe configuration or an existing active fault 409, disabled controls or non-local access 403, and unavailable lab or command failures 503.

When a matching active device or exact endpoint/interface link exists in PostgreSQL, lifecycle transitions are saved to the existing `public.fault_injections` table. No schema migration was added. Records that cannot be mapped or saved remain available in process with `storage_status` of `UNMAPPED` or `UNAVAILABLE`. Stored history is not an authority for restoring a live fault: restoration uses the live controller and its captured pre-state. Phase 6 metrics/events remain observation-based; injecting a fault itself does not invent an event. Monitoring snapshots and probes can observe an active fault, and Phase 6 can persist those actual readings through its existing opt-in endpoints.

From `backend/`, run offline tests on Windows with `.venv/Scripts/python.exe -m pytest -q`. In Ubuntu WSL2 as root, run the real lab suite with `NETRCA_RUN_MININET_TESTS=1 NETRCA_RUN_FAULT_TESTS=1 /home/zeeshan/netrca-venv/bin/python -m pytest tests -q`. The isolated rollback-only PostgreSQL test is opt-in with `NETRCA_RUN_FAULT_DB_TESTS=1`; it needs a reachable configured database. Stop the lab through its existing network API or CLI; fault cleanup runs before the owned Mininet instance stops. If restoration fails, inspect the fault record and recover it again before exiting the backend.
