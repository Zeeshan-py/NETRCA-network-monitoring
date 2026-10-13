"""PostgreSQL topology records. Runtime Mininet objects are never auto-saved."""
from datetime import datetime, timezone
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.db.connection import transaction
from app.topology.graph import TopologyGraph
from app.topology.models import Device, DeviceCreate, Link, LinkCreate, Snapshot


DEVICE_COLUMNS = "id, name, device_type, status, ip_address::text AS ip_address, mac_address, hostname, is_active, metadata, created_at, updated_at"
LINK_COLUMNS = "id, source_device_id, destination_device_id, status, bandwidth_mbps, latency_ms, packet_loss_percent, interface_source, interface_destination, metadata, created_at, updated_at"


class TopologyConflict(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class TopologyNotFound(LookupError):
    pass


class TopologyStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self) -> TopologyGraph:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cursor.execute(f"SELECT {DEVICE_COLUMNS} FROM public.devices ORDER BY name, id")
                devices = [Device.model_validate(row) for row in cursor.fetchall()]
                cursor.execute(f"SELECT {LINK_COLUMNS} FROM public.links ORDER BY id")
                links = [Link.model_validate(row) for row in cursor.fetchall()]
        return TopologyGraph(devices, links)

    def list_snapshots(self, limit: int = 20) -> list[Snapshot]:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SELECT id, snapshot_time, topology_data, reason, created_at "
                               "FROM public.topology_snapshots ORDER BY snapshot_time DESC, id DESC LIMIT %s", (limit,))
                return [Snapshot.model_validate(row) for row in cursor.fetchall()]

    def create_snapshot(self, reason: str | None = None) -> Snapshot:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                cursor.execute(f"SELECT {DEVICE_COLUMNS} FROM public.devices ORDER BY name, id")
                devices = [Device.model_validate(row) for row in cursor.fetchall()]
                cursor.execute(f"SELECT {LINK_COLUMNS} FROM public.links ORDER BY id")
                links = [Link.model_validate(row) for row in cursor.fetchall()]
                validation = TopologyGraph(devices, links).validate()
                if not validation.valid:
                    raise TopologyConflict("INVALID_TOPOLOGY")
                data = {"nodes": [item.model_dump(mode="json") for item in devices],
                        "links": [item.model_dump(mode="json") for item in links]}
                cursor.execute(
                    "INSERT INTO public.topology_snapshots (snapshot_time, topology_data, reason) "
                    "VALUES (%s, %s, %s) RETURNING id, snapshot_time, topology_data, reason, created_at",
                    (datetime.now(timezone.utc), Jsonb(data), reason),
                )
                return Snapshot.model_validate(cursor.fetchone())

    def get_device(self, device_id: UUID) -> Device:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(f"SELECT {DEVICE_COLUMNS} FROM public.devices WHERE id = %s", (device_id,))
                row = cursor.fetchone()
        if row is None:
            raise TopologyNotFound("DEVICE_NOT_FOUND")
        return Device.model_validate(row)

    def get_link(self, link_id: UUID) -> Link:
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(f"SELECT {LINK_COLUMNS} FROM public.links WHERE id = %s", (link_id,))
                row = cursor.fetchone()
        if row is None:
            raise TopologyNotFound("LINK_NOT_FOUND")
        return Link.model_validate(row)

    def create_device(self, value: DeviceCreate) -> Device:
        if not value.name.strip():
            raise TopologyConflict("EMPTY_DEVICE_NAME")
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    f"INSERT INTO public.devices (name, device_type, status, ip_address, mac_address, hostname, metadata) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING {DEVICE_COLUMNS}",
                    (value.name, value.device_type, value.status, value.ip_address,
                     value.mac_address, value.hostname, Jsonb(value.metadata) if value.metadata is not None else None),
                )
                row = cursor.fetchone()
        if row is None:
            raise TopologyConflict("DUPLICATE_DEVICE")
        return Device.model_validate(row)

    def create_link(self, value: LinkCreate) -> Link:
        if value.source_device_id == value.destination_device_id:
            raise TopologyConflict("SELF_LINK")
        with transaction(self.settings) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                # Serialize link creation because the Phase 2 schema has no unordered-pair unique index.
                cursor.execute("SELECT pg_advisory_xact_lock(47301, 4)")
                cursor.execute("SELECT id FROM public.devices WHERE id IN (%s, %s)",
                               (value.source_device_id, value.destination_device_id))
                if len(cursor.fetchall()) != 2:
                    raise TopologyConflict("INVALID_LINK_ENDPOINT")
                cursor.execute(
                    "SELECT 1 FROM public.links WHERE "
                    "(source_device_id = %s AND destination_device_id = %s) OR "
                    "(source_device_id = %s AND destination_device_id = %s) LIMIT 1",
                    (value.source_device_id, value.destination_device_id,
                     value.destination_device_id, value.source_device_id),
                )
                if cursor.fetchone() is not None:
                    raise TopologyConflict("DUPLICATE_LINK")
                cursor.execute(
                    f"INSERT INTO public.links (source_device_id, destination_device_id, status, "
                    f"bandwidth_mbps, latency_ms, packet_loss_percent, interface_source, interface_destination, metadata) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING {LINK_COLUMNS}",
                    (value.source_device_id, value.destination_device_id, value.status,
                     value.bandwidth_mbps, value.latency_ms, value.packet_loss_percent,
                     value.interface_source, value.interface_destination,
                     Jsonb(value.metadata) if value.metadata is not None else None),
                )
                row = cursor.fetchone()
        return Link.model_validate(row)
