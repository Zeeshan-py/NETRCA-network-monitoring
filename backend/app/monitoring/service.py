"""Bounded, shell-free observation commands inside Mininet node namespaces."""
import json
import re
from datetime import datetime, timezone
from ipaddress import ip_address
from subprocess import PIPE, TimeoutExpired

from app.monitoring.models import DeviceReading, InterfaceReading, LinkReading, MonitoringSnapshot, ProbeReading
from app.network.topology import NODES, TOPOLOGY_NAME


_INTERFACE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")
_PING_SUMMARY = re.compile(r"(\d+) packets? transmitted, (\d+) (?:packets? )?received, ([\d.]+)% packet loss")
_PING_RTT = re.compile(r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = [\d.]+/([\d.]+)/")
_DEVICE_TYPES = {node.name: node.device_type for node in NODES}
MAX_INTERFACES = 16


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _command(node, args: list[str], *, timeout: float) -> tuple[str | None, int | None, str | None]:
    """Return stdout, exit code, error code; never invoke a shell."""
    try:
        process = node.popen(args, stdout=PIPE, stderr=PIPE)
    except (OSError, RuntimeError):
        return None, None, "COMMAND_UNAVAILABLE"
    try:
        stdout, _stderr = process.communicate(timeout=timeout)
    except TimeoutExpired:
        process.kill()
        try:
            process.communicate(timeout=1)
        except TimeoutExpired:
            pass
        return None, None, "COMMAND_TIMEOUT"
    return stdout.decode("utf-8", errors="replace"), process.returncode, None


def _counter(stats: dict, direction: str, key: str) -> int | None:
    value = (stats.get(direction) or {}).get(key)
    return value if isinstance(value, int) and value >= 0 else None


def _interface(node, name: str) -> InterfaceReading:
    if not _INTERFACE_NAME.fullmatch(name):
        return InterfaceReading(name=name, status="UNAVAILABLE", error_code="INVALID_INTERFACE_NAME")
    output, code, error = _command(node, ["ip", "-j", "-s", "link", "show", "dev", name], timeout=1)
    if error or code != 0:
        return InterfaceReading(name=name, status="UNAVAILABLE", error_code=error or "INTERFACE_MISSING")
    try:
        value = json.loads(output or "")[0]
        if value.get("ifname") != name:
            raise ValueError
        flags = value.get("flags") or []
        state = value.get("operstate")
        status = "DOWN" if "UP" not in flags or state == "DOWN" else "UP" if state in {"UP", "UNKNOWN"} else "UNKNOWN"
        stats = value.get("stats64") or value.get("stats") or {}
        rx_bytes = _counter(stats, "rx", "bytes")
        tx_bytes = _counter(stats, "tx", "bytes")
        return InterfaceReading(
            name=name, status=status, operational_state=state,
            rx_bytes=rx_bytes, tx_bytes=tx_bytes,
            rx_packets=_counter(stats, "rx", "packets"), tx_packets=_counter(stats, "tx", "packets"),
            rx_errors=_counter(stats, "rx", "errors"), tx_errors=_counter(stats, "tx", "errors"),
            error_code="COUNTERS_UNAVAILABLE" if rx_bytes is None or tx_bytes is None else
                       "INTERFACE_STATE_UNAVAILABLE" if status == "UNKNOWN" else None,
        )
    except (ValueError, IndexError, KeyError, TypeError):
        return InterfaceReading(name=name, status="UNAVAILABLE", error_code="INTERFACE_PARSE_FAILED")


def capture(net) -> MonitoringSnapshot:
    """Collect at most 16 interfaces; individual failures remain visible."""
    devices: list[DeviceReading] = []
    errors: list[str] = []
    readings: dict[tuple[str, str], InterfaceReading] = {}
    remaining = MAX_INTERFACES
    for node in [*net.switches, *net.hosts]:
        interfaces: list[InterfaceReading] = []
        try:
            names = [interface.name for interface in node.intfList()]
        except Exception:
            names = []
            errors.append(f"{node.name}:INTERFACES_UNAVAILABLE")
        for name in names:
            if remaining == 0:
                errors.append("INTERFACE_LIMIT_REACHED")
                break
            remaining -= 1
            reading = _interface(node, name)
            interfaces.append(reading)
            readings[(node.name, name)] = reading
            if reading.error_code:
                errors.append(f"{node.name}/{name}:{reading.error_code}")
        devices.append(DeviceReading(name=node.name, device_type=_DEVICE_TYPES[node.name], interfaces=interfaces))

    links: list[LinkReading] = []
    for link in net.links:
        left, right = link.intf1, link.intf2
        a = readings.get((left.node.name, left.name))
        b = readings.get((right.node.name, right.name))
        state = "DOWN" if any(item and item.status == "DOWN" for item in (a, b)) else "UP" if a and b and a.status == b.status == "UP" else "UNKNOWN"
        links.append(LinkReading(source=left.node.name, destination=right.node.name,
                                 interface_source=left.name, interface_destination=right.name, status=state))
    return MonitoringSnapshot(observed_at=_now(), topology_name=TOPOLOGY_NAME, network_state="RUNNING",
                              collection_status="PARTIAL" if errors else "COMPLETE", devices=devices,
                              links=links, errors=errors)


def probe(net, source: str, destination: str, *, count: int, timeout_seconds: int) -> ProbeReading:
    """Ping one known Mininet host from another; no arbitrary address or command."""
    hosts = {host.name: host for host in net.hosts}
    if source not in hosts or destination not in hosts or source == destination:
        raise ValueError("Probe requires two distinct known Mininet hosts")
    try:
        target = hosts[destination].IP()
    except Exception:
        target = ""
    try:
        ip_address(target)
    except ValueError:
        return ProbeReading(observed_at=_now(), source=source, destination=destination,
                            status="UNAVAILABLE", error_code="TARGET_ADDRESS_UNAVAILABLE")
    output, code, error = _command(hosts[source],
                                   ["ping", "-n", "-c", str(count), "-W", str(timeout_seconds), target],
                                   timeout=count * timeout_seconds + 2)
    if error:
        return ProbeReading(observed_at=_now(), source=source, destination=destination,
                            status="TIMEOUT" if error == "COMMAND_TIMEOUT" else "UNAVAILABLE", error_code=error)
    match = _PING_SUMMARY.search(output or "")
    if not match or code not in {0, 1}:
        return ProbeReading(observed_at=_now(), source=source, destination=destination,
                            status="UNAVAILABLE", error_code="PING_RESULT_UNAVAILABLE")
    sent, received, loss = int(match[1]), int(match[2]), float(match[3])
    rtt = _PING_RTT.search(output or "")
    return ProbeReading(observed_at=_now(), source=source, destination=destination,
                        packets_sent=sent, packets_received=received, packet_loss_percent=loss,
                        latency_ms=float(rtt[1]) if rtt else None,
                        status="REACHABLE" if received else "UNREACHABLE")
