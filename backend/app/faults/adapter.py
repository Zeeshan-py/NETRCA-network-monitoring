"""Strict, shell-free mutations of interfaces belonging to the owned Mininet instance."""
import json
import re
from subprocess import PIPE, TimeoutExpired

from app.faults.models import FaultRequest
from app.network.errors import NetworkError
from app.network.topology import HOST_NAMES, LINKS, NODES


_NAMES = {item.name for item in NODES}
_LINKS = {frozenset((item.source, item.destination)) for item in LINKS}
_INTERFACE = re.compile(r"^[A-Za-z0-9_-]+-eth[0-9]{1,2}$")


class InvalidFaultTarget(NetworkError):
    code = "INVALID_FAULT_TARGET"
    http_status = 400


class UnsafeFaultTarget(NetworkError):
    code = "UNSAFE_FAULT_TARGET"
    http_status = 409


class FaultOperationError(NetworkError):
    code = "FAULT_OPERATION_FAILED"
    http_status = 503


class FaultApplyFailure(FaultOperationError):
    def __init__(self, state: dict, *, needs_restore: bool):
        self.state = state
        self.needs_restore = needs_restore
        super().__init__("Fault application failed")


def _run(node, args: list[str]) -> str:
    try:
        process = node.popen(args, stdout=PIPE, stderr=PIPE)
        try:
            output, _ = process.communicate(timeout=3)
        except TimeoutExpired:
            process.kill()
            process.communicate(timeout=1)
            raise FaultOperationError("Lab command timed out") from None
        if process.returncode != 0:
            raise FaultOperationError("Lab command failed")
        return output.decode("utf-8", errors="replace")
    except FaultOperationError:
        raise
    except (OSError, RuntimeError, TimeoutExpired):
        raise FaultOperationError("Lab command failed") from None


def _nodes(net):
    nodes = {node.name: node for node in [*net.hosts, *net.switches]}
    if set(nodes) != _NAMES or len(nodes) != len(_NAMES):
        raise UnsafeFaultTarget("Live lab does not match the fixed NetRCA topology")
    pairs = [frozenset((link.intf1.node.name, link.intf2.node.name)) for link in net.links]
    if len(pairs) != len(_LINKS) or set(pairs) != _LINKS:
        raise UnsafeFaultTarget("Live lab links do not match the fixed NetRCA topology")
    return nodes


def _owned_endpoint(net, node, interface: str):
    if not _INTERFACE.fullmatch(interface) or not interface.startswith(f"{node.name}-eth"):
        raise InvalidFaultTarget("Interface is not a NetRCA lab port")
    matching = [intf for link in net.links for intf in (link.intf1, link.intf2)
                if intf.node is node and intf.name == interface]
    if len(matching) != 1 or all(intf is not matching[0] for intf in node.intfList()):
        raise InvalidFaultTarget("Interface is not part of an owned lab link")
    return matching[0]


def _targets(net, request: FaultRequest):
    nodes = _nodes(net)
    if request.fault_type == "LINK_FAILURE":
        pair = frozenset((request.source, request.destination))
        if pair not in _LINKS:
            raise InvalidFaultTarget("Link is not in the NetRCA lab")
        matching = [link for link in net.links
                    if frozenset((link.intf1.node.name, link.intf2.node.name)) == pair]
        if len(matching) != 1:
            raise UnsafeFaultTarget("Live lab link is missing or ambiguous")
        endpoints = (matching[0].intf1, matching[0].intf2)
        return [(intf.node, _owned_endpoint(net, intf.node, intf.name).name) for intf in endpoints]
    if request.device not in nodes:
        raise InvalidFaultTarget("Device is not in the NetRCA lab")
    if request.fault_type in {"PACKET_LOSS", "HIGH_LATENCY"} and request.device not in HOST_NAMES:
        raise UnsafeFaultTarget("Traffic shaping is limited to isolated lab hosts")
    node = nodes[request.device]
    intf = _owned_endpoint(net, node, request.interface)
    return [(node, intf.name)]


def _up(node, interface: str) -> bool:
    try:
        data = json.loads(_run(node, ["ip", "-j", "link", "show", "dev", interface]))
        if len(data) != 1 or data[0].get("ifname") != interface:
            raise ValueError
        return "UP" in data[0]["flags"]
    except (ValueError, KeyError, TypeError):
        raise FaultOperationError("Cannot inspect lab interface state") from None


def _qdisc(node, interface: str) -> str:
    try:
        data = json.loads(_run(node, ["tc", "-j", "qdisc", "show", "dev", interface]))
        roots = [entry for entry in data if entry.get("root")]
        if len(data) != 1 or len(roots) != 1:
            raise ValueError
        return roots[0]["kind"]
    except (ValueError, KeyError, TypeError):
        raise FaultOperationError("Cannot inspect lab qdisc") from None


def apply(net, request: FaultRequest) -> dict:
    """Return captured pre-state only after verified application."""
    targets = _targets(net, request)
    mode = "qdisc" if request.fault_type in {"PACKET_LOSS", "HIGH_LATENCY"} else "admin"
    state = {"mode": mode, "targets": []}
    for node, interface in targets:
        entry = {"device": node.name, "interface": interface}
        if mode == "admin":
            entry["was_up"] = _up(node, interface)
            if not entry["was_up"]:
                raise UnsafeFaultTarget("Target interface is already down")
        else:
            entry["qdisc"] = _qdisc(node, interface)
            if entry["qdisc"] != "noqueue":
                raise UnsafeFaultTarget("Existing traffic shaping cannot be replaced safely")
        state["targets"].append(entry)
    try:
        for node, interface in targets:
            if mode == "admin":
                _run(node, ["ip", "link", "set", "dev", interface, "down"])
                if _up(node, interface):
                    raise FaultOperationError("Interface remained up")
            else:
                value = (f"{request.packet_loss_percent}%" if request.fault_type == "PACKET_LOSS"
                         else f"{request.latency_ms}ms")
                args = ["tc", "qdisc", "replace", "dev", interface, "root", "netem",
                        "loss" if request.fault_type == "PACKET_LOSS" else "delay", value]
                _run(node, args)
                if _qdisc(node, interface) != "netem":
                    raise FaultOperationError("Traffic shaping did not become active")
        return state
    except FaultOperationError:
        try:
            restore(net, state)
        except FaultOperationError:
            raise FaultApplyFailure(state, needs_restore=True) from None
        raise FaultApplyFailure(state, needs_restore=False) from None


def restore(net, state: dict) -> None:
    """Restore every captured port, continuing after one command fails."""
    nodes = _nodes(net)
    failed = False
    for entry in state["targets"]:
        node = nodes.get(entry["device"])
        if node is None:
            failed = True
            continue
        try:
            interface = _owned_endpoint(net, node, entry["interface"]).name
            if state["mode"] == "admin":
                desired = bool(entry["was_up"])
                if _up(node, interface) != desired:
                    _run(node, ["ip", "link", "set", "dev", interface, "up" if desired else "down"])
                if _up(node, interface) != desired:
                    raise FaultOperationError("Interface state was not restored")
            elif state["mode"] == "qdisc":
                if entry["qdisc"] != "noqueue":
                    raise FaultOperationError("Unsupported saved qdisc")
                if _qdisc(node, interface) != "noqueue":
                    _run(node, ["tc", "qdisc", "del", "dev", interface, "root"])
                if _qdisc(node, interface) != "noqueue":
                    raise FaultOperationError("Qdisc was not restored")
            else:
                raise FaultOperationError("Unknown restoration mode")
        except (FaultOperationError, InvalidFaultTarget, UnsafeFaultTarget):
            failed = True
    if failed:
        raise FaultOperationError("One or more lab ports could not be restored")
