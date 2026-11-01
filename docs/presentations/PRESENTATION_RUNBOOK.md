# NetRCA presentation runbook

This setup is designed for a repeatable firm presentation without Docker, remote
database seeding, Mininet, or a live Gemini request. The populated scenario is
explicitly labeled **Synthetic demo** in the UI.

## Start the presentation

From PowerShell in the repository root:

```powershell
.\scripts\start-presentation.ps1
```

The script starts the FastAPI health endpoint on `127.0.0.1:8000`, starts Next.js
on `127.0.0.1:3000`, waits for both services, and opens the dashboard. Runtime
logs are written under `%TEMP%\netrca-presentation`.

Stop both local listeners with:

```powershell
.\scripts\stop-presentation.ps1
```

If a previous frontend or backend terminal is already using port 3000 or 8000,
the start script stops safely with the exact PID instead of terminating an
unknown process.

## Five-minute pitch flow

1. Open **Demo Brief** and frame the product: deterministic evidence first,
   explainable analysis second.
2. Open **Overview** and describe the WAN outage, degraded devices, packet-loss
   signal, and active incident.
3. Open **Topology**, keep **Stored topology** selected, and show the failed
   uplink plus the intentionally disconnected backup host.
4. Open **Evidence** and connect metric, log, and event timestamps through stable
   device and link IDs.
5. Open **Incidents**, select the checkout outage, and show correlated evidence,
   the rule-scored RCA candidate, potential failure chain, and uncertainty.
6. Select **Show presentation explanation**. This is a static evidence-linked
   fixture and does not call Gemini.

## What you can claim

- A working, responsive technical prototype and repeatable product demonstration.
- Local-only protected network controls and opt-in write paths.
- Stored evidence, deterministic correlation, explainable RCA candidates, and
  explicit potential-versus-confirmed impact semantics.
- A PostgreSQL/Supabase-compatible persistence implementation and a WSL2 Mininet
  laboratory that have been tested separately.

## What is not yet customer-production ready

Do not represent this build as a finished multi-tenant product. Customer
production still requires tenant authentication, role-based authorization, SSO,
secret rotation and managed secret storage, deployment architecture, audit actor
identity, backup/restore operations, monitoring/SLA processes, dependency
security remediation, load testing, and an independent security review.

The right commercial offer is a **controlled pilot**: connect one approved lab
or read-only telemetry source, validate the evidence model and workflow with the
customer, then harden tenancy and deployment around the proven operating model.
