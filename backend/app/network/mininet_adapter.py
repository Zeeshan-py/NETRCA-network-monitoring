"""Owns one Mininet instance and only its resources; no global mn -c cleanup."""
import os
from pathlib import Path

from app.network.errors import NetworkAlreadyRunning, NetworkNotRunning, ShutdownFailure, StartupFailure
from app.network.models import ConnectivityView, DeviceView, LinkView, TopologyView
from app.network.topology import HOST_NAMES, LINKS, NODES, TOPOLOGY_NAME, build_mininet_topology
from app.monitoring.models import MonitoringSnapshot, ProbeReading
from app.monitoring.service import capture, probe


class MininetAdapter:
    def __init__(self) -> None:
        self._net = None
        self._lock_fd: int | None = None

    def _acquire_process_lock(self) -> None:
        import fcntl

        path = Path("/run/lock/netrca-mininet.lock")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise NetworkAlreadyRunning("Another NetRCA simulator owns the lab") from None
        except BaseException:
            os.close(fd)
            raise
        self._lock_fd = fd

    def _release_process_lock(self) -> None:
        if self._lock_fd is not None:
            import fcntl

            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            os.close(self._lock_fd)
            self._lock_fd = None

    def start(self) -> TopologyView:
        if self._net is not None:
            raise NetworkAlreadyRunning("Network is already running")
        self._acquire_process_lock()
        try:
            from mininet.net import Mininet
            from mininet.node import OVSBridge

            self._net = Mininet(
                topo=build_mininet_topology(), controller=None, switch=OVSBridge,
                autoSetMacs=True, autoStaticArp=True, build=False,
            )
            self._net.build()
            self._net.start()
            topology = self.topology()
            expected_nodes = {node.name for node in NODES}
            expected_links = {frozenset((edge.source, edge.destination)) for edge in LINKS}
            if {node.name for node in topology.nodes} != expected_nodes or {frozenset((edge.source, edge.destination)) for edge in topology.links} != expected_links or any(edge.status != "UP" for edge in topology.links):
                raise StartupFailure("Network did not create the expected live topology")
            if not self.test_connectivity(timeout=2).connected:
                raise StartupFailure("Simulated hosts could not communicate")
            return topology
        except BaseException as error:
            try:
                self.stop()
            except ShutdownFailure:
                raise StartupFailure("Network startup failed and owned resources need manual inspection") from None
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(error, StartupFailure):
                raise
            raise StartupFailure("Network startup failed") from None

    def stop(self) -> None:
        if self._net is not None:
            try:
                self._net.stop()
            except Exception:
                raise ShutdownFailure("Failed to stop the owned Mininet instance") from None
            self._net = None
        self._release_process_lock()

    def topology(self) -> TopologyView:
        if self._net is None:
            raise NetworkNotRunning("Network is not running")
        kinds = {node.name: node.device_type for node in NODES}
        nodes = [
            DeviceView(id=node.name, name=node.name, device_type=kinds[node.name], ip_address=node.IP() or None if node.name in HOST_NAMES else None)
            for node in [*self._net.switches, *self._net.hosts]
        ]
        links = [
            LinkView(
                id=f"{link.intf1.node.name}--{link.intf2.node.name}",
                source=link.intf1.node.name,
                destination=link.intf2.node.name,
                status="UP" if link.intf1.isUp() and link.intf2.isUp() else "DOWN",
                interface_source=link.intf1.name,
                interface_destination=link.intf2.name,
            ) for link in self._net.links
        ]
        return TopologyView(topology_name=TOPOLOGY_NAME, nodes=nodes, links=links)

    def test_connectivity(self, timeout: int) -> ConnectivityView:
        if self._net is None:
            raise NetworkNotRunning("Network is not running")
        actual_hosts = {host.name for host in self._net.hosts}
        if not set(HOST_NAMES) <= actual_hosts:
            raise StartupFailure("Expected hosts are missing")
        loss = float(self._net.pingAll(timeout=timeout))
        return ConnectivityView(hosts=list(HOST_NAMES), packet_loss_percent=loss, connected=loss == 0)

    def monitor_snapshot(self) -> MonitoringSnapshot:
        if self._net is None:
            raise NetworkNotRunning("Network is not running")
        return capture(self._net)

    def probe_hosts(self, source: str, destination: str, count: int, timeout_seconds: int) -> ProbeReading:
        if self._net is None:
            raise NetworkNotRunning("Network is not running")
        return probe(self._net, source, destination, count=count, timeout_seconds=timeout_seconds)
