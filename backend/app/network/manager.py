"""One-process lifecycle coordinator; adapter also holds a Linux process lock."""
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from threading import RLock
from typing import Callable, Protocol

from app.network.environment import check_environment
from app.network.errors import ConnectivityFailure, InvalidProbeTarget, MonitoringFailure, NetworkAlreadyRunning, NetworkError, NetworkNotRunning, NetworkUnavailable, OperationBusy, ShutdownFailure, StartupFailure
from app.network.mininet_adapter import MininetAdapter
from app.network.models import ConnectivityView, EnvironmentReport, NetworkStatus, TopologyView
from app.network.topology import TOPOLOGY_NAME
from app.network.topology import HOST_NAMES
from app.monitoring.models import MonitoringSnapshot, ProbeReading


class NetworkAdapter(Protocol):
    def start(self) -> TopologyView: ...
    def stop(self) -> None: ...
    def topology(self) -> TopologyView: ...
    def test_connectivity(self, timeout: int) -> ConnectivityView: ...
    def monitor_snapshot(self) -> MonitoringSnapshot: ...
    def probe_hosts(self, source: str, destination: str, count: int, timeout_seconds: int) -> ProbeReading: ...
    def apply_fault(self, request: object) -> dict: ...
    def restore_fault(self, state: dict) -> None: ...


class NetworkManager:
    def __init__(
        self,
        *,
        enabled: bool = False,
        adapter_factory: Callable[[], NetworkAdapter] = MininetAdapter,
        environment_probe: Callable[[], EnvironmentReport] = check_environment,
    ) -> None:
        self._enabled = enabled
        self._factory = adapter_factory
        self._probe = environment_probe
        self._mutex = RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="netrca-mininet")
        self._adapter: NetworkAdapter | None = None
        self._state = "STOPPED"
        self._busy = False
        self._closed = False
        self._active_future: Future | None = None
        self._operation: str | None = None
        self._last_operation: str | None = None
        self._last_result: str | None = None
        self._detail: str | None = None
        self._started_at: datetime | None = None
        self._device_count = 0
        self._link_count = 0
        self._before_stop: Callable[[NetworkAdapter], None] | None = None
        self._after_stop: Callable[[], None] | None = None
        self._stop_failed: Callable[[], None] | None = None

    def set_fault_hooks(self, before_stop: Callable[[NetworkAdapter], None], after_stop: Callable[[], None],
                        stop_failed: Callable[[], None] | None = None) -> None:
        self._before_stop = before_stop
        self._after_stop = after_stop
        self._stop_failed = stop_failed

    def _stop_adapter(self) -> None:
        if self._adapter is None:
            return
        if self._before_stop is not None:
            self._before_stop(self._adapter)
        try:
            self._adapter.stop()
        except Exception:
            if self._stop_failed is not None:
                self._stop_failed()
            raise
        if self._after_stop is not None:
            self._after_stop()

    def check_environment(self) -> EnvironmentReport:
        if not self._enabled:
            return EnvironmentReport(available=False, code="SIMULATION_DISABLED")
        return self._probe()

    def get_status(self) -> NetworkStatus:
        with self._mutex:
            state = self._state
            started_at = self._started_at
            counts = (self._device_count, self._link_count)
            operation = self._operation
            last_operation = self._last_operation
            last_result = self._last_result
            detail = self._detail
        if state == "STOPPED":
            environment = self.check_environment()
            if not environment.available:
                state = "DISABLED" if environment.code == "SIMULATION_DISABLED" else "UNAVAILABLE"
                detail = environment.code
        return NetworkStatus(
            available=state in {"STOPPED", "STARTING", "RUNNING", "STOPPING", "RESETTING"},
            state=state,
            topology_name=TOPOLOGY_NAME,
            started_at=started_at,
            device_count=counts[0], link_count=counts[1],
            operation=operation, last_operation=last_operation,
            last_result=last_result, detail=detail,
        )

    def _queue(self, name: str, transition: str, action: Callable[[], object]) -> Future:
        with self._mutex:
            if self._closed:
                raise NetworkUnavailable("Network manager is closed")
            if self._busy:
                raise OperationBusy("Another network operation is in progress")
            self._busy = True
            self._state = transition
            self._operation = name
            self._detail = None

            def run():
                try:
                    result = action()
                    with self._mutex:
                        self._last_result = "FAILED" if isinstance(result, ConnectivityView) and not result.connected else "SUCCEEDED"
                    return result
                except NetworkError as error:
                    with self._mutex:
                        self._state = "FAILED"
                        self._last_result = "FAILED"
                        self._detail = error.code
                    raise
                except Exception:
                    with self._mutex:
                        self._state = "FAILED"
                        self._last_result = "FAILED"
                        self._detail = "NETWORK_OPERATION_FAILED"
                    error_type = ShutdownFailure if name == "STOP" else ConnectivityFailure if name == "CONNECTIVITY_TEST" else StartupFailure
                    raise error_type("Network operation failed") from None
                finally:
                    with self._mutex:
                        self._busy = False
                        self._operation = None
                        self._last_operation = name

            self._active_future = self._executor.submit(run)
            return self._active_future

    def _ensure_ready(self) -> None:
        report = self.check_environment()
        if not report.available:
            raise NetworkUnavailable(report.code)

    def start_network(self) -> Future:
        self._ensure_ready()
        with self._mutex:
            if self._state == "RUNNING":
                raise NetworkAlreadyRunning("Network is already running")
            if self._state == "FAILED" and self._adapter is not None:
                raise ShutdownFailure("Stop the failed instance before starting again")

        def action():
            adapter = self._factory()
            with self._mutex:
                self._adapter = adapter
            topology = adapter.start()
            with self._mutex:
                self._state = "RUNNING"
                self._started_at = datetime.now(timezone.utc)
                self._device_count = len(topology.nodes)
                self._link_count = len(topology.links)
            return self.get_status()

        return self._queue("START", "STARTING", action)

    def stop_network(self) -> Future:
        with self._mutex:
            if self._state == "STOPPED" and not self._busy:
                self._ensure_ready()
                raise NetworkNotRunning("Network is not running")

        def action():
            if self._adapter is not None:
                self._stop_adapter()
            with self._mutex:
                self._adapter = None
                self._state = "STOPPED"
                self._started_at = None
                self._device_count = self._link_count = 0
            return self.get_status()

        return self._queue("STOP", "STOPPING", action)

    def reset_network(self, *, require_running: bool = False) -> Future:
        self._ensure_ready()
        with self._mutex:
            if require_running and self._state != "RUNNING":
                raise NetworkNotRunning("Network is not running")

        def action():
            if self._adapter is not None:
                self._stop_adapter()
            with self._mutex:
                self._adapter = None
                self._started_at = None
                self._device_count = self._link_count = 0
            adapter = self._factory()
            with self._mutex:
                self._adapter = adapter
            topology = adapter.start()
            with self._mutex:
                self._state = "RUNNING"
                self._started_at = datetime.now(timezone.utc)
                self._device_count = len(topology.nodes)
                self._link_count = len(topology.links)
            return self.get_status()

        return self._queue("RESTART" if require_running else "RESET", "RESETTING", action)

    def get_topology(self) -> TopologyView:
        with self._mutex:
            if self._busy:
                raise OperationBusy("Network operation is in progress")
            if self._state != "RUNNING" or self._adapter is None:
                self._ensure_ready()
                raise NetworkNotRunning("Network is not running")
            return self._adapter.topology()

    def test_connectivity(self, *, timeout: int = 2) -> Future:
        if timeout < 1 or timeout > 5:
            raise ValueError("Connectivity timeout must be 1 to 5 seconds")
        with self._mutex:
            if self._state != "RUNNING" or self._adapter is None:
                self._ensure_ready()
                raise NetworkNotRunning("Network is not running")

        def action():
            assert self._adapter is not None
            result = self._adapter.test_connectivity(timeout=timeout)
            with self._mutex:
                self._state = "RUNNING"
                if not result.connected:
                    self._detail = "HOST_CONNECTIVITY_FAILED"
            return result

        return self._queue("CONNECTIVITY_TEST", "RUNNING", action)

    def _observe(self, name: str, action: Callable[[NetworkAdapter], object], *, allow_failed: bool = False) -> Future:
        """Serialize read-only observations without marking the lab failed."""
        with self._mutex:
            if self._closed:
                raise NetworkUnavailable("Network manager is closed")
            if self._busy:
                raise OperationBusy("Another network operation is in progress")
            if (self._state != "RUNNING" and not (allow_failed and self._state == "FAILED")) or self._adapter is None:
                self._ensure_ready()
                raise NetworkNotRunning("Network is not running")
            adapter = self._adapter
            self._busy = True
            self._operation = name
            self._detail = None

            def run():
                try:
                    result = action(adapter)
                    with self._mutex:
                        self._last_result = "FAILED" if isinstance(result, ProbeReading) and result.status != "REACHABLE" else "SUCCEEDED"
                    return result
                except NetworkError as error:
                    with self._mutex:
                        self._last_result = "FAILED"
                        self._detail = error.code
                    raise
                except Exception:
                    with self._mutex:
                        self._last_result = "FAILED"
                        self._detail = "MONITORING_FAILED"
                    raise MonitoringFailure("Monitoring operation failed") from None
                finally:
                    with self._mutex:
                        self._busy = False
                        self._operation = None
                        self._last_operation = name

            self._active_future = self._executor.submit(run)
            return self._active_future

    def monitor_snapshot(self) -> Future:
        return self._observe("MONITOR_SNAPSHOT", lambda adapter: adapter.monitor_snapshot())

    def fault_action(self, name: str, action: Callable[[NetworkAdapter], object]) -> Future:
        return self._observe(name, action, allow_failed=name == "FAULT_RESTORE")

    def probe_hosts(self, source: str, destination: str, *, count: int = 2, timeout_seconds: int = 2) -> Future:
        if source not in HOST_NAMES or destination not in HOST_NAMES or source == destination:
            raise InvalidProbeTarget("Probe requires two distinct known Mininet hosts")
        if count < 1 or count > 3 or timeout_seconds < 1 or timeout_seconds > 2:
            raise InvalidProbeTarget("Probe parameters are outside allowed bounds")
        return self._observe("MONITOR_PROBE", lambda adapter: adapter.probe_hosts(source, destination, count, timeout_seconds))

    def close(self, timeout: float = 10) -> None:
        """Shutdown hook; never cleans up resources owned by other Mininet users."""
        with self._mutex:
            active = self._active_future if self._busy else None
        if active is not None:
            try:
                active.result(timeout=timeout)
            except Exception:
                pass
        with self._mutex:
            if self._adapter is not None and not self._busy:
                self._stop_adapter()
                self._adapter = None
                self._state = "STOPPED"
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
