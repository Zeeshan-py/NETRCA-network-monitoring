# NetRCA Mininet lab (Phase 3)

Phase 3 defines a fixed, controlled Mininet lab in `backend/app/network/`.
There is no network monitoring, fault injection, database topology sync, RCA,
or AI in this module. Simulation is **disabled by default**. A Windows Python
process can report the missing environment and run offline tests; it cannot
create the Linux network.

## Topology and behavior

```text
h1 (10.77.0.11) ─ s1 ─ s2 ─ h2 (10.77.0.12)
                       └──── server1 (10.77.0.20)
```

There are five nodes and four links. `s1` and `s2` are Open vSwitch bridges
in standalone mode. `h1`, `h2`, and `server1` are Mininet hosts; `server1` is
labeled SERVER for future service placement, but no application service runs
there yet. No router or routing function is claimed. Mininet builds the
topology programmatically using `Topo`, `Mininet`, and `OVSBridge`, as covered
by the [Mininet Topo](https://mininet.org/api/classmininet_1_1topo_1_1Topo.html),
[Mininet network](https://mininet.org/api/classmininet_1_1net_1_1Mininet.html),
and [OVSBridge](https://mininet.org/api/classmininet_1_1node_1_1OVSBridge.html)
API references.

Startup verifies the expected live nodes/links, checks interface state, and
runs Mininet's host-to-host `pingAll(timeout=2)` inside the lab. It reports
RUNNING only after those checks succeed. An explicit connectivity test reports
the measured packet loss and whether all hosts reached each other. This is
an on-demand connectivity check, not a continuous telemetry metric. Topology
`id` values are simulator names; later persistence must map these names to
database UUIDs before writing to `devices`/`links`.

The manager offers environment check, start, status, topology, connectivity
test, stop, restart, and reset. Reset stops the owned instance and starts the
same initial topology; restart requires an already running network. A Linux
process lock prevents two NetRCA processes from starting the lab at once.
Only the Mininet instance created by this process is stopped. No `mn -c`,
host-wide interface deletion, or arbitrary shell command is used by the app.

## Environment findings on this workstation

**Validation update (2026-10-13):** The installed Canonical Ubuntu app was
launched and registered as Ubuntu 26.04.1 LTS on WSL2. The Linux account is
`zeeshan`. Mininet 2.3.0, Open vSwitch 3.7.1, and `python3-venv` were installed
from Ubuntu packages. OVS is active and its kernel module is loaded. The
official `sudo mn --switch ovsbr --test pingall` check passed with 0% packet
loss (2/2 received). The NetRCA environment check returned `READY`; its smoke
cycle built the five-node topology, passed connectivity before and after reset,
and ended `STOPPED`. The opt-in real integration tests passed (2/2), and the
full Linux backend suite passed (26/26). After tests, only `lo` and `eth0`
remained and `ovs-vsctl list-br` was empty. `docker-desktop` remained the
default WSL distribution and was not changed. The setup history below records
the earlier failed attempts; it is superseded by this verified result.

Read-only inspection on 2026-10-12 found Windows 11 Pro, Python 3.14.2,
WSL 2.6.3, and only the stopped `docker-desktop` WSL2 distribution. Ubuntu
is not installed. The Windows environment has no Mininet Python module,
`mn`, `ovs-vsctl`, or Linux `ip` tool. Linux root privileges and OVS daemon
functionality cannot be assessed until a suitable Linux distribution exists.
Docker Desktop's internal distribution is not a supported workspace for this
project. The owner approved Ubuntu installation, but the attempts did not
complete, so no Ubuntu distribution or network package was installed.

On 2026-10-13, `wsl --install -d Ubuntu-24.04 --no-launch` and its
`--web-download` variant stalled with incomplete image files. A direct
official Ubuntu WSL image download reset, and ranged downloads remained
incomplete. WinGet's Ubuntu package staging failed with `0x80d02002`, which
Microsoft identifies as a [download with no progress](https://learn.microsoft.com/en-us/windows/win32/delivery_optimization/do-return-values).
The Store-backed generic Ubuntu installer was also tried, but showed no
installation progress and was stopped; no Ubuntu package appeared afterward.
The final `wsl --list --verbose` still showed only `docker-desktop`.

The preferred environment is Ubuntu under WSL2 **if its kernel supports
working Open vSwitch**. A dedicated Ubuntu VM is the fallback. The
[official Mininet download guide](https://mininet.org/download/) recommends
its prebuilt VM for reliability and documents package installation and the
`ovsbr` ping test. The Ubuntu installation commands were attempted but did
not succeed; the Linux package and topology commands below have **not been
executed on this workstation**. The owner approved Ubuntu WSL2 setup.

## Recommended WSL2/Ubuntu setup (Linux steps not executed here)

1. Install an Ubuntu WSL2 distribution through the normal Windows setup,
   then verify `wsl --list --verbose` shows it at version 2. This step may
   require Windows administrator privileges. Do not use the `docker-desktop`
   distribution as the development host. If online setup stalls, the
   [official Ubuntu WSL instructions](https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/)
   describe downloading a complete `.wsl` image and installing it with
   `wsl --install --from-file <image>.wsl`. Verify the official checksum
   before installation; the incomplete files from this workstation's attempts
   cannot be used.
2. Inside Ubuntu, install `python3-venv`, Mininet, Open vSwitch, `iproute2`,
   and `iputils-ping` with the distro's package manager. For Ubuntu releases
   supported by those packages:

   ```bash
   sudo apt update
   sudo apt install python3-venv mininet openvswitch-switch iproute2 iputils-ping
   sudo service openvswitch-switch start
   sudo mn --switch ovsbr --test pingall
   ```

   The final command is the Mininet project's documented OVS bridge
   smoke test. If OVS cannot start or bridge/ping tests fail under WSL2,
   stop there and use a dedicated Ubuntu VM; do not claim this project works
   on that WSL setup.
3. The existing Windows repository appears in WSL as
   `/mnt/d/SEMESTER 5/AI Lab/Project`. Use the same repository in place.
   The Windows `.venv` cannot run Linux Python packages. Create a Linux
   venv in your Ubuntu home directory with access to the distro's Mininet
   package, then install the backend's Python requirements:

   ```bash
   python3 -m venv --system-site-packages ~/netrca-venv
   source ~/netrca-venv/bin/activate
   cd "/mnt/d/SEMESTER 5/AI Lab/Project/backend"
   python -m pip install -r requirements-dev.txt
   ```

   If the distro package is not visible to that Python interpreter, verify
   the distro's `python3` and venv versions match before proceeding. Do not
   use `pip install mininet` as a substitute for the Linux networking tools.

## Verify and run the lab

In Ubuntu, from the `backend` directory, the environment check is read-only:

```bash
sudo ~/netrca-venv/bin/python -m app.network.cli environment
```

It returns a code such as `READY`, `MININET_NOT_INSTALLED`,
`NETWORK_TOOLS_MISSING`, `OVS_UNAVAILABLE`, or `ROOT_REQUIRED`. To perform
one complete owned lab cycle—start, inspect the actual topology, ping all
hosts, reset, ping again, and stop—run:

```bash
sudo env NETRCA_SIMULATION_ENABLED=true ~/netrca-venv/bin/python -m app.network.cli smoke
```

The command exits nonzero if a prerequisite or connectivity check fails. It
prints only simulator names, link states and the final state. Its `finally`
handler attempts to stop the owned instance on failure.

To run the local FastAPI controls instead, use a **single worker**, keep it
bound to loopback, and enable the simulation explicitly:

```bash
sudo env NETRCA_SIMULATION_ENABLED=true NETRCA_CORS_ORIGINS=http://localhost:3000 \
  ~/netrca-venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Examples from another terminal in the same Ubuntu environment:

```bash
curl http://127.0.0.1:8000/api/v1/network/status
curl -H 'X-NetRCA-Local-Control: 1' -X POST http://127.0.0.1:8000/api/v1/network/start
curl http://127.0.0.1:8000/api/v1/topology
curl -H 'X-NetRCA-Local-Control: 1' -X POST http://127.0.0.1:8000/api/v1/network/connectivity-test
curl -H 'X-NetRCA-Local-Control: 1' -X POST http://127.0.0.1:8000/api/v1/network/reset
curl -H 'X-NetRCA-Local-Control: 1' -X POST http://127.0.0.1:8000/api/v1/network/stop
```

`POST /api/v1/network/restart` is also available while running. The simulator
endpoints reject non-loopback peers; controls additionally require the custom
header, and browser origins must match a configured **local** CORS origin.
These are development gates, not user authentication. Keep the API on
127.0.0.1 inside the isolated lab. Do not put it behind a public proxy or run
multiple Uvicorn workers. The API responds 202 when a bounded request wait
expires while its operation continues; poll `/network/status` for the final
result. A 503 indicates missing prerequisites or a failed operation. No route
accepts a shell command, arbitrary topology, interface name or target host.

`NETRCA_SIMULATION_ENABLED=false` is the default in `backend/.env.example`.
`NETRCA_SIMULATION_OPERATION_TIMEOUT_SECONDS` controls the HTTP wait (1–60,
default 20); it does not forcibly kill a Mininet operation in progress. A
stalled Mininet call can delay shutdown; inspect only this lab's resources
before a manual recovery. The backend shutdown hook attempts to stop its own
instance. Since this phase has no authentication, a root-owned API must never
be exposed beyond the isolated local development host.

## Tests and troubleshooting

Offline mock tests run on Windows and do not prove Mininet operation:

```powershell
cd backend
.venv/Scripts/python.exe -m pytest tests/test_network.py -q
```

Once Ubuntu/OVS is ready, opt in to the **real** integration tests from the
Linux `backend` directory. They create the lab, verify its nodes/links,
connectivity, reset, repeated start and shutdown, and check cleanup after an
injected startup-verification failure:

```bash
sudo env NETRCA_RUN_MININET_TESTS=1 ~/netrca-venv/bin/python -m pytest tests/test_mininet_integration.py -q
```

Run this only on the intended isolated lab. The default backend suite skips
it. `LINUX_REQUIRED` means the current interpreter is Windows; use Ubuntu.
`ROOT_REQUIRED` means run the lab check/process with the required Linux
privilege. `MININET_NOT_INSTALLED` means the distro Python cannot import
Mininet. `NETWORK_TOOLS_MISSING` means OVS, `mnexec`, `ip`, or `ping` is not
found. `OVS_UNAVAILABLE` means `ovs-vsctl show` failed or timed out; check
the daemon and WSL kernel support. A failed startup reports an error and
tries to stop only the instance it created; if that cleanup fails, stop
retrying until the lab is inspected. No live topology or metrics are invented
when the simulator is unavailable.
