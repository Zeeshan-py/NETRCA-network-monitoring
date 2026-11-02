# Unified network scenario contract

NetRCA uses `scenarios/netrca_lab_v1.json` as the canonical definition of its semester laboratory. The file is data, not executable input: it cannot contain shell commands, controllers, arbitrary interface operations, or host scripts.

## Canonical topology

```text
h1 (10.77.0.11) ─ s1 ─ s2 ─ h2 (10.77.0.12)
                       └──── server1 (10.77.0.20)
```

The contract contains a schema version, scenario name, nodes, physical links, deterministic UUIDs, IP interfaces, and expected Mininet interface names. Node keys and display names intentionally match the safe Mininet identifiers.

## Single-source adapters

```text
scenarios/netrca_lab_v1.json
       ├── Python validation → Mininet Topo → live topology/monitoring
       ├── live graph projection → deterministic UUID graph IDs
       └── TypeScript import → synthetic evidence overlay → dashboard graph
```

`backend/app/network/scenario.py` validates the file with Pydantic. `backend/app/network/topology.py` builds the Mininet `Topo` from the validated model. `frontend/src/lib/presentation-demo.ts` imports the same JSON and adds only clearly labeled synthetic state and incident evidence. The physical nodes, links, interface mapping, scenario name, and graph IDs therefore remain consistent across the lab and presentation.

The read-only local endpoint `GET /api/v1/network/scenario` returns the validated contract without enabling or starting Mininet. Live topology remains available from `GET /api/v1/topology` only while the simulator is running.

## Validation boundaries

The loader rejects:

- unsafe scenario, node, interface, or link identifiers;
- unknown or identical link endpoints;
- duplicate node keys, names, IDs, addresses, links, or interfaces;
- switches claiming host IP addresses;
- hosts or servers without IPv4 interface addresses;
- IDs that do not match the deterministic UUID contract;
- scenario path traversal or an unknown scenario name.

The current semester build loads only the repository-controlled canonical scenario. It does not accept topology uploads or arbitrary network commands through an API.

## Verification

Run offline contract and adapter tests on Windows:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q tests/test_network_scenarios.py tests/test_network.py
```

Run the actual lab only in the approved Ubuntu environment:

```bash
cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend"
sudo env NETRCA_SIMULATION_ENABLED=true \
  ~/netrca-venv/bin/python -m app.network.cli smoke
```

The smoke command must report successful connectivity before and after reset and finish in `STOPPED`. Verify no Open vSwitch bridges or Mininet processes remain afterward.

Additional fault/evidence profiles should reference this topology contract rather than duplicating its nodes and links. Adding selectable scenarios is a later controlled extension and must retain the same validation and cleanup guarantees.
