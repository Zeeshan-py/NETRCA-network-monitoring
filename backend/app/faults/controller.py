"""One active lab fault, with tracked expiry and restoration."""
from datetime import datetime, timedelta, timezone
from threading import RLock, Timer
from uuid import UUID, uuid4

from app.db.connection import DatabaseUnavailable
from app.faults.adapter import FaultApplyFailure, FaultOperationError
from app.faults.models import FaultRecord, FaultRequest
from app.faults.store import FaultStore, FaultUnmapped
from app.network.errors import MonitoringFailure, NetworkError, OperationBusy
from app.network.manager import NetworkManager


class FaultDisabled(NetworkError):
    code = "FAULT_INJECTION_DISABLED"
    http_status = 403


class FaultBusy(NetworkError):
    code = "ACTIVE_FAULT_EXISTS"
    http_status = 409


class FaultNotFound(NetworkError):
    code = "FAULT_NOT_FOUND"
    http_status = 404


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FaultController:
    def __init__(self, manager: NetworkManager, store: FaultStore, *, enabled: bool, timeout: int):
        self.manager = manager
        self.store = store
        self.enabled = enabled
        self.timeout = timeout
        self._lock = RLock()
        self._records: dict[UUID, FaultRecord] = {}
        self._states: dict[UUID, dict] = {}
        self._active: UUID | None = None
        self._timer: Timer | None = None
        self._expiry_attempts = 0
        manager.set_fault_hooks(self.on_lab_stopping, self.on_lab_stopped, self.on_lab_stop_failed)

    def _persist(self, record: FaultRecord) -> None:
        try:
            self.store.save(record, self._states[record.id])
            record.storage_status = "SYNCED"
        except FaultUnmapped:
            record.storage_status = "UNMAPPED"
        except DatabaseUnavailable:
            record.storage_status = "UNAVAILABLE"
        except Exception:
            # Persistence must never prevent lab restoration or shutdown.
            record.storage_status = "UNAVAILABLE"

    def _schedule(self, seconds: float, identifier: UUID) -> None:
        if self._timer is not None:
            self._timer.cancel()
        timer = Timer(seconds, self._expire, args=(identifier,))
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _record(self, request: FaultRequest, identifier: UUID, state: dict,
                *, failed_application: bool = False, needs_restore: bool = False) -> FaultRecord:
        if len(self._records) >= 1000:
            oldest = next((key for key, value in self._records.items() if value.status != "ACTIVE"), None)
            if oldest is not None:
                self._records.pop(oldest)
                self._states.pop(oldest, None)
        now = _now()
        target = ({"source": request.source, "destination": request.destination}
                  if request.fault_type == "LINK_FAILURE" else
                  {"device": request.device, "interface": request.interface})
        parameters: dict[str, str | int] = {"duration_seconds": request.duration_seconds}
        if request.packet_loss_percent is not None:
            parameters["packet_loss_percent"] = str(request.packet_loss_percent)
        if request.latency_ms is not None:
            parameters["latency_ms"] = str(request.latency_ms)
        record = FaultRecord(
            id=identifier, fault_type=request.fault_type, target=target,
            parameters=parameters, severity=request.severity, started_at=now,
            expires_at=now + timedelta(seconds=request.duration_seconds),
            status="ACTIVE" if not failed_application or needs_restore else "CANCELLED",
            ended_at=now if failed_application and not needs_restore else None,
            end_reason="APPLY_FAILED" if failed_application else None,
            restoration_result="FAILED" if needs_restore else
                               "SUCCEEDED" if failed_application else "PENDING",
            error_code="FAULT_APPLY_FAILED" if failed_application else None,
        )
        self._records[identifier] = record
        self._states[identifier] = state
        if record.status == "ACTIVE":
            self._active = identifier
        self._persist(record)
        if record.status == "ACTIVE":
            self._schedule(request.duration_seconds, identifier)
        return record

    def inject(self, request: FaultRequest) -> FaultRecord:
        if not self.enabled:
            raise FaultDisabled("Fault injection is disabled")
        with self._lock:
            if self._active is not None:
                raise FaultBusy("Restore the active fault before injecting another")
            self._expiry_attempts = 0
            identifier = uuid4()
            try:
                # Every lab command has its own deadline. Waiting for the serialized
                # operation to finish prevents a timed-out HTTP request from leaving
                # an applied fault that was never registered for recovery.
                state = self.manager.fault_action("FAULT_APPLY", lambda adapter: adapter.apply_fault(request)).result()
            except FaultApplyFailure as error:
                record = self._record(request, identifier, error.state, failed_application=True,
                                      needs_restore=error.needs_restore)
                return record
            return self._record(request, identifier, state)

    def _restore(self, identifier: UUID, *, reason: str, cancelled: bool = False) -> FaultRecord:
        record = self._records.get(identifier)
        if record is None:
            raise FaultNotFound("Fault was not found in this process")
        if record.status != "ACTIVE":
            return record
        try:
            self.manager.fault_action("FAULT_RESTORE", lambda adapter:
                                      adapter.restore_fault(self._states[identifier])).result()
        except (FaultOperationError, MonitoringFailure):
            record.restoration_result = "FAILED"
            record.error_code = "FAULT_RESTORE_FAILED"
            self._persist(record)
            return record
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        record.status = "CANCELLED" if cancelled else "COMPLETED"
        record.ended_at = _now()
        record.end_reason = reason
        record.restoration_result = "SUCCEEDED"
        record.error_code = None
        self._active = None
        self._persist(record)
        return record

    def recover(self, identifier: UUID, *, cancel: bool = False) -> FaultRecord:
        with self._lock:
            return self._restore(identifier, reason="CANCELLED" if cancel else "RECOVERED", cancelled=cancel)

    def _expire(self, identifier: UUID) -> None:
        with self._lock:
            if self._active != identifier:
                return
            try:
                result = self._restore(identifier, reason="EXPIRED")
            except (OperationBusy, NetworkError):
                result = self._records[identifier]
                result.restoration_result = "FAILED"
                result.error_code = "FAULT_RESTORE_DEFERRED"
                self._persist(result)
            if result.status == "ACTIVE" and self._expiry_attempts < 10:
                self._expiry_attempts += 1
                self._schedule(1, identifier)

    def on_lab_stopping(self, adapter) -> None:
        with self._lock:
            if self._active is None:
                return
            identifier = self._active
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            record = self._records[identifier]
            try:
                adapter.restore_fault(self._states[identifier])
                record.restoration_result = "SUCCEEDED"
                record.error_code = None
            except Exception:
                record.restoration_result = "FAILED"
                record.error_code = "FAULT_RESTORE_FAILED"
            self._persist(record)

    def on_lab_stopped(self) -> None:
        with self._lock:
            if self._active is None:
                return
            record = self._records[self._active]
            record.status = "COMPLETED" if record.restoration_result == "SUCCEEDED" else "CANCELLED"
            record.ended_at = _now()
            record.end_reason = "LAB_STOPPED"
            self._active = None
            self._persist(record)

    def on_lab_stop_failed(self) -> None:
        """Keep the fault recoverable when stopping the owned lab fails."""
        with self._lock:
            if self._active is None:
                return
            record = self._records[self._active]
            if record.restoration_result == "SUCCEEDED":
                record.status = "COMPLETED"
                record.ended_at = _now()
                record.end_reason = "RECOVERED"
                self._active = None
            else:
                self._schedule(1, self._active)
            self._persist(record)

    def get(self, identifier: UUID) -> FaultRecord:
        with self._lock:
            record = self._records.get(identifier)
            if record is None:
                raise FaultNotFound("Fault was not found in this process")
            return record.model_copy(deep=True)

    def list(self, *, page: int, limit: int) -> dict:
        with self._lock:
            records = sorted(self._records.values(), key=lambda item: (item.started_at, item.id), reverse=True)
            total = len(records)
            items = [record.model_copy(deep=True) for record in records[(page - 1) * limit:page * limit]]
        return {"data": items, "pagination": {"page": page, "limit": limit, "total": total,
                                              "pages": (total + limit - 1) // limit}}

    def reset(self) -> FaultRecord | None:
        with self._lock:
            return self._restore(self._active, reason="CANCELLED", cancelled=True) if self._active else None
