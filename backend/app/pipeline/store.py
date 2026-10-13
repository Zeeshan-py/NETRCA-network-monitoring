"""Transactional PostgreSQL evidence store; Mininet records are never auto-seeded."""
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.db.connection import transaction
from app.monitoring.models import MonitoringSnapshot, ProbeReading
from app.pipeline.models import EventIn, LogIn, MetricIn


class EvidenceConflict(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _key(*parts: object) -> str:
    return sha256("|".join(str(item) for item in parts).encode()).hexdigest()


def _metric(cursor, item: MetricIn) -> bool:
    metadata = {"source": item.source, "observation_key": item.observation_key}
    if item.interface:
        metadata["interface"] = item.interface
    if item.target:
        metadata["target"] = item.target
    cursor.execute(
        "INSERT INTO public.metrics (device_id, link_id, metric_type, value, unit, timestamp, metadata) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
        (item.device_id, item.link_id, item.metric_type, item.value, item.unit, item.timestamp, Jsonb(metadata)),
    )
    if cursor.fetchone() is not None:
        return True
    cursor.execute("SELECT device_id, link_id, metric_type, value, unit, timestamp, metadata FROM public.metrics "
                   "WHERE metadata->>'observation_key' = %s", (item.observation_key,))
    existing = cursor.fetchone()
    if existing is None or any((existing["device_id"] != item.device_id,
                               existing["link_id"] != item.link_id,
                               existing["metric_type"] != item.metric_type,
                               existing["value"] != item.value,
                               existing["unit"] != item.unit,
                               existing["timestamp"] != item.timestamp,
                               existing["metadata"] != metadata)):
        raise EvidenceConflict("OBSERVATION_KEY_CONFLICT")
    return False


def _event(cursor, item: EventIn) -> bool:
    cursor.execute(
        "INSERT INTO public.events (device_id, link_id, event_type, severity, message, status, timestamp, metadata) "
        "VALUES (%s,%s,%s,%s,%s,'DETECTED',%s,%s) ON CONFLICT DO NOTHING RETURNING id",
        (item.device_id, item.link_id, item.event_type, item.severity, item.message,
         item.timestamp, Jsonb({"source": item.source, "dedup_key": item.dedup_key})),
    )
    if cursor.fetchone() is not None:
        return True
    cursor.execute("SELECT device_id, link_id, event_type, severity, message, timestamp, metadata "
                   "FROM public.events WHERE status='DETECTED' AND metadata->>'dedup_key' = %s",
                   (item.dedup_key,))
    existing = cursor.fetchone()
    if existing is not None and existing["event_type"] != item.event_type and (
        existing["device_id"] == item.device_id and existing["link_id"] == item.link_id
        and existing["metadata"]["source"] == item.source
    ):
        _resolve(cursor, item.dedup_key)
        return _event(cursor, item)
    if existing is None or any((existing["device_id"] != item.device_id,
                               existing["link_id"] != item.link_id,
                               existing["event_type"] != item.event_type,
                               existing["severity"] != item.severity,
                               existing["message"] != item.message,
                               existing["metadata"]["source"] != item.source)):
        raise EvidenceConflict("EVENT_KEY_CONFLICT")
    return False


def _resolve(cursor, dedup_key: str) -> None:
    cursor.execute("UPDATE public.events SET status = 'RESOLVED' "
                   "WHERE status = 'DETECTED' AND metadata->>'dedup_key' = %s", (dedup_key,))


class EvidenceStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def ingest_metrics(self, items: list[MetricIn]) -> dict[str, int]:
        if not 1 <= len(items) <= 100:
            raise EvidenceConflict("INVALID_BATCH_SIZE")
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                ids = {item.device_id for item in items if item.device_id}
                if ids:
                    cursor.execute("SELECT id FROM public.devices WHERE id = ANY(%s) AND is_active", (list(ids),))
                    if {row["id"] for row in cursor.fetchall()} != ids:
                        raise EvidenceConflict("DEVICE_NOT_FOUND")
                link_ids = {item.link_id for item in items if item.link_id}
                if link_ids:
                    cursor.execute("SELECT id FROM public.links WHERE id = ANY(%s)", (list(link_ids),))
                    if {row["id"] for row in cursor.fetchall()} != link_ids:
                        raise EvidenceConflict("LINK_NOT_FOUND")
                inserted = sum(_metric(cursor, item) for item in items)
        return {"inserted": inserted, "duplicates": len(items) - inserted}

    def ingest_log(self, item: LogIn) -> dict[str, int]:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                if item.device_id:
                    cursor.execute("SELECT 1 FROM public.devices WHERE id = %s", (item.device_id,))
                    if cursor.fetchone() is None:
                        raise EvidenceConflict("DEVICE_NOT_FOUND")
                if item.service_id:
                    cursor.execute("SELECT 1 FROM public.services WHERE id = %s", (item.service_id,))
                    if cursor.fetchone() is None:
                        raise EvidenceConflict("SERVICE_NOT_FOUND")
                cursor.execute(
                    "INSERT INTO public.logs (device_id, service_id, severity, event_type, message, source, timestamp, metadata) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",
                    (item.device_id, item.service_id, item.severity, item.event_type, item.message,
                     item.source, item.timestamp, Jsonb({"observation_key": item.observation_key})),
                )
                inserted = cursor.fetchone() is not None
                if not inserted:
                    cursor.execute("SELECT device_id, service_id, severity, event_type, message, source, timestamp "
                                   "FROM public.logs WHERE metadata->>'observation_key' = %s",
                                   (item.observation_key,))
                    existing = cursor.fetchone()
                    if existing is None or any((existing["device_id"] != item.device_id,
                                               existing["service_id"] != item.service_id,
                                               existing["severity"] != item.severity,
                                               existing["event_type"] != item.event_type,
                                               existing["message"] != item.message,
                                               existing["source"] != item.source,
                                               existing["timestamp"] != item.timestamp)):
                        raise EvidenceConflict("OBSERVATION_KEY_CONFLICT")
        return {"inserted": int(inserted), "duplicates": int(not inserted)}

    def ingest_event(self, item: EventIn) -> dict[str, int]:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                if item.device_id:
                    cursor.execute("SELECT 1 FROM public.devices WHERE id = %s", (item.device_id,))
                    if cursor.fetchone() is None:
                        raise EvidenceConflict("DEVICE_NOT_FOUND")
                if item.link_id:
                    cursor.execute("SELECT 1 FROM public.links WHERE id = %s", (item.link_id,))
                    if cursor.fetchone() is None:
                        raise EvidenceConflict("LINK_NOT_FOUND")
                inserted = _event(cursor, item)
        return {"inserted": int(inserted), "duplicates": int(not inserted)}

    def ingest_snapshot(self, snapshot: MonitoringSnapshot) -> dict[str, int]:
        if snapshot.network_state != "RUNNING" or snapshot.collection_status == "UNAVAILABLE":
            raise EvidenceConflict("OBSERVATION_UNAVAILABLE")
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(47301, 6)")
                names = [device.name for device in snapshot.devices]
                if (not names or len(names) != len(set(names)) or len(names) > 32
                    or sum(len(device.interfaces) for device in snapshot.devices) > 32
                    or len(snapshot.links) > 64 or len(snapshot.errors) > 64):
                    raise EvidenceConflict("INVALID_OBSERVATION")
                cursor.execute("SELECT id, name FROM public.devices WHERE name = ANY(%s) AND is_active", (names,))
                devices = {row["name"]: row["id"] for row in cursor.fetchall()}
                if len(devices) != len(names):
                    raise EvidenceConflict("DEVICE_NOT_FOUND")
                cursor.execute("SELECT id, source_device_id, destination_device_id, interface_source, interface_destination "
                               "FROM public.links WHERE source_device_id = ANY(%s) AND destination_device_id = ANY(%s)",
                               (list(devices.values()), list(devices.values())))
                stored_links = cursor.fetchall()
                metrics = events = duplicates = 0
                unmapped_links = 0
                for device in snapshot.devices:
                    device_id = devices[device.name]
                    for interface in device.interfaces:
                        previous = None
                        if interface.status in {"UP", "DOWN"}:
                            cursor.execute("SELECT value, timestamp FROM public.metrics WHERE device_id=%s "
                                           "AND metric_type='INTERFACE_STATE' AND metadata->>'interface'=%s "
                                           "ORDER BY timestamp DESC, id DESC LIMIT 1", (device_id, interface.name))
                            previous = cursor.fetchone()
                        fields = (("rx_bytes", "RX_BYTES", "bytes"), ("tx_bytes", "TX_BYTES", "bytes"),
                                  ("rx_packets", "RX_PACKETS", "packets"), ("tx_packets", "TX_PACKETS", "packets"),
                                  ("rx_errors", "RX_ERRORS", "packets"), ("tx_errors", "TX_ERRORS", "packets"))
                        values = [(kind, getattr(interface, field), unit) for field, kind, unit in fields]
                        if interface.status in {"UP", "DOWN"}:
                            values.append(("INTERFACE_STATE", int(interface.status == "UP"), "state"))
                        for kind, value, unit in values:
                            if value is None:
                                continue
                            item = MetricIn(device_id=device_id, metric_type=kind, value=value, unit=unit,
                                            timestamp=snapshot.observed_at, source="mininet_snapshot",
                                            interface=interface.name,
                                            observation_key=_key("snapshot", snapshot.observed_at.isoformat(),
                                                                 device.name, interface.name, kind))
                            inserted = _metric(cursor, item)
                            metrics += int(inserted)
                            duplicates += int(not inserted)
                        if interface.status in {"UP", "DOWN"}:
                            dedup = f"interface:{device_id}:{interface.name}"
                            if previous and previous["timestamp"] < snapshot.observed_at and previous["value"] == 1 and interface.status == "DOWN":
                                events += int(_event(cursor, EventIn(device_id=device_id, event_type="INTERFACE_FAILURE",
                                    severity="HIGH", source="mininet_snapshot", timestamp=snapshot.observed_at,
                                    dedup_key=dedup, message=f"Interface {interface.name} changed to DOWN")))
                            elif previous and previous["timestamp"] < snapshot.observed_at and previous["value"] == 0 and interface.status == "UP":
                                _resolve(cursor, dedup)
                for link in snapshot.links:
                    if link.status == "UNKNOWN":
                        continue
                    source_id = devices.get(link.source)
                    destination_id = devices.get(link.destination)
                    matches = [row for row in stored_links if (
                        (row["source_device_id"] == source_id and row["destination_device_id"] == destination_id
                         and (row["interface_source"] in {None, link.interface_source})
                         and (row["interface_destination"] in {None, link.interface_destination})) or
                        (row["source_device_id"] == destination_id and row["destination_device_id"] == source_id
                         and (row["interface_source"] in {None, link.interface_destination})
                         and (row["interface_destination"] in {None, link.interface_source})))]
                    if len(matches) != 1:
                        unmapped_links += 1
                        continue
                    link_id = matches[0]["id"]
                    cursor.execute("SELECT value, timestamp FROM public.metrics WHERE link_id=%s "
                                   "AND metric_type='LINK_STATE' ORDER BY timestamp DESC, id DESC LIMIT 1", (link_id,))
                    previous = cursor.fetchone()
                    inserted = _metric(cursor, MetricIn(link_id=link_id, metric_type="LINK_STATE",
                        value=int(link.status == "UP"), unit="state", timestamp=snapshot.observed_at,
                        source="mininet_snapshot", observation_key=_key("snapshot", snapshot.observed_at.isoformat(),
                                                                          link_id, "LINK_STATE")))
                    metrics += int(inserted)
                    duplicates += int(not inserted)
                    dedup = f"link:{link_id}"
                    if previous and previous["timestamp"] < snapshot.observed_at and previous["value"] == 1 and link.status == "DOWN":
                        events += int(_event(cursor, EventIn(link_id=link_id, event_type="LINK_FAILURE",
                            severity="HIGH", source="mininet_snapshot", timestamp=snapshot.observed_at,
                            dedup_key=dedup, message="Link changed to DOWN")))
                    elif previous and previous["timestamp"] < snapshot.observed_at and previous["value"] == 0 and link.status == "UP":
                        _resolve(cursor, dedup)
                collection_key = "collection:mininet_snapshot"
                if snapshot.collection_status == "PARTIAL":
                    events += int(_event(cursor, EventIn(event_type="COLLECTION_FAILURE", severity="MEDIUM",
                        source="mininet_snapshot", timestamp=snapshot.observed_at, dedup_key=collection_key,
                        message="Monitoring snapshot was incomplete")))
                else:
                    _resolve(cursor, collection_key)
        return {"metrics": metrics, "events": events, "duplicates": duplicates, "unmapped_links": unmapped_links}

    def ingest_probe(self, probe: ProbeReading) -> dict[str, int]:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id, name FROM public.devices WHERE name = ANY(%s) AND is_active",
                               ([probe.source, probe.destination],))
                devices = {row["name"]: row["id"] for row in cursor.fetchall()}
                if len(devices) != 2 or probe.source == probe.destination:
                    raise EvidenceConflict("DEVICE_NOT_FOUND")
                source_id = devices[probe.source]
                metrics = events = duplicates = 0
                values = (("LATENCY", probe.latency_ms, "ms"),
                          ("PACKET_LOSS", probe.packet_loss_percent, "%"),
                          ("AVAILABILITY", 100 if probe.status == "REACHABLE" else
                           0 if probe.status == "UNREACHABLE" else None, "%"))
                for kind, value, unit in values:
                    if value is None:
                        continue
                    inserted = _metric(cursor, MetricIn(device_id=source_id, metric_type=kind, value=value,
                        unit=unit, timestamp=probe.observed_at, source="mininet_probe", target=probe.destination,
                        observation_key=_key("probe", probe.observed_at.isoformat(), probe.source,
                                             probe.destination, kind)))
                    metrics += int(inserted)
                    duplicates += int(not inserted)
                failure_key = f"probe:{source_id}:{devices[probe.destination]}"
                if probe.status in {"UNREACHABLE", "TIMEOUT", "UNAVAILABLE"}:
                    event_type = "PROBE_TIMEOUT" if probe.status == "TIMEOUT" else "PROBE_FAILED"
                    events += int(_event(cursor, EventIn(device_id=source_id, event_type=event_type,
                        severity="MEDIUM", source="mininet_probe", timestamp=probe.observed_at,
                        dedup_key=failure_key, message=f"Probe to {probe.destination} {probe.status.lower()}")))
                elif probe.status == "REACHABLE":
                    _resolve(cursor, failure_key)
        return {"metrics": metrics, "events": events, "duplicates": duplicates}

    def list_records(self, table: str, *, page: int, limit: int, device_id: UUID | None = None,
                     link_id: UUID | None = None,
                     name: str | None = None, from_time: datetime | None = None,
                     to_time: datetime | None = None) -> dict:
        if table not in {"metrics", "logs", "events"}:
            raise ValueError("Unsupported evidence table")
        column = {"metrics": "metric_type", "logs": "severity", "events": "event_type"}[table]
        clauses = []
        params: list = []
        if device_id:
            clauses.append("device_id = %s")
            params.append(device_id)
        if link_id:
            if table != "metrics" and table != "events":
                raise ValueError("Link filtering is unavailable for logs")
            clauses.append("link_id = %s")
            params.append(link_id)
        if name:
            clauses.append(f"{column} = %s")
            params.append(name)
        if from_time:
            clauses.append("timestamp >= %s")
            params.append(from_time)
        if to_time:
            clauses.append("timestamp <= %s")
            params.append(to_time)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                if connection.info.transaction_status == TransactionStatus.IDLE:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cursor.execute(f"SELECT count(*) AS total FROM public.{table}{where}", params)
                total = cursor.fetchone()["total"]
                cursor.execute(f"SELECT * FROM public.{table}{where} ORDER BY timestamp DESC, id DESC LIMIT %s OFFSET %s",
                               [*params, limit, (page - 1) * limit])
                items = cursor.fetchall()
        return {"data": items, "pagination": {"page": page, "limit": limit, "total": total,
                                               "pages": (total + limit - 1) // limit}}
